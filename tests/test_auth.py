import base64
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l import auth
from d2l.commands import auth_cmd
from d2l.errors import TokenNotFoundError


class AuthTests(unittest.TestCase):
    def make_token(self, **claims):
        payload = {
            "iss": auth.TOKEN_ISSUER,
            "aud": auth.TOKEN_AUDIENCE,
            "exp": int(time.time()) + 3600,
            "sub": "12345",
            "tenantid": "tenant-1",
        }
        payload.update(claims)

        def encode(part):
            raw = json.dumps(part, separators=(",", ":")).encode()
            return base64.urlsafe_b64encode(raw).decode().rstrip("=")

        return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode(payload)}.sig"

    def test_load_token_rejects_legacy_browser_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token.json"
            token_file.write_text(json.dumps({"auth_type": "browser-session", "cookies": []}))
            with patch.object(auth, "TOKEN_FILE", token_file):
                with self.assertRaises(TokenNotFoundError) as ctx:
                    auth.load_token()
        self.assertIn("unsupported auth_type=browser-session", str(ctx.exception))

    def test_load_token_accepts_valid_saved_bearer(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token.json"
            token = self.make_token()
            token_file.write_text(json.dumps({"token": token, "exp": int(time.time()) + 3600}))
            with patch.object(auth, "TOKEN_FILE", token_file):
                loaded = auth.load_token()
        self.assertEqual(loaded, token)

    def test_make_session_rejects_non_d2l_bearer(self):
        token = self.make_token(iss="https://example.com/auth")
        with self.assertRaises(TokenNotFoundError):
            auth.make_session(token)

    def test_token_info_reports_unsupported_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token.json"
            token_file.write_text(json.dumps({"auth_type": "browser-session"}))
            with patch.object(auth, "TOKEN_FILE", token_file):
                info = auth.token_info()
        self.assertEqual(info["status"], "unsupported")
        self.assertEqual(info["auth_type"], "browser-session")
        self.assertIn("unsupported auth_type=browser-session", info["error"])

    def test_token_command_fails_clearly_for_unsupported_auth(self):
        runner = CliRunner()
        with patch.object(auth_cmd, "token_info", return_value={
            "status": "unsupported",
            "auth_type": "browser-session",
            "error": "token.json contains unsupported auth_type=browser-session. Run: d2l login",
        }):
            result = runner.invoke(auth_cmd.token)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("unsupported auth_type=browser-session", result.output)


if __name__ == "__main__":
    unittest.main()
