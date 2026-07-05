import base64
import json
import os
import time

import requests

from d2l.config import get_lms_host, TOKEN_FILE, USER_AGENT
from d2l.errors import TokenExpiredError, TokenNotFoundError

TOKEN_ISSUER = "https://api.brightspace.com/auth"
TOKEN_AUDIENCE = "https://api.brightspace.com/auth/token"


def decode_jwt_claims(token):
    """Decode JWT payload without external deps."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _read_token_file():
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text())


def _parse_bearer_claims(token):
    if not isinstance(token, str) or token.count(".") != 2:
        return None
    try:
        claims = decode_jwt_claims(token)
    except Exception:
        return None
    if claims.get("iss") != TOKEN_ISSUER or claims.get("aud") != TOKEN_AUDIENCE:
        return None
    return claims


def _unsupported_token_file_message(data):
    if isinstance(data, dict) and data.get("auth_type"):
        return (
            f"token.json contains unsupported auth_type={data['auth_type']}. "
            "Run: d2l login"
        )
    return "token.json does not contain a valid D2L bearer token. Run: d2l login"


def _load_env_token(token, source_name):
    if not token:
        return None
    if _parse_bearer_claims(token):
        return token
    raise TokenNotFoundError(
        f"{source_name} does not contain a valid D2L bearer token. Run: d2l login"
    )


def load_token():
    """Load bearer token from ~/.d2l/token.json > .env > D2L_TOKEN env var.

    An expired token.json no longer blocks the env fallbacks.
    Raises TokenExpiredError if only an expired token was found.
    Raises TokenNotFoundError if not found.
    """
    expired_error = None
    data = _read_token_file()
    if data is not None:
        token = data.get("token") if isinstance(data, dict) else None
        claims = _parse_bearer_claims(token)
        if not claims:
            raise TokenNotFoundError(_unsupported_token_file_message(data))

        exp = claims.get("exp", data.get("exp", 0))
        if exp > time.time():
            return token
        expired_error = TokenExpiredError(
            f"Token expired at {time.ctime(exp)}. Run: d2l login"
        )

    try:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("D2L_TOKEN="):
                    return _load_env_token(
                        line.strip().split("=", 1)[1], ".env D2L_TOKEN"
                    )

        env_token = _load_env_token(os.environ.get("D2L_TOKEN"), "D2L_TOKEN")
        if env_token:
            return env_token
    except TokenNotFoundError:
        if expired_error is None:
            raise

    if expired_error:
        raise expired_error
    raise TokenNotFoundError("No bearer token found. Run: d2l login")


def token_info():
    """Return token metadata dict (no API call needed)."""
    data = _read_token_file()
    if data is None:
        return {"status": "not found", "error": "No token found. Run: d2l login"}

    token = data.get("token") if isinstance(data, dict) else None
    claims = _parse_bearer_claims(token)
    if not claims:
        return {
            "status": "unsupported",
            "auth_type": data.get("auth_type") if isinstance(data, dict) else None,
            "error": _unsupported_token_file_message(data),
        }

    exp = claims.get("exp", data.get("exp", 0))
    now = time.time()
    remaining = max(0, exp - now)
    return {
        "status": "valid" if exp > now else "expired",
        "auth_type": "bearer",
        "user_id": data.get("sub") or claims.get("sub"),
        "tenant": data.get("tenant") or claims.get("tenantid"),
        "expires_at": time.ctime(exp),
        "remaining_seconds": int(remaining),
        "remaining_minutes": round(remaining / 60, 1),
        "captured_at": time.ctime(data.get("captured_at", 0)),
    }


def make_session(token):
    """Create a requests.Session with Bearer auth and browser headers."""
    if not _parse_bearer_claims(token):
        raise TokenNotFoundError(
            "Saved token is not a valid D2L bearer token. Run: d2l login"
        )

    lms_host = get_lms_host()
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Origin": lms_host,
            "Referer": f"{lms_host}/",
            "User-Agent": USER_AGENT,
        }
    )
    return s
