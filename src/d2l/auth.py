import base64
import json
import os
import time

import requests

from d2l.config import LMS_HOST, TOKEN_FILE, USER_AGENT
from d2l.errors import TokenExpiredError, TokenNotFoundError


def decode_jwt_claims(token):
    """Decode JWT payload without external deps."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _load_file_auth():
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text())


def load_token():
    """Load D2L auth from ~/.d2l/token.json > .env > D2L_TOKEN env var.

    Returns either a bearer token string or a cookie-auth dict.
    Raises TokenExpiredError if found but expired and no cookie session exists.
    Raises TokenNotFoundError if not found.
    """
    data = _load_file_auth()
    if data:
        exp = data.get("exp", 0)
        if data.get("token") and exp > time.time():
            return data["token"]
        if data.get("cookies"):
            return data
        if data.get("token"):
            raise TokenExpiredError(
                f"Token expired at {time.ctime(exp)}. Run: d2l login"
            )

    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("D2L_TOKEN="):
                return line.strip().split("=", 1)[1]

    val = os.environ.get("D2L_TOKEN")
    if val:
        return val

    raise TokenNotFoundError("No token found. Run: d2l login")


def token_info():
    """Return token metadata dict (no API call needed)."""
    data = _load_file_auth()
    if not data:
        return {"status": "not found"}

    now = time.time()
    if data.get("token"):
        exp = data.get("exp", 0)
        remaining = max(0, exp - now)
        return {
            "status": "valid" if exp > now else "expired",
            "auth_type": "bearer",
            "user_id": data.get("sub"),
            "tenant": data.get("tenant"),
            "expires_at": time.ctime(exp),
            "remaining_seconds": int(remaining),
            "remaining_minutes": round(remaining / 60, 1),
            "captured_at": time.ctime(data.get("captured_at", 0)),
        }

    if data.get("cookies"):
        return {
            "status": "valid",
            "auth_type": "browser-session",
            "user_id": data.get("sub"),
            "tenant": data.get("tenant"),
            "captured_at": time.ctime(data.get("captured_at", 0)),
            "cookie_count": len(data.get("cookies", [])),
        }

    return {"status": "not found"}


def make_session(auth):
    """Create a requests.Session with bearer or cookie auth and browser headers."""
    s = requests.Session()
    s.headers.update({
        "Origin": LMS_HOST,
        "Referer": f"{LMS_HOST}/",
        "User-Agent": USER_AGENT,
    })

    if isinstance(auth, str):
        s.headers["Authorization"] = f"Bearer {auth}"
        return s

    if isinstance(auth, dict):
        token = auth.get("token")
        if token:
            s.headers["Authorization"] = f"Bearer {token}"
        for cookie in auth.get("cookies", []):
            s.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/"),
            )
        return s

    raise TokenNotFoundError("No valid D2L auth found. Run: d2l login")
