import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l.commands.onboard import course_fingerprint, _render_sop, _write_state


class OnboardTests(unittest.TestCase):
    def enrollment(self, course_id, name, code):
        return {"OrgUnit": {"Id": course_id, "Name": name, "Code": code}}

    def test_course_fingerprint_is_stable_across_order(self):
        courses_a = [
            self.enrollment(2, "Biology", "BIO101"),
            self.enrollment(1, "Algebra", "MATH101"),
        ]
        courses_b = list(reversed(courses_a))
        self.assertEqual(course_fingerprint(courses_a), course_fingerprint(courses_b))
        self.assertTrue(course_fingerprint(courses_a).startswith("sha256:"))

    def test_course_fingerprint_changes_when_course_list_changes(self):
        base = [self.enrollment(1, "Algebra", "MATH101")]
        changed = [
            self.enrollment(1, "Algebra", "MATH101"),
            self.enrollment(2, "Biology", "BIO101"),
        ]
        self.assertNotEqual(course_fingerprint(base), course_fingerprint(changed))

    def test_render_sop_includes_sentinel_guidance(self):
        courses = [{"id": 1, "name": "Algebra", "code": "MATH101"}]
        sop = _render_sop(
            courses,
            {"1": {"assignment_count": 2, "quiz_count": 3, "has_content_toc": True}},
            {"1": {
                "source_of_truth": "Syllabus first",
                "weekly_rhythm": "Mondays",
                "grading_style": "Quizzes",
                "external_tools": "None",
                "agent_help": "Reminders",
                "stop_and_ask": "Missing syllabus",
            }},
            "2026-05-09T00:00:00Z",
        )
        self.assertIn("# D2L Course Operations SOP", sop)
        self.assertIn("Syllabus first", sop)
        self.assertIn(".d2l/onboarding.json", sop)
        self.assertIn("d2l --md assignments 1", sop)

    def test_write_state_records_sop_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / ".d2l" / "onboarding.json"
            output_path = Path("D2L_COURSE_SOP.md")
            data = _write_state(
                state_path,
                output_path,
                "sha256:abc",
                [{"id": 1, "name": "Algebra", "code": "MATH101"}],
                "2026-05-09T00:00:00Z",
            )
            self.assertTrue(state_path.exists())
            loaded = json.loads(state_path.read_text())
            self.assertEqual(data["course_fingerprint"], "sha256:abc")
            self.assertEqual(loaded["sop_file"], "D2L_COURSE_SOP.md")


if __name__ == "__main__":
    unittest.main()
