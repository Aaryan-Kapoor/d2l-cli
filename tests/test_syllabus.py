import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d2l.commands import syllabus


class SyllabusTests(unittest.TestCase):
    def enrollment(self, name, code):
        return {"OrgUnit": {"Name": name, "Code": code}}

    @patch.object(syllabus.requests, "get")
    def test_find_syllabus_prefers_current_term_and_course_identity(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {
            "items": [
                {
                    "syllabus_id": "wrong-old-course",
                    "title": "CYBR 4893 Section W01 (84881)",
                    "sub_title": "IoT: Apps & Security",
                    "term_name": "Fall Semester 2025",
                    "subject_name": "CYBR",
                    "course_number": "4893",
                },
                {
                    "syllabus_id": "correct-history",
                    "title": "HIST 2112 W01 (84881)",
                    "sub_title": "Survey of U.S. History II",
                    "term_name": "Fall Semester 2026",
                    "subject_name": "HIST",
                    "course_number": "2112",
                },
            ]
        }
        get.return_value = response

        with patch.object(
            syllabus,
            "_syllabus_host",
            return_value="https://example.simplesyllabus.com",
        ):
            found = syllabus._find_syllabus(
                self.enrollment(
                    "Survey of U.S. History II Section W01 Fall Semester 2026 CO",
                    "CO.430.HIST2112.84881.20272",
                )
            )

        self.assertEqual(found["syllabus_id"], "correct-history")

    def test_build_doc_path_matches_current_simplesyllabus_route(self):
        item = {
            "syllabus_id": "fv0jgyz8c",
            "title": "AI 3642 01 (87707)",
            "sub_title": "Artificial Intelligence",
            "term_name": "Fall Semester 2026",
        }
        self.assertEqual(
            syllabus._build_doc_path(item),
            "fv0jgyz8c/Fall-Semester-2026-AI-3642-01-%2887707%29-Artificial-Intelligence",
        )

    @patch.object(syllabus.requests, "get")
    def test_fetch_syllabus_uses_doc_html_endpoint(self, get):
        response = Mock(status_code=200, text="<main><h1>Course</h1><p>Policy text</p></main>")
        get.return_value = response
        item = {
            "syllabus_id": "abc123",
            "title": "CS 1000 01 (12345)",
            "sub_title": "Computing",
            "term_name": "Fall Semester 2026",
        }

        with patch.object(
            syllabus,
            "_syllabus_host",
            return_value="https://example.simplesyllabus.com",
        ):
            html = syllabus._fetch_syllabus_html(item)

        self.assertIn("Policy text", html)
        self.assertIn("/api2/doc-html/abc123/", get.call_args.args[0])

    def test_extract_html_text_ignores_styles_and_scripts(self):
        html = """
        <style>.secret { display: none; }</style>
        <main><h1>Grading</h1><p>Exams: 60%</p><p>Projects: 40%</p></main>
        <script>window.secret = true;</script>
        """
        text = syllabus._extract_html_text(html)
        self.assertIn("Grading", text)
        self.assertIn("Exams: 60%", text)
        self.assertNotIn("display: none", text)
        self.assertNotIn("window.secret", text)


if __name__ == "__main__":
    unittest.main()
