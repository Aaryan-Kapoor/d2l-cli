import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import click

from d2l.errors import handle_errors, TokenExpiredError, TokenNotFoundError
from d2l.formatting import get_format, OutputFormat, output
from d2l.resolver import CourseResolver

ONBOARDING_VERSION = 1
DEFAULT_OUTPUT = "D2L_COURSE_SOP.md"
DEFAULT_STATE_DIR = ".d2l"
DEFAULT_STATE_FILE = "onboarding.json"


def _course_record(enrollment):
    ou = enrollment.get("OrgUnit", {})
    return {
        "id": ou.get("Id"),
        "name": ou.get("Name"),
        "code": ou.get("Code"),
    }


def course_fingerprint(courses):
    """Stable fingerprint for the active course set."""
    normalized = sorted(
        (_course_record(c) for c in courses),
        key=lambda c: (str(c.get("id") or ""), c.get("code") or "", c.get("name") or ""),
    )
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _safe(fn, default=None):
    """Best-effort fetch: missing/forbidden course data degrades to a default,
    but auth failures propagate so onboarding fails loudly instead of writing
    a blank SOP."""
    try:
        return fn()
    except (TokenExpiredError, TokenNotFoundError):
        raise
    except Exception:
        return default


def _prompt_text(label, default=""):
    return click.prompt(label, default=default, show_default=False).strip()


def _course_context(client, course_id):
    assignments = _safe(lambda: client.assignments(course_id), []) or []
    quizzes = _safe(lambda: client.quizzes(course_id), []) or []
    content = _safe(lambda: client.content_toc(course_id), None)
    return {
        "assignment_count": len(assignments) if isinstance(assignments, list) else None,
        "quiz_count": len(quizzes) if isinstance(quizzes, list) else None,
        "has_content_toc": bool(content),
    }


def _default_answers():
    return {
        "source_of_truth": "D2L due dates, syllabus, and course content. Confirm course-specific quirks with the user.",
        "weekly_rhythm": "Unknown yet. Ask the user or infer from syllabus/content after review.",
        "grading_style": "Unknown yet. Fetch the syllabus before making grade-policy claims.",
        "external_tools": "None known yet.",
        "agent_help": "Track due dates, summarize course changes, and stop when required data is missing.",
        "stop_and_ask": "Ask before relying on stale, partial, or ambiguous course data.",
    }


def _interview_course(course, non_interactive=False):
    if non_interactive:
        return _default_answers()

    name = course.get("name") or course.get("id")
    click.echo(f"\n--- {name} ---")
    return {
        "source_of_truth": _prompt_text(
            "Where are the real deadlines/source of truth?",
            "D2L due dates, syllabus, and course content",
        ),
        "weekly_rhythm": _prompt_text(
            "Weekly rhythm / recurring pattern?",
            "Unknown yet",
        ),
        "grading_style": _prompt_text(
            "Grading style / what matters most?",
            "Unknown yet; fetch syllabus before grade-policy claims",
        ),
        "external_tools": _prompt_text(
            "External tools/sites/docs?",
            "None known",
        ),
        "agent_help": _prompt_text(
            "What should an agent proactively help with?",
            "Track due dates and summarize course changes",
        ),
        "stop_and_ask": _prompt_text(
            "When should an agent stop and ask you?",
            "When required data is missing, stale, partial, or ambiguous",
        ),
    }


