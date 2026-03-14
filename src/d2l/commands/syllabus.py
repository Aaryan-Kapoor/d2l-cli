import re
import json

import click
import requests

from d2l.errors import handle_errors, D2LError
from d2l.formatting import get_format, OutputFormat, output, section
from d2l.resolver import CourseResolver

SYLLABUS_SEARCH_URL = "https://kennesaw.simplesyllabus.com/api2/syllabus-search"
SYLLABUS_FULL_URL = "https://kennesaw.simplesyllabus.com/api2/doc-full-page-get"

# Regex to strip HTML tags for plain text extraction
_TAG_RE = re.compile(r"<[^>]+>")


def _extract_crn(enrollment):
    """Extract CRN from D2L course code like CO.430.CS3305.10931.20264"""
    code = enrollment.get("OrgUnit", {}).get("Code", "")
    parts = code.split(".")
    if len(parts) >= 4:
        return parts[3]
    return None


def _find_syllabus_id(crn):
    """Search SimpleSyllabus for a course by CRN, return syllabus_id or None."""
    r = requests.get(SYLLABUS_SEARCH_URL, params={"search": crn})
    if r.status_code != 200:
        return None
    data = r.json()
    for item in data.get("items", []):
        if crn in item.get("title", ""):
            return item.get("syllabus_id")
    return None


def _fetch_syllabus(syllabus_id):
    """Fetch full syllabus document from SimpleSyllabus. Returns doc_data dict."""
    r = requests.get(SYLLABUS_FULL_URL, params={"code": syllabus_id})
    if r.status_code != 200:
        return None
    data = r.json()
    items = data.get("items", [])
    if not items:
        return None
    return items[0].get("doc_data")


def _extract_text(components):
    """Extract readable text from syllabus HTML components."""
    parts = []
    for comp in components:
        html = comp.get("html", "")
        text = _TAG_RE.sub("", html).strip()
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        if text and len(text) > 5:
            parts.append(text)
    return "\n\n".join(parts)


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

    syllabus_id = _find_syllabus_id(crn)
    if not syllabus_id:
        raise D2LError(f"No syllabus found on SimpleSyllabus for CRN {crn} ({name})")

    doc = _fetch_syllabus(syllabus_id)
    if not doc:
        raise D2LError(f"Could not fetch syllabus document: {syllabus_id}")

    fmt = get_format()

    if fmt == OutputFormat.JSON:
        print(json.dumps({
            "course": name,
            "crn": crn,
            "syllabus_id": syllabus_id,
            "url": f"https://kennesaw.simplesyllabus.com/en-US/doc/{syllabus_id}/",
            "title": doc.get("title"),
            "sub_title": doc.get("sub_title"),
            "term": doc.get("term", {}).get("name"),
            "modified": doc.get("modified"),
            "editors": doc.get("editors", []),
            "properties": doc.get("properties"),
            "components_html": [c.get("html", "") for c in (doc.get("components") or [])],
            "components_text": _extract_text(doc.get("components") or []),
        }, indent=2, default=str))
        return

    if raw:
        for comp in (doc.get("components") or []):
            print(comp.get("html", ""))
            print()
        return

    # Human / Markdown output
    md = fmt == OutputFormat.MARKDOWN
    h1 = "#" if md else "==="
    h2 = "##" if md else "---"

    print(f"{h1} Syllabus: {doc.get('title', name)}")
    if doc.get("sub_title"):
        print(f"Course: {doc['sub_title']}")
    print(f"Term: {doc.get('term', {}).get('name', '?')}")
    print(f"URL: https://kennesaw.simplesyllabus.com/en-US/doc/{syllabus_id}/")
    print(f"Last modified: {doc.get('modified', '?')}")

    editors = doc.get("editors", [])
    if editors:
        names = [f"{e.get('first_name', '')} {e.get('last_name', '')}".strip() for e in editors]
        print(f"Instructor(s): {', '.join(names)}")
    print()

    components = doc.get("components") or []
    text = _extract_text(components)
    if text:
        print(text)
