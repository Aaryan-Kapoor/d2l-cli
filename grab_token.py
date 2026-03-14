"""
Launches a browser to kennesaw.view.usg.edu, intercepts a Bearer token
from API requests, and saves it to ~/.d2l/token.json.

Uses a persistent browser profile so you only log in once.
"""

import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

D2L_URL = "https://kennesaw.view.usg.edu/d2l/home"
TOKEN_DIR = Path.home() / ".d2l"
TOKEN_FILE = TOKEN_DIR / "token.json"
BROWSER_PROFILE = TOKEN_DIR / "browser_profile"


def save_token(token: str):
    TOKEN_DIR.mkdir(exist_ok=True)
    # Decode JWT to get expiry without external deps
    import base64
    payload = token.split(".")[1]
    # Fix padding
    payload += "=" * (4 - len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))

    data = {
        "token": token,
        "exp": claims.get("exp"),
        "sub": claims.get("sub"),
        "tenant": claims.get("tenantid"),
        "captured_at": int(time.time()),
    }
    TOKEN_FILE.write_text(json.dumps(data, indent=2))
    print(f"\n[OK] Token saved to {TOKEN_FILE}")
    print(f"     Expires: {time.ctime(claims['exp'])}")
    print(f"     User ID: {claims.get('sub')}")


def main():
    captured_token = None

    def on_request(request):
        nonlocal captured_token
        if captured_token:
            return
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer eyJ"):
            captured_token = auth.removeprefix("Bearer ")
            print(f"[*] Captured Bearer token from: {request.url[:80]}...")

    with sync_playwright() as p:
        print(f"[*] Launching browser (profile: {BROWSER_PROFILE})")
        print("[*] Log in if prompted. The token will be captured automatically.\n")

        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.on("request", on_request)

        page.goto(D2L_URL, wait_until="domcontentloaded")

        # Wait for token capture — either from page load or after user logs in
        print("[*] Waiting for a Bearer token from API requests...")
        print("    (If you're already logged in, this should be instant.)")
        print("    (If not, log in through the browser window.)\n")

        # Poll until we get a token or user closes the browser
        try:
            while not captured_token:
                page.wait_for_timeout(500)
                # Check if browser is still open
                if not context.pages:
                    break
        except Exception:
            pass

        if captured_token:
            save_token(captured_token)
        else:
            print("[!] No token captured. Browser was closed before a token was found.")
            sys.exit(1)

        context.close()


if __name__ == "__main__":
    main()
