import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l.commands import update_cmd


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.commands = []

        def record(cmd):
            self.commands.append(cmd)
            return 0

        self._run = patch.object(update_cmd, "_run", side_effect=record)
        self._extras = patch.object(update_cmd, "_extras", return_value="[login]")
        self._run.start()
        self._extras.start()

    def tearDown(self):
        self._run.stop()
        self._extras.stop()

    def test_editable_checkout_only_pulls(self):
        origin = {"url": "file:///home/me/d2l-cli", "dir_info": {"editable": True}}
        with patch.object(update_cmd, "_direct_url", return_value=origin):
            result = self.runner.invoke(update_cmd.update)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.commands[0][:2], ["git", "-C"])
        self.assertIn("/home/me/d2l-cli", self.commands[0])

    def test_non_editable_checkout_pulls_then_reinstalls(self):
        # PEP 610 records a plain local-dir install as an empty dir_info dict
        origin = {"url": "file:///home/me/d2l-cli", "dir_info": {}}
        with patch.object(update_cmd, "_direct_url", return_value=origin):
            result = self.runner.invoke(update_cmd.update)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(self.commands), 2)
        self.assertIn("pip", self.commands[1])
        self.assertIn("/home/me/d2l-cli[login]", self.commands[1])

    def test_package_install_upgrades_from_pypi(self):
        with patch.object(update_cmd, "_direct_url", return_value=None):
            result = self.runner.invoke(update_cmd.update)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(self.commands), 1)
        self.assertIn("--upgrade", self.commands[0])
        self.assertEqual(self.commands[0][-1], "d2l-cli[login]")
        self.assertNotIn("--force-reinstall", self.commands[0])

    def test_ref_option_installs_from_git(self):
        with patch.object(update_cmd, "_direct_url", return_value=None):
            result = self.runner.invoke(update_cmd.update, ["--ref", "v0.2.0"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(self.commands), 1)
        self.assertIn("--force-reinstall", self.commands[0])
        self.assertIn(f"d2l-cli[login] @ {update_cmd.GIT_URL}", self.commands[0][-1])
        self.assertTrue(self.commands[0][-1].endswith(".git@v0.2.0"))

    def test_failed_pull_aborts(self):
        origin = {"url": "file:///home/me/d2l-cli", "dir_info": {"editable": True}}
        with patch.object(update_cmd, "_direct_url", return_value=origin):
            with patch.object(update_cmd, "_run", return_value=1):
                result = self.runner.invoke(update_cmd.update)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("git pull failed", result.output)


if __name__ == "__main__":
    unittest.main()
