import base64
import json
import re
import time
from pathlib import Path

import click

from d2l.auth import token_info, load_token, make_session
from d2l.errors import handle_errors
from d2l.formatting import output, table

D2L_TOKEN_RE = re.compile(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
D2L_TOKEN_ISSUER = "https://api.brightspace.com/auth"
D2L_TOKEN_AUDIENCE = "https://api.brightspace.com/auth/token"
WHOAMI_PATH = "/d2l/api/lp/1.47/users/whoami"
LOGIN_WAIT_SECONDS = 15


def _decode_jwt_claims(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _extract_profile_token(browser_profile: Path):
    leveldb_dir = browser_profile / "Default" / "Local Storage" / "leveldb"
    if not leveldb_dir.exists():
        return None

    now = int(time.time())
    seen = set()
    best = None

    for path in sorted(leveldb_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix not in {".log", ".ldb"}:
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue

        for match in D2L_TOKEN_RE.finditer(raw):
            token = match.group(0).decode("utf-8", "ignore")
            if token in seen:
                continue
            seen.add(token)
            try:
                claims = _decode_jwt_claims(token)
            except Exception:
                continue
            if claims.get("iss") != D2L_TOKEN_ISSUER:
                continue
            if claims.get("aud") != D2L_TOKEN_AUDIENCE:
                continue
            exp = claims.get("exp")
            if not isinstance(exp, int) or exp <= now:
                continue
            candidate = (exp, token, claims, path)
            if best is None or candidate[0] > best[0]:
                best = candidate

    if not best:
        return None

    _, token, claims, path = best
    return token, claims, path


def _save_token(token: str, claims: dict, token_file: Path, token_dir: Path):
    token_dir.mkdir(exist_ok=True)
    data = {
        "auth_type": "bearer",
        "token": token,
        "exp": claims.get("exp"),
        "sub": claims.get("sub"),
        "tenant": claims.get("tenantid"),
        "captured_at": int(time.time()),
    }
    token_file.write_text(json.dumps(data, indent=2))


def _save_cookie_session(cookies, whoami: dict, token_file: Path, token_dir: Path):
    token_dir.mkdir(exist_ok=True)
    data = {
        "auth_type": "browser-session",
        "sub": whoami.get("Identifier"),
        "tenant": None,
        "captured_at": int(time.time()),
        "cookies": [
            {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain"),
                "path": c.get("path", "/"),
            }
            for c in cookies
        ],
    }
    token_file.write_text(json.dumps(data, indent=2))


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

    d2l_url = "https://kennesaw.view.usg.edu/d2l/home"
    captured_token = None
    captured_claims = None

    def on_request(request):
        nonlocal captured_token, captured_claims
        if captured_token:
            return
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer eyJ"):
            token = auth.removeprefix("Bearer ")
            try:
                claims = _decode_jwt_claims(token)
            except Exception:
                return
            captured_token = token
            captured_claims = claims
            click.echo(f"[*] Captured token from request: {request.url[:80]}...")

    with sync_playwright() as p:
        click.echo(f"[*] Launching browser (profile: {BROWSER_PROFILE})")
        if not headless:
            click.echo("[*] Log in if prompted. Token will be captured automatically.\n")

        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE),
            headless=headless,
            viewport={"width": 1280, "height": 900},
        )
        context.on("request", on_request)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(d2l_url, wait_until="domcontentloaded")

        deadline = time.time() + LOGIN_WAIT_SECONDS
        try:
            while not captured_token and time.time() < deadline:
                page.wait_for_timeout(500)
                if not context.pages:
                    break
        except Exception:
            pass

        whoami_data = None
        try:
            whoami_data = page.evaluate(
                f"""
async () => {{
  const resp = await fetch('{WHOAMI_PATH}', {{ credentials: 'include' }});
  const text = await resp.text();
  return {{ ok: resp.ok, status: resp.status, text }};
}}
"""
            )
        except Exception:
            whoami_data = None

        if not captured_token:
            profile_token = _extract_profile_token(BROWSER_PROFILE)
            if profile_token:
                captured_token, captured_claims, token_path = profile_token
                click.echo(f"[*] Loaded token from browser profile: {token_path}")

        if captured_token and captured_claims:
            _save_token(captured_token, captured_claims, TOKEN_FILE, TOKEN_DIR)
            click.echo(f"\n[OK] Token saved to {TOKEN_FILE}")
            click.echo(f"     Expires: {time.ctime(captured_claims['exp'])}")
            click.echo(f"     User ID: {captured_claims.get('sub')}")
        elif whoami_data and whoami_data.get("ok"):
            whoami = json.loads(whoami_data["text"])
            cookies = context.cookies([d2l_url])
            _save_cookie_session(cookies, whoami, TOKEN_FILE, TOKEN_DIR)
            click.echo(f"\n[OK] Browser session saved to {TOKEN_FILE}")
            click.echo(f"     User ID: {whoami.get('Identifier')}")
            click.echo(f"     Cookie count: {len(cookies)}")
        else:
            click.echo("[!] No token or browser session captured.", err=True)
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
    if info.get("auth_type"):
        click.echo(f"Auth:      {info['auth_type']}")
    if info.get("user_id") is not None:
        click.echo(f"User ID:   {info['user_id']}")
    if info.get("expires_at"):
        click.echo(f"Expires:   {info['expires_at']}")
    if info.get("remaining_minutes") is not None:
        click.echo(f"Remaining: {info['remaining_minutes']} min")
    if info.get("cookie_count") is not None:
        click.echo(f"Cookies:   {info['cookie_count']}")
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
