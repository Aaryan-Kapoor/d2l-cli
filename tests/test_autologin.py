import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l import cli as cli_mod
from d2l import config
from d2l.commands import auth_cmd
from d2l.errors import TokenExpiredError, TokenNotFoundError


class AttemptAutoLoginTests(unittest.TestCase):
    def test_disabled_by_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(config, "BROWSER_PROFILE", Path(tmp)):
                with patch.dict(os.environ, {auth_cmd.AUTO_LOGIN_DISABLED_ENV: "1"}):
                    self.assertFalse(auth_cmd.attempt_auto_login())

    def test_no_browser_profile_fails_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(config, "BROWSER_PROFILE", Path(tmp) / "nope"):
                os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
                self.assertFalse(auth_cmd.attempt_auto_login())

    def test_runs_quiet_headless_capture_when_profile_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(config, "BROWSER_PROFILE", Path(tmp)):
                os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
                with patch.object(auth_cmd, "_playwright_available", return_value=True):
                    with patch.object(auth_cmd, "_capture_and_save", return_value=True) as cap:
                        self.assertTrue(auth_cmd.attempt_auto_login())
        cap.assert_called_once_with(headless=True, channel="auto", quiet=True)

    def test_never_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(config, "BROWSER_PROFILE", Path(tmp)):
                os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
                with patch.object(auth_cmd, "_playwright_available", return_value=True):
                    with patch.object(auth_cmd, "_capture_and_save", side_effect=RuntimeError("boom")):
                        self.assertFalse(auth_cmd.attempt_auto_login())


class ResolveTokenTests(unittest.TestCase):
    def test_valid_token_needs_no_refresh(self):
        with patch.object(cli_mod, "load_token", return_value="tok"):
            with patch.object(auth_cmd, "attempt_auto_login") as auto:
                self.assertEqual(cli_mod._resolve_token(), "tok")
        auto.assert_not_called()

    def test_expired_token_refreshes_and_retries(self):
        with patch.object(cli_mod, "load_token", side_effect=[TokenExpiredError("old"), "fresh"]):
            with patch.object(auth_cmd, "attempt_auto_login", return_value=True):
                self.assertEqual(cli_mod._resolve_token(), "fresh")

    def test_failed_refresh_tells_user_to_login_interactively(self):
        with patch.object(cli_mod, "load_token", side_effect=TokenNotFoundError("none")):
            with patch.object(auth_cmd, "attempt_auto_login", return_value=False):
                with self.assertRaises(TokenNotFoundError) as ctx:
                    cli_mod._resolve_token()
        self.assertIn("d2l login", str(ctx.exception))
        self.assertIn("browser window will open", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
