import json
import os
from pathlib import Path

from d2l.errors import ConfigError

LP_VERSION = "1.47"
LE_VERSION = "1.80"
BAS_VERSION = "2.2"

TOKEN_DIR = Path.home() / ".d2l"
TOKEN_FILE = TOKEN_DIR / "token.json"
CONFIG_FILE = TOKEN_DIR / "config.json"
BROWSER_PROFILE = TOKEN_DIR / "browser_profile"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


def load_config():
    """Read ~/.d2l/config.json. Returns {} when missing or unreadable."""
    try:
        data = json.loads(CONFIG_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(updates):
    """Merge updates into ~/.d2l/config.json and return the new config."""
    config = load_config()
    config.update(updates)
    config = {k: v for k, v in config.items() if v is not None}
    TOKEN_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
    return config


def normalize_host(url):
    """Normalize a Brightspace URL to https://host (no path, no trailing slash)."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    scheme, _, rest = url.partition("://")
    host = rest.split("/")[0]
    if not host or "." not in host:
        return None
    return f"{scheme}://{host}"


def get_lms_host(required=True):
    """Resolve the Brightspace host: D2L_HOST env > ~/.d2l/config.json.

    Raises ConfigError when required and unconfigured, with the fix spelled out
    so both students and agents know the exact next command.
    """
    host = normalize_host(os.environ.get("D2L_HOST") or load_config().get("lms_host"))
    if host or not required:
        return host
    raise ConfigError(
        "No school configured. Run: d2l setup "
        "(or d2l setup --host https://your-school.brightspace-url)"
    )


def get_syllabus_host():
    """SimpleSyllabus host, or None when the school doesn't have one configured."""
    return normalize_host(
        os.environ.get("D2L_SYLLABUS_HOST") or load_config().get("syllabus_host")
    )
