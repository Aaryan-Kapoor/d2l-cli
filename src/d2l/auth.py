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
    payload += "=" * (4 - len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def load_token():
    """Load token from ~/.d2l/token.json > .env > D2L_TOKEN env var.

    Raises TokenExpiredError if found but expired.
    Raises TokenNotFoundError if not found.
    """
    # 1. ~/.d2l/token.json
    if TOKEN_FILE.exists():
        data = json.loads(TOKEN_FILE.read_text())
        exp = data.get("exp", 0)
        if exp > time.time():
            return data["token"]
        raise TokenExpiredError(
            f"Token expired at {time.ctime(exp)}. Run: d2l login"
        )

    # 2. .env file
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("D2L_TOKEN="):
                return line.strip().split("=", 1)[1]

    # 3. Environment variable
    val = os.environ.get("D2L_TOKEN")
    if val:
        return val

    raise TokenNotFoundError("No token found. Run: d2l login")


def token_info():
    """Return token metadata dict (no API call needed)."""
    if not TOKEN_FILE.exists():
        return {"status": "not found"}
    data = json.loads(TOKEN_FILE.read_text())
    exp = data.get("exp", 0)
    now = time.time()
    remaining = max(0, exp - now)
    return {
        "status": "valid" if exp > now else "expired",
        "user_id": data.get("sub"),
        "tenant": data.get("tenant"),
        "expires_at": time.ctime(exp),
        "remaining_seconds": int(remaining),
        "remaining_minutes": round(remaining / 60, 1),
        "captured_at": time.ctime(data.get("captured_at", 0)),
    }


def make_session(token):
    """Create a requests.Session with Bearer auth and browser headers."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Origin": LMS_HOST,
        "Referer": f"{LMS_HOST}/",
        "User-Agent": USER_AGENT,
    })
    return s
