import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l import config
from d2l.errors import ConfigError
from d2l.formatting import set_format, OutputFormat


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmp.name)
        self._patches = [
            patch.object(config, "TOKEN_DIR", tmp_path),
            patch.object(config, "CONFIG_FILE", tmp_path / "config.json"),
            patch.dict(os.environ, {}, clear=False),
        ]
        for p in self._patches:
            p.start()
        os.environ.pop("D2L_HOST", None)
        os.environ.pop("D2L_SYLLABUS_HOST", None)

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def test_normalize_host(self):
        self.assertEqual(
            config.normalize_host("kennesaw.view.usg.edu/d2l/home"),
            "https://kennesaw.view.usg.edu",
        )
        self.assertEqual(
            config.normalize_host("https://gastate.view.usg.edu/"),
            "https://gastate.view.usg.edu",
        )
        self.assertIsNone(config.normalize_host(""))
        self.assertIsNone(config.normalize_host("not a url"))

    def test_get_lms_host_raises_when_unconfigured(self):
        with self.assertRaises(ConfigError) as ctx:
            config.get_lms_host()
        self.assertIn("d2l setup", str(ctx.exception))
        self.assertIsNone(config.get_lms_host(required=False))

    def test_env_var_overrides_config_file(self):
        config.save_config({"lms_host": "https://kennesaw.view.usg.edu"})
        self.assertEqual(config.get_lms_host(), "https://kennesaw.view.usg.edu")
        os.environ["D2L_HOST"] = "https://gastate.view.usg.edu"
        try:
            self.assertEqual(config.get_lms_host(), "https://gastate.view.usg.edu")
        finally:
            del os.environ["D2L_HOST"]

    def test_save_config_drops_none_values(self):
        config.save_config({"lms_host": "https://x.view.usg.edu", "syllabus_host": "https://x.simplesyllabus.com"})
        config.save_config({"syllabus_host": None})
        stored = json.loads(config.CONFIG_FILE.read_text())
        self.assertNotIn("syllabus_host", stored)
        self.assertEqual(stored["lms_host"], "https://x.view.usg.edu")


class SetupCommandTests(unittest.TestCase):
    def setUp(self):
        set_format(OutputFormat.HUMAN)
        self.tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmp.name)
        self._patches = [
            patch.object(config, "TOKEN_DIR", tmp_path),
            patch.object(config, "CONFIG_FILE", tmp_path / "config.json"),
        ]
        for p in self._patches:
            p.start()
        os.environ.pop("D2L_HOST", None)
        self.runner = CliRunner()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def invoke(self, *args):
        from d2l.cli import cli
        return self.runner.invoke(cli, list(args))

    def test_setup_with_school_preset_alias(self):
        result = self.invoke("setup", "--school", "gsu")
        self.assertEqual(result.exit_code, 0, result.output)
        stored = json.loads(config.CONFIG_FILE.read_text())
        self.assertEqual(stored["lms_host"], "https://gastate.view.usg.edu")
        self.assertEqual(stored["school"], "Georgia State University")

    def test_setup_with_raw_host(self):
        result = self.invoke("setup", "--host", "myschool.brightspace.com/d2l/home")
        self.assertEqual(result.exit_code, 0, result.output)
        stored = json.loads(config.CONFIG_FILE.read_text())
        self.assertEqual(stored["lms_host"], "https://myschool.brightspace.com")

    def test_setup_rejects_unknown_school(self):
        result = self.invoke("setup", "--school", "nowhere u")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Unknown school", result.output)

    def test_setup_without_args_fails_when_not_a_tty(self):
        result = self.invoke("setup")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("--school", result.output)

    def test_doctor_reports_setup_as_next_step_when_unconfigured(self):
        from d2l import auth
        with patch.object(auth, "TOKEN_FILE", Path(self.tmp.name) / "token.json"):
            result = self.invoke("--json", "doctor")
        set_format(OutputFormat.HUMAN)
        self.assertEqual(result.exit_code, 1)
        data = json.loads(result.output)
        self.assertEqual(data["status"], "action_needed")
        self.assertEqual(data["next_step"], "d2l setup")


class DownloadSanitizeTests(unittest.TestCase):
    def test_safe_filename_strips_traversal(self):
        from d2l.commands.download import _safe_filename
        self.assertEqual(_safe_filename("../../evil.sh", "fb"), "evil.sh")
        self.assertEqual(_safe_filename("/etc/passwd", "fb"), "passwd")
        self.assertEqual(_safe_filename("..\\..\\evil.exe", "fb"), "evil.exe")
        self.assertEqual(_safe_filename("notes.pdf", "fb"), "notes.pdf")
        self.assertEqual(_safe_filename("..", "fb"), "fb")
        self.assertEqual(_safe_filename("", "fb"), "fb")


if __name__ == "__main__":
    unittest.main()
