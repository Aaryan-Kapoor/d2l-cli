import json
from importlib.metadata import version as pkg_version
from pathlib import Path

import click

from d2l.auth import load_token, make_session, token_info
from d2l.client import D2LClient
from d2l.config import get_lms_host, get_syllabus_host
from d2l.formatting import get_format, OutputFormat, output
from d2l.resolver import CourseResolver

ONBOARD_SOP = "D2L_COURSE_SOP.md"
ONBOARD_STATE = Path(".d2l") / "onboarding.json"


def _check(name, ok, detail, next_step=None, info_only=False):
    return {
        "check": name,
        "ok": bool(ok),
        "detail": detail,
        "next_step": next_step,
        "info_only": info_only,
    }


def _run_checks():
    checks = []

    try:
        ver = pkg_version("d2l-cli")
    except Exception:
        ver = "unknown"
    checks.append(_check("cli", True, f"d2l-cli {ver}"))

    host = get_lms_host(required=False)
    checks.append(_check(
        "config", host is not None,
        f"Brightspace: {host}" if host else "No school configured",
        next_step=None if host else "d2l setup",
    ))

    syllabus_host = get_syllabus_host()
    checks.append(_check(
        "syllabus", True,
        f"SimpleSyllabus: {syllabus_host}" if syllabus_host
        else "SimpleSyllabus not configured (syllabus command disabled)",
        info_only=True,
    ))

    info = token_info()
    token_ok = info.get("status") == "valid"
    detail = (
        f"Token valid, {info.get('remaining_minutes')} min remaining"
        if token_ok else info.get("error") or f"Token {info.get('status')}"
    )
    checks.append(_check("token", token_ok, detail, next_step=None if token_ok else "d2l login"))

    client = None
    if host and token_ok:
        try:
            client = D2LClient(make_session(load_token()))
            me = client.whoami()
            name = f"{me.get('FirstName', '')} {me.get('LastName', '')}".strip()
            checks.append(_check("api", True, f"Authenticated as {name or me.get('UniqueName')}"))
        except Exception as e:
            client = None
            checks.append(_check("api", False, f"API call failed: {e}", next_step="d2l login"))
    else:
        checks.append(_check("api", False, "Skipped (fix config/token first)"))

    course_fp = None
    if client:
        try:
            enrollments = CourseResolver(client).list_courses()
            from d2l.commands.onboard import course_fingerprint
            course_fp = course_fingerprint(enrollments)
            checks.append(_check("courses", len(enrollments) > 0, f"{len(enrollments)} active course(s)"))
        except Exception as e:
            checks.append(_check("courses", False, f"Could not list courses: {e}"))
    else:
        checks.append(_check("courses", False, "Skipped (fix config/token first)"))

    if not Path(ONBOARD_SOP).exists() or not ONBOARD_STATE.exists():
        checks.append(_check(
            "onboarding", False,
            "Not onboarded in this directory (no SOP/state file)",
            next_step="d2l onboard", info_only=True,
        ))
    else:
        try:
            state = json.loads(ONBOARD_STATE.read_text())
        except (OSError, json.JSONDecodeError):
            state = {}
        stored_fp = state.get("course_fingerprint")
        if course_fp and stored_fp == course_fp:
            checks.append(_check("onboarding", True, f"Complete and current ({ONBOARD_SOP})", info_only=True))
        elif course_fp:
            checks.append(_check(
                "onboarding", False,
                "Course list changed since onboarding",
                next_step="d2l onboard", info_only=True,
            ))
        else:
            checks.append(_check(
                "onboarding", True,
                f"SOP present ({ONBOARD_SOP}); freshness unknown (API unavailable)",
                info_only=True,
            ))
    return checks


@click.command()
def doctor():
    """Diagnose setup state: config, auth, API access, courses, onboarding.

    Designed for agents: `d2l --json doctor` reports every check with a
    `next_step` command, so the next required action is never a guess.
    Exits non-zero when a required check fails.
    """
    checks = _run_checks()
    required_failed = [c for c in checks if not c["ok"] and not c["info_only"]]
    next_steps = [c["next_step"] for c in checks if c["next_step"]]
    result = {
        "status": "ready" if not required_failed else "action_needed",
        "checks": checks,
        "next_step": next_steps[0] if next_steps else None,
    }

    if get_format() == OutputFormat.JSON:
        output(result)
    else:
        for c in checks:
            mark = "ok" if c["ok"] else ("--" if c["info_only"] else "!!")
            line = f"  [{mark}] {c['check']:<10} {c['detail']}"
            if c["next_step"]:
                line += f"  -> {c['next_step']}"
            click.echo(line)
        click.echo()
        if result["status"] == "ready":
            click.echo("Ready." + (f" Suggested: {result['next_step']}" if result["next_step"] else ""))
        else:
            click.echo(f"Action needed. Next: {result['next_step']}")

    if required_failed:
        raise SystemExit(1)
