import click

from d2l.auth import token_info, load_token, make_session
from d2l.errors import handle_errors
from d2l.formatting import output, table


@click.command()
@click.option("--headless", is_flag=True, help="Run browser headless (for servers)")
def login(headless):
    """Launch browser to capture D2L auth token."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        click.echo("Playwright not installed. Run: pip install playwright && playwright install chromium", err=True)
        raise SystemExit(1)

    from d2l.config import TOKEN_DIR, TOKEN_FILE, BROWSER_PROFILE
    import json, time, base64

    d2l_url = "https://kennesaw.view.usg.edu/d2l/home"
    captured_token = None

    def on_request(request):
        nonlocal captured_token
        if captured_token:
            return
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer eyJ"):
            captured_token = auth.removeprefix("Bearer ")
            click.echo(f"[*] Captured token from: {request.url[:80]}...")

    with sync_playwright() as p:
        click.echo(f"[*] Launching browser (profile: {BROWSER_PROFILE})")
        if not headless:
            click.echo("[*] Log in if prompted. Token will be captured automatically.\n")

        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE),
            headless=headless,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("request", on_request)
        page.goto(d2l_url, wait_until="domcontentloaded")

        try:
            while not captured_token:
                page.wait_for_timeout(500)
                if not context.pages:
                    break
        except Exception:
            pass

        if captured_token:
            TOKEN_DIR.mkdir(exist_ok=True)
            payload = captured_token.split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            data = {
                "token": captured_token,
                "exp": claims.get("exp"),
                "sub": claims.get("sub"),
                "tenant": claims.get("tenantid"),
                "captured_at": int(time.time()),
            }
            TOKEN_FILE.write_text(json.dumps(data, indent=2))
            click.echo(f"\n[OK] Token saved to {TOKEN_FILE}")
            click.echo(f"     Expires: {time.ctime(claims['exp'])}")
            click.echo(f"     User ID: {claims.get('sub')}")
        else:
            click.echo("[!] No token captured.", err=True)
            raise SystemExit(1)

        context.close()


@click.command()
def token():
    """Show token status (no API call needed)."""
    info = token_info()
    if info["status"] == "not found":
        click.echo("No token found. Run: d2l login")
        return
    click.echo(f"Status:    {info['status']}")
    click.echo(f"User ID:   {info['user_id']}")
    click.echo(f"Expires:   {info['expires_at']}")
    click.echo(f"Remaining: {info['remaining_minutes']} min")
    click.echo(f"Captured:  {info['captured_at']}")


@click.command()
@click.pass_context
@handle_errors
def whoami(ctx):
    """Show current user identity."""
    client = ctx.obj["get_client"]()
    data = client.whoami()
    output(data, human_fn=lambda d: (
        f"  {d.get('FirstName')} {d.get('LastName')}\n"
        f"  Username: {d.get('UniqueName')}\n"
        f"  ID: {d.get('Identifier')}"
    ), title="Who Am I")
