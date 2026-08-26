import re
import json
from html.parser import HTMLParser
from urllib.parse import quote

import click
import requests

from d2l.config import get_syllabus_host
from d2l.errors import handle_errors, D2LError, ConfigError
from d2l.formatting import get_format, OutputFormat, output, section
from d2l.resolver import CourseResolver

_TERM_RE = re.compile(r"\b(Fall|Spring|Summer) Semester \d{4}\b", re.IGNORECASE)
_COURSE_CODE_RE = re.compile(r"^([A-Za-z]+)(\d+[A-Za-z]?)$")
_SLUG_SEPARATORS_RE = re.compile(r"[ _.\-/]+")


class _SyllabusTextParser(HTMLParser):
    """Extract readable syllabus text while ignoring CSS and JavaScript."""

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "div", "dl", "dt",
        "dd", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
        "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
        "p", "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead",
        "tr", "ul",
    }
    IGNORED_TAGS = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.IGNORED_TAGS and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def _syllabus_host():
    host = get_syllabus_host()
    if not host:
        raise ConfigError(
            "No SimpleSyllabus site configured for your school. If your school "
            "uses SimpleSyllabus, run: d2l setup --syllabus-host "
            "https://your-school.simplesyllabus.com"
        )
    return host


def _extract_crn(enrollment):
    """Extract CRN from D2L course code like CO.430.CS3305.10931.20264"""
    code = enrollment.get("OrgUnit", {}).get("Code", "")
    parts = code.split(".")
    if len(parts) >= 4:
        return parts[3]
    return None


def _course_identity(enrollment):
    """Return the expected term, subject, and course number from a D2L enrollment."""
    org = enrollment.get("OrgUnit", {})
    name = org.get("Name", "")
    code_parts = org.get("Code", "").split(".")
    term_match = _TERM_RE.search(name)
    term = term_match.group(0) if term_match else None
    subject = course_number = None
    if len(code_parts) >= 3:
        course_match = _COURSE_CODE_RE.match(code_parts[2])
        if course_match:
            subject, course_number = course_match.groups()
    return term, subject, course_number


def _find_syllabus(enrollment):
    """Find the best SimpleSyllabus result using CRN, term, and course identity."""
    crn = _extract_crn(enrollment)
    if not crn:
        return None
    r = requests.get(f"{_syllabus_host()}/api2/syllabus-search", params={"search": crn})
    if r.status_code != 200:
        return None
    candidates = [
        item for item in r.json().get("items", [])
        if crn in item.get("title", "") and item.get("syllabus_id")
    ]
    if not candidates:
        return None

    expected_term, expected_subject, expected_number = _course_identity(enrollment)
    org_name = enrollment.get("OrgUnit", {}).get("Name", "").lower()

    def score(item):
        value = 0
        if expected_term and item.get("term_name", "").lower() == expected_term.lower():
            value += 100
        if expected_subject and item.get("subject_name", "").lower() == expected_subject.lower():
            value += 25
        if expected_number and str(item.get("course_number", "")).lower() == expected_number.lower():
            value += 25
        subtitle = item.get("sub_title", "").lower()
        if subtitle and subtitle in org_name:
            value += 10
        return value

    return max(candidates, key=score)


def _build_doc_path(item):
    """Build SimpleSyllabus's canonical document path from search metadata."""
    display_name = f"{item.get('term_name', '')} {item.get('title', '')}".strip()
    if item.get("sub_title"):
        display_name += f" - {item['sub_title']}"
    slug = _SLUG_SEPARATORS_RE.sub("-", display_name)
    return f"{item['syllabus_id']}/{quote(slug, safe='-~')}"


def _fetch_syllabus_html(item):
    """Fetch the current public HTML representation of a syllabus."""
    r = requests.get(f"{_syllabus_host()}/api2/doc-html/{_build_doc_path(item)}")
    if r.status_code != 200:
        return None
    return r.text


def _extract_html_text(html):
    """Extract readable, line-preserving text from a full syllabus HTML page."""
    parser = _SyllabusTextParser()
    parser.feed(html or "")
    lines = []
    for raw_line in "".join(parser.parts).splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines)


@click.command()
@click.argument("course")
@click.option("--raw", is_flag=True, help="Output raw HTML components (for debugging)")
@click.pass_context
@handle_errors
def syllabus(ctx, course, raw):
    """Fetch syllabus from SimpleSyllabus. COURSE can be a name, code, or ID.

    No authentication needed — SimpleSyllabus data is public.

    Examples:
      d2l syllabus "data structures"
      d2l --md syllabus "calc"
      d2l --json syllabus "econ"
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    enrollment = resolver.resolve(course)
    name = enrollment["OrgUnit"]["Name"]
    crn = _extract_crn(enrollment)

    if not crn:
        raise D2LError(f"Could not extract CRN from course code: {enrollment['OrgUnit'].get('Code')}")

    syllabus_item = _find_syllabus(enrollment)
    if not syllabus_item:
        raise D2LError(f"No syllabus found on SimpleSyllabus for CRN {crn} ({name})")

    syllabus_id = syllabus_item["syllabus_id"]
    syllabus_html = _fetch_syllabus_html(syllabus_item)
    if not syllabus_html:
        raise D2LError(f"Could not fetch syllabus document: {syllabus_id}")

    syllabus_text = _extract_html_text(syllabus_html)
    page_url = f"{_syllabus_host()}/en-US/doc/{_build_doc_path(syllabus_item)}?mode=view"
    instructor = syllabus_item.get("instructor") or {}

    fmt = get_format()

    if fmt == OutputFormat.JSON:
        print(json.dumps({
            "course": name,
            "crn": crn,
            "syllabus_id": syllabus_id,
            "url": page_url,
            "title": syllabus_item.get("title"),
            "sub_title": syllabus_item.get("sub_title"),
            "term": syllabus_item.get("term_name"),
            "modified": syllabus_item.get("last_updated"),
            "editors": [instructor] if instructor else [],
            "properties": None,
            "components_html": [syllabus_html],
            "components_text": syllabus_text,
        }, indent=2, default=str))
        return

    if raw:
        print(syllabus_html)
        return

    # Human / Markdown output
    md = fmt == OutputFormat.MARKDOWN
    h1 = "#" if md else "==="
    h2 = "##" if md else "---"

    print(f"{h1} Syllabus: {syllabus_item.get('title', name)}")
    if syllabus_item.get("sub_title"):
        print(f"Course: {syllabus_item['sub_title']}")
    print(f"Term: {syllabus_item.get('term_name', '?')}")
    print(f"URL: {page_url}")
    print(f"Last modified: {syllabus_item.get('last_updated', '?')}")

    if instructor:
        instructor_name = instructor.get("full_name") or (
            f"{instructor.get('first_name', '')} {instructor.get('last_name', '')}".strip()
        )
        if instructor_name:
            print(f"Instructor(s): {instructor_name}")
    print()

    if syllabus_text:
        print(syllabus_text)