def _render_sop(courses, contexts, answers, generated_at):
    lines = [
        "# D2L Course Operations SOP",
        "",
        f"Generated: {generated_at}",
        "",
        "This file captures how an AI agent should work with the user's active D2L courses. It is intentionally user-specific, but should not contain passwords, tokens, or private credentials.",
        "",
        "## Global Rules",
        "",
        "- Use `d2l` only for read-only Brightspace data.",
        "- Prefer `--md` or `--json` when processing CLI output.",
        "- Put global flags before the command, e.g. `d2l --md grades COURSE`.",
        "- If auth fails, try `d2l login --headless` first. If that fails, ask before launching `d2l login` for interactive browser login.",
        "- Do not scrape D2L course data through the browser. Browser login is only for authentication.",
        "- Fetch the syllabus before answering policy, grading-weight, prerequisite, or instructor-rule questions when a syllabus is available.",
        "- If required data cannot be fetched, stop and report the blocker instead of guessing.",
        "",
        "## Active Courses",
        "",
        "| ID | Name | Code | Assignments | Quizzes | Content TOC |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]

    for course in courses:
        cid = course.get("id")
        ctx = contexts.get(str(cid), {})
        lines.append(
            f"| {cid or ''} | {course.get('name') or ''} | {course.get('code') or ''} | "
            f"{ctx.get('assignment_count', '') if ctx.get('assignment_count') is not None else ''} | "
            f"{ctx.get('quiz_count', '') if ctx.get('quiz_count') is not None else ''} | "
            f"{'yes' if ctx.get('has_content_toc') else 'unknown/no'} |"
        )

    lines += ["", "## Per-Course Workflows", ""]

    for course in courses:
        cid = course.get("id")
        ans = answers.get(str(cid), _default_answers())
        title = course.get("name") or f"Course {cid}"
        lines += [
            f"### {title}",
            "",
            f"- **Org unit ID:** `{cid}`",
            f"- **Code:** `{course.get('code') or ''}`",
            f"- **Source of truth:** {ans.get('source_of_truth') or 'Unknown'}",
            f"- **Weekly rhythm:** {ans.get('weekly_rhythm') or 'Unknown'}",
            f"- **Grading style / priorities:** {ans.get('grading_style') or 'Unknown'}",
            f"- **External tools:** {ans.get('external_tools') or 'None known'}",
            f"- **Agent help:** {ans.get('agent_help') or 'Track due dates and summarize changes'}",
            f"- **Stop and ask when:** {ans.get('stop_and_ask') or 'Required data is missing or ambiguous'}",
            "",
            "Useful commands:",
            "",
            "```bash",
            f"d2l --md syllabus {cid}",
            f"d2l --md assignments {cid}",
            f"d2l --md quizzes {cid}",
            f"d2l --md content {cid} --toc",
            f"d2l --md grades {cid}",
            "```",
            "",
        ]

    lines += [
        "## Maintenance",
        "",
        "- Re-run onboarding when the active course list changes or a new term starts.",
        "- If `.d2l/onboarding.json` exists and its course fingerprint still matches active courses, read this SOP instead of repeating onboarding.",
        "- If the fingerprint changed, ask the user whether to update the SOP.",
        "",
    ]
    return "\n".join(lines)


def _write_state(state_path, output_path, fingerprint, courses, generated_at):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": ONBOARDING_VERSION,
        "completed_at": generated_at,
        "sop_file": str(output_path),
        "course_fingerprint": fingerprint,
        "courses": courses,
    }
    state_path.write_text(json.dumps(data, indent=2, default=str))
    return data


@click.command()
@click.option("--output", "output_file", default=DEFAULT_OUTPUT, show_default=True, help="SOP markdown file to write")
@click.option("--state-dir", default=DEFAULT_STATE_DIR, show_default=True, help="Directory for onboarding state")
@click.option("--force", is_flag=True, help="Re-run onboarding even if the current course fingerprint is already onboarded")
@click.option("--yes", "non_interactive", is_flag=True, help="Do not prompt; write a starter SOP with default placeholders")
@click.pass_context
@handle_errors
def onboard(ctx, output_file, state_dir, force, non_interactive):
    """Create or refresh a course-operations SOP for active D2L courses."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    enrollments = resolver.list_courses()
    courses = [_course_record(e) for e in enrollments]
    fingerprint = course_fingerprint(enrollments)

    output_path = Path(output_file)
    state_path = Path(state_dir) / DEFAULT_STATE_FILE

    if state_path.exists() and output_path.exists() and not force:
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}
        if state.get("course_fingerprint") == fingerprint:
            result = {
                "status": "already_onboarded",
                "sop_file": str(output_path),
                "state_file": str(state_path),
                "course_count": len(courses),
            }
            if get_format() == OutputFormat.JSON:
                output(result)
            else:
                click.echo(f"Onboarding already complete: {output_path}")
                click.echo("Course list fingerprint matches active courses. Use --force to refresh.")
            return
        if not non_interactive:
            if not click.confirm(
                "Active course list changed since onboarding. Update the SOP now?",
                default=False,
            ):
                click.echo("Onboarding unchanged.")
                return
            # Confirming the update already covers overwriting the SOP file.
            force = True

    if output_path.exists() and not force and not non_interactive:
        if not click.confirm(f"Overwrite existing {output_path}?", default=False):
            click.echo("Onboarding cancelled.")
            return

    if not non_interactive:
        click.echo("This will create a course-operations SOP for your active D2L courses.")
        click.echo("Answer briefly. You can edit the markdown file afterward.")

    contexts = {}
    answers = {}
    for course in courses:
        cid = str(course.get("id"))
        contexts[cid] = _course_context(client, course.get("id"))
        answers[cid] = _interview_course(course, non_interactive=non_interactive)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sop = _render_sop(courses, contexts, answers, generated_at)
    output_path.write_text(sop)
    state = _write_state(state_path, output_path, fingerprint, courses, generated_at)

    result = {
        "status": "onboarded",
        "sop_file": str(output_path),
        "state_file": str(state_path),
        "course_count": len(courses),
        "course_fingerprint": fingerprint,
    }
    if get_format() == OutputFormat.JSON:
        output({**result, "state": state})
    else:
        click.echo(f"Wrote SOP: {output_path}")
        click.echo(f"Wrote state: {state_path}")
        click.echo(f"Courses onboarded: {len(courses)}")
