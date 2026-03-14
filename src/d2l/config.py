from pathlib import Path

LMS_HOST = "https://kennesaw.view.usg.edu"
TENANT_ID = "857f39d7-a377-40a5-9272-5bb63ea6aafe"

LP_VERSION = "1.47"
LE_VERSION = "1.80"
BAS_VERSION = "2.2"
EP_VERSION = "2.3"
LR_VERSION = "1.0"

TOKEN_DIR = Path.home() / ".d2l"
TOKEN_FILE = TOKEN_DIR / "token.json"
BROWSER_PROFILE = TOKEN_DIR / "browser_profile"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
