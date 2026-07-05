import json
import re
import time
from pathlib import Path

import click

from d2l.auth import TOKEN_AUDIENCE, TOKEN_ISSUER, decode_jwt_claims, token_info
from d2l.errors import handle_errors
from d2l.formatting import output

D2L_TOKEN_RE = re.compile(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
LOCAL_STORAGE_KEY = "D2L.Fetch.Tokens"
XSRF_STORAGE_KEY = "XSRF.Token"
AUTH_SCOPE = "*:*:*"
LOGIN_WAIT_SECONDS = 300
HEADLESS_WAIT_SECONDS = 30


def _is_valid_claims(claims):
    return (
        claims.get("iss") == TOKEN_ISSUER
        and claims.get("aud") == TOKEN_AUDIENCE
        and isinstance(claims.get("exp"), int)
    )


def _parse_token(token):
    try:
        claims = decode_jwt_claims(token)
    except Exception:
        return None
    if not _is_valid_claims(claims):
        return None
    return claims


def _save_token(token, claims, token_file, token_dir):
    token_dir.mkdir(exist_ok=True)
    data = {
        "token": token,
        "exp": claims.get("exp"),
        "sub": claims.get("sub"),
        "tenant": claims.get("tenantid"),
        "captured_at": int(time.time()),
    }
    token_file.write_text(json.dumps(data, indent=2))


def _extract_token_from_local_storage(page):
    try:
        raw = page.evaluate(
            """key => {
                try {
                    return window.localStorage.getItem(key);
                } catch {
                    return null;
                }
            }""",
            LOCAL_STORAGE_KEY,
        )
    except Exception:
        return None

    if not raw:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None

    now = int(time.time())
    best = None
    for item in data.values():
        if not isinstance(item, dict):
            continue
        token = item.get("access_token")
        if not token:
            continue
        claims = _parse_token(token)
        if not claims:
            continue
        exp = claims.get("exp", 0)
        if exp <= now:
            continue
        candidate = (exp, token, claims)
        if best is None or candidate[0] > best[0]:
            best = candidate

    if best is None:
        return None

    _, token, claims = best
    return token, claims


def _request_token_in_page(page):
    try:
        result = page.evaluate(
            """({ xsrfKey, scope }) => (async () => {
                let xsrf = null;
                try {
                    xsrf = window.localStorage.getItem(xsrfKey);
                } catch {}

                if (!xsrf) {
                    const xsrfResp = await window.fetch('/d2l/lp/auth/xsrf-tokens', {
                        credentials: 'include'
                    });
                    if (!xsrfResp.ok) {
                        return { ok: false, status: xsrfResp.status, stage: 'xsrf' };
                    }
                    const xsrfData = await xsrfResp.json();
                    xsrf = xsrfData.referrerToken;
                    try {
                        window.localStorage.setItem(xsrfKey, xsrf);
                    } catch {}
                }

                const tokenResp = await window.fetch('/d2l/lp/auth/oauth2/token', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Csrf-Token': xsrf,
                    },
                    body: `scope=${scope}`,
                });

                const text = await tokenResp.text();
                return { ok: tokenResp.ok, status: tokenResp.status, text };
            })()""",
            {"xsrfKey": XSRF_STORAGE_KEY, "scope": AUTH_SCOPE},
        )
    except Exception:
        return None

    if not result or not result.get("ok"):
        return None

    try:
        data = json.loads(result["text"])
    except Exception:
        return None

    token = data.get("access_token")
    if not token:
        return None

    claims = _parse_token(token)
    if not claims:
        return None
    if claims.get("exp", 0) <= time.time():
        return None
    return token, claims


def _extract_profile_token(browser_profile: Path):
    leveldb_dir = browser_profile / "Default" / "Local Storage" / "leveldb"
    if not leveldb_dir.exists():
        return None

    now = int(time.time())
    seen = set()
    best = None

    # Best-effort fallback only. Chrome may still be writing these files.
    for path in sorted(leveldb_dir.iterdir()):
        if not path.is_file() or path.suffix not in {".log", ".ldb"}:
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
            claims = _parse_token(token)
            if not claims:
                continue
            exp = claims.get("exp", 0)
            if exp <= now:
                continue
            candidate = (exp, token, claims, path)
            if best is None or candidate[0] > best[0]:
                best = candidate

    if not best:
        return None

    _, token, claims, path = best
    return token, claims, path


def _launch_context(p, browser_profile, headless, channel):
    """Launch a persistent browser context, falling back across browsers.

    'auto' tries Playwright's bundled Chromium first, then installed Chrome
    and Edge — so login works even when `playwright install chromium` was
    never run, as long as any Chromium-family browser is on the machine.
    """
    if channel == "auto":
        attempts = [(None, "bundled Chromium"), ("chrome", "Google Chrome"), ("msedge", "Microsoft Edge")]
    elif channel == "chromium":
        attempts = [(None, "bundled Chromium")]
    else:
        attempts = [(channel, channel)]

    errors = []
    for chan, label in attempts:
        kwargs = {"headless": headless, "viewport": {"width": 1280, "height": 900}}
        if chan:
            kwargs["channel"] = chan
        try:
            return p.chromium.launch_persistent_context(str(browser_profile), **kwargs), label
        except Exception as e:
            first_line = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            errors.append(f"    {label}: {first_line}")

    return None, errors


def _capture_and_save(headless, channel="auto", quiet=False):
    """Launch a browser, capture a D2L token, and save it. Returns True on success.

    quiet=True suppresses all output — used by the automatic background
    refresh so command output stays clean.
    """
    def echo(msg, err=False):
        if not quiet:
            click.echo(msg, err=err)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        echo(
            'Playwright not installed. Run: pip install "d2l-cli[login]" '
            "(no browser download needed if Chrome or Edge is installed)",
            err=True,
        )
        return False

    from d2l.config import get_lms_host, TOKEN_DIR, TOKEN_FILE, BROWSER_PROFILE
    from d2l.errors import ConfigError

    try:
        d2l_url = f"{get_lms_host()}/d2l/home"
    except ConfigError as e:
        echo(str(e), err=True)
        return False
    captured_token = None
    captured_claims = None

    def on_request(request):
        nonlocal captured_token, captured_claims
        if captured_token:
            return
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer eyJ"):
            return
        token = auth.removeprefix("Bearer ")
        claims = _parse_token(token)
        if not claims:
            return
        if claims["exp"] <= time.time():
            return
        captured_token = token
        captured_claims = claims
        echo(f"[*] Captured token from request: {request.url[:80]}...")

    with sync_playwright() as p:
        context, launch_result = _launch_context(p, BROWSER_PROFILE, headless, channel)
        if context is None:
            echo("[!] Could not launch a browser for login. Tried:", err=True)
            for line in launch_result:
                echo(line, err=True)
            echo(
                "    Fix: run `python -m playwright install chromium`, "
                "or install Google Chrome / Microsoft Edge.",
                err=True,
            )
            return False
        echo(f"[*] Launched {launch_result} (profile: {BROWSER_PROFILE})")
        if not headless:
            echo("[*] Log in if prompted. Token will be captured automatically.\n")

        context.on("request", on_request)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(d2l_url, wait_until="domcontentloaded")

        deadline = time.time() + (
            HEADLESS_WAIT_SECONDS if headless else LOGIN_WAIT_SECONDS
        )
        try:
            while not captured_token and time.time() < deadline:
                for candidate in reversed(context.pages or [page]):
                    result = _extract_token_from_local_storage(candidate)
                    if result:
                        captured_token, captured_claims = result
                        echo("[*] Captured token from local storage")
                        break
                    result = _request_token_in_page(candidate)
                    if result:
                        captured_token, captured_claims = result
                        echo("[*] Refreshed token through D2L auth endpoint")
                        break
                if captured_token:
                    break
                if context.pages:
                    context.pages[-1].wait_for_timeout(500)
                else:
                    break
        except Exception:
            pass

        if not captured_token:
            profile_token = _extract_profile_token(BROWSER_PROFILE)
            if profile_token:
                captured_token, captured_claims, token_path = profile_token
                echo(f"[*] Loaded token from browser profile: {token_path}")

        context.close()

    if captured_token and captured_claims:
        _save_token(captured_token, captured_claims, TOKEN_FILE, TOKEN_DIR)
        echo(f"\n[OK] Token saved to {TOKEN_FILE}")
        echo(f"     Expires: {time.ctime(captured_claims['exp'])}")
        echo(f"     User ID: {captured_claims.get('sub')}")
        return True

    echo("[!] No token captured.", err=True)
    return False


AUTO_LOGIN_DISABLED_ENV = "D2L_NO_AUTO_LOGIN"


def _playwright_available():
    from importlib.util import find_spec

    return find_spec("playwright") is not None


def attempt_auto_login():
    """Silent headless token refresh using saved session cookies.

    Called automatically when a command finds the token missing/expired.
    Returns True if a fresh token was captured; never raises and never
    opens a visible browser.
    """
    import os

    from d2l.config import BROWSER_PROFILE

    if os.environ.get(AUTO_LOGIN_DISABLED_ENV):
        return False
    if not BROWSER_PROFILE.exists():
        return False
    if not _playwright_available():
        return False

    click.echo("[*] D2L token expired — refreshing sign-in in the background...", err=True)
    try:
        return _capture_and_save(headless=True, channel="auto", quiet=True)
    except Exception:
        return False


@click.command()
@click.option("--headless", is_flag=True, help="Run browser headless (for servers)")
@click.option(
    "--channel",
    type=click.Choice(["auto", "chromium", "chrome", "msedge"]),
    default="auto",
    show_default=True,
    help="Browser to launch; auto falls back from bundled Chromium to installed Chrome/Edge",
)
def login(headless, channel):
    """Launch browser to capture D2L auth token."""
    if not _capture_and_save(headless=headless, channel=channel):
        raise SystemExit(1)


@click.command()
def token():
    """Show token status (no API call needed)."""
    info = token_info()
    if info["status"] == "not found":
        click.echo(info.get("error", "No token found. Run: d2l login"))
        return
    if info["status"] == "unsupported":
        click.echo(
            info.get("error", "Unsupported auth in token.json. Run: d2l login"),
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"Status:    {info['status']}")
    if info.get("auth_type"):
        click.echo(f"Auth:      {info['auth_type']}")
    if info.get("user_id") is not None:
        click.echo(f"User ID:   {info['user_id']}")
    if info.get("expires_at"):
        click.echo(f"Expires:   {info['expires_at']}")
    if info.get("remaining_minutes") is not None:
        click.echo(f"Remaining: {info['remaining_minutes']} min")
    if info.get("captured_at"):
        click.echo(f"Captured:  {info['captured_at']}")


@click.command()
@click.pass_context
@handle_errors
def whoami(ctx):
    """Show current user identity."""
    client = ctx.obj["get_client"]()
    data = client.whoami()
    output(
        data,
        human_fn=lambda d: (
            f"  {d.get('FirstName')} {d.get('LastName')}\n"
            f"  Username: {d.get('UniqueName')}\n"
            f"  ID: {d.get('Identifier')}"
        ),
        title="Who Am I",
    )
