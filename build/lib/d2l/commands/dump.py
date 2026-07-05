import json
from datetime import datetime, timedelta, timezone

import click

from d2l.errors import handle_errors, NotFoundError, ForbiddenError
from d2l.formatting import (
    get_format, OutputFormat, format_date, format_grade, rich_text,
)
from d2l.resolver import CourseResolver


ALL_SECTIONS = {"grades", "assignments", "content", "news", "quizzes", "discussions", "calendar"}


def _safe(fn, default=None):
    """Call fn, return default on 403/404."""
    try:
        return fn()
    except (NotFoundError, ForbiddenError):
        return default


def _parse_iso(s):
    """Parse an ISO 8601 string to a datetime. Returns None on failure."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _since_filter(items, since_dt, *date_keys):
    """Filter a list of dicts, keeping items where ANY of the date_keys is >= since_dt."""
    if not since_dt:
        return items
    out = []
    for item in items:
        for key in date_keys:
            val = item.get(key)
            dt = _parse_iso(val)
            if dt and dt >= since_dt:
                out.append(item)
                break
    return out


@click.command()
@click.option("--course", "course_filters", multiple=True, help="Limit to specific courses (repeatable)")
@click.option("--shallow", is_flag=True, help="Enrollments + due/overdue only")
@click.option("--since", "since_hours", type=float, help="Only show items from the last N hours (e.g. 24)")
@click.option("--include", "includes", multiple=True,
              type=click.Choice(sorted(ALL_SECTIONS)),
              help="Include only these sections per course")
@click.pass_context
@handle_errors
def dump(ctx, course_filters, shallow, since_hours, includes):
    """Dump comprehensive academic snapshot for AI consumption.

    With --since, filters ALL sections to only show items with dates in that
    window — new announcements, recently-due assignments, upcoming quizzes, etc.

    Best with --md for AI assistants, --json for programmatic use.

    Examples:
      d2l dump --md
      d2l dump --since 24 --md          # What's new in the last 24 hours
      d2l dump --md --course "data structures"
      d2l dump --shallow --md
      d2l dump --json
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    fmt = get_format()
    sections = set(includes) if includes else ALL_SECTIONS

    since_dt = None
    since_iso = None
    if since_hours:
        since_dt = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Header
    me = client.whoami()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Resolve courses
    if course_filters:
        courses = [resolver.resolve(q) for q in course_filters]
    else:
        courses = resolver.list_courses()

    org_ids = [c["OrgUnit"]["Id"] for c in courses]
    ids_csv = ",".join(str(i) for i in org_ids)

    # Cross-course data
    overdue = _safe(lambda: client.overdue_items(org_ids_csv=ids_csv), [])
    iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    iso_week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    due_soon = _safe(lambda: client.due_items(org_ids_csv=ids_csv, start=iso_now, end=iso_week), [])

    if fmt == OutputFormat.JSON:
        _dump_json(me, now, courses, overdue, due_soon, client, sections, shallow, since_dt, since_iso, since_hours)
    else:
        _dump_text(me, now, courses, overdue, due_soon, client, sections, shallow, fmt, since_dt, since_iso, since_hours)


def _dump_json(me, now, courses, overdue, due_soon, client, sections, shallow, since_dt, since_iso, since_hours):
    result = {
        "generated_at": now,
        "student": me,
        "overdue_items": overdue,
        "due_soon": due_soon,
        "courses": [],
    }
    if since_hours:
        result["since_hours"] = since_hours
        result["since_cutoff"] = since_iso
    if not shallow:
        for enrollment in courses:
            ou = enrollment["OrgUnit"]
            oid = ou["Id"]
            course_data = {"org_unit": ou, "access": enrollment.get("Access")}
            if "grades" in sections:
                all_grades = _safe(lambda: client.grades(oid), [])
                items = all_grades if isinstance(all_grades, list) else []
                course_data["grades"] = _since_filter(items, since_dt, "LastModified", "LastModifiedDate")
            if "assignments" in sections:
                all_assigns = _safe(lambda: client.assignments(oid), [])
                course_data["assignments"] = _since_filter(all_assigns, since_dt, "DueDate", "StartDate", "LastModifiedDate")
            if "content" in sections and not since_dt:
                course_data["content_toc"] = _safe(lambda: client.content_toc(oid))
            if "news" in sections:
                course_data["news"] = _safe(lambda: client.news(oid, since=since_iso), [])
            if "quizzes" in sections:
                all_quizzes = _safe(lambda: client.quizzes(oid), [])
                course_data["quizzes"] = _since_filter(all_quizzes, since_dt, "DueDate", "StartDate", "EndDate")
            if "discussions" in sections and not since_dt:
                course_data["discussion_forums"] = _safe(lambda: client.discussion_forums(oid), [])
            if "calendar" in sections:
                start = since_iso or now
                end = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                course_data["calendar_events"] = _safe(
                    lambda: client.calendar_events(org_id=oid, start=start, end=end),
                    [],
                )
            result["courses"].append(course_data)
    print(json.dumps(result, indent=2, default=str))


def _dump_text(me, now, courses, overdue, due_soon, client, sections, shallow, fmt, since_dt, since_iso, since_hours):
    md = fmt == OutputFormat.MARKDOWN
    h1 = "#" if md else "==="
    h2 = "##" if md else "---"
    h3 = "###" if md else ""

    title = "D2L Academic Snapshot"
    if since_hours:
        title += f" (last {since_hours:g}h)"
    print(f"{h1} {title}")
    print(f"Generated: {now}")
    print(f"Student: {me.get('FirstName')} {me.get('LastName')} ({me.get('UniqueName')}), ID: {me.get('Identifier')}")
    if since_iso:
        print(f"Since: {since_iso}")
    print()

    # Overdue
    if overdue:
        print(f"{h2} Overdue Items\n")
        if md:
            print("| Course | Item | Due |")
            print("| --- | --- | --- |")
        for item in overdue:
            name = item.get("ItemName", item.get("Name", "?"))
            course_name = item.get("OrgUnitName", "")
            due = format_date(item.get("DueDate") or item.get("EndDate"))
            if md:
                print(f"| {course_name} | {name} | {due} |")
            else:
                print(f"  [{course_name}] {name} — due {due}")
        print()
    else:
        print(f"{h2} Overdue Items\n\nNone!\n")

    # Due soon
    if due_soon:
        print(f"{h2} Due This Week\n")
        if md:
            print("| Course | Item | Due |")
            print("| --- | --- | --- |")
        for item in due_soon:
            name = item.get("ItemName", item.get("Name", "?"))
            course_name = item.get("OrgUnitName", "")
            due = format_date(item.get("DueDate") or item.get("EndDate"))
            if md:
                print(f"| {course_name} | {name} | {due} |")
            else:
                print(f"  [{course_name}] {name} — due {due}")
        print()
    else:
        print(f"{h2} Due This Week\n\nNone!\n")

    if shallow:
        return

    # Per-course
    for enrollment in courses:
        ou = enrollment["OrgUnit"]
        oid = ou["Id"]
        access = enrollment.get("Access", {})
        course_had_content = False

        # Collect per-course data, applying since filter
        course_sections = []

        if "grades" in sections:
            all_grades = _safe(lambda: client.grades(oid), [])
            items = all_grades if isinstance(all_grades, list) else []
            items = _since_filter(items, since_dt, "LastModified", "LastModifiedDate")
            if items:
                course_sections.append(("grades", items))

        if "assignments" in sections:
            all_assigns = _safe(lambda: client.assignments(oid), [])
            items = _since_filter(all_assigns, since_dt, "DueDate", "StartDate", "LastModifiedDate")
            if items:
                course_sections.append(("assignments", items))

        if "news" in sections:
            news_data = _safe(lambda: client.news(oid, since=since_iso), [])
            if news_data:
                course_sections.append(("news", news_data))

        if "quizzes" in sections:
            all_quizzes = _safe(lambda: client.quizzes(oid), [])
            items = _since_filter(all_quizzes, since_dt, "DueDate", "StartDate", "EndDate")
            if items:
                course_sections.append(("quizzes", items))

        if "discussions" in sections and not since_dt:
            forum_data = _safe(lambda: client.discussion_forums(oid), [])
            if forum_data:
                course_sections.append(("discussions", forum_data))

        if "content" in sections and not since_dt:
            toc = _safe(lambda: client.content_toc(oid))
            if toc:
                course_sections.append(("content", toc))

        if "calendar" in sections:
            start = since_iso or now
            end = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            cal_data = _safe(lambda: client.calendar_events(org_id=oid, start=start, end=end), [])
            if cal_data:
                course_sections.append(("calendar", cal_data))

        # Skip course entirely if --since and nothing matched
        if since_dt and not course_sections:
            continue

        print(f"{h2} Course: {ou.get('Name')}")
        print(f"ID: {oid} | Code: {ou.get('Code', 'n/a')} | Active: {access.get('IsActive')} | Ends: {format_date(access.get('EndDate'))}")
        print()

        for section_name, data in course_sections:
            if section_name == "grades":
                print(f"{h3} Grades\n" if md else "  Grades:")
                if md:
                    print("| Item | Score | Display |")
                    print("| --- | --- | --- |")
                for g in data:
                    score = format_grade(g.get("PointsNumerator"), g.get("PointsDenominator"))
                    display = g.get("DisplayedGrade", "")
                    if md:
                        print(f"| {g.get('GradeObjectName', '?')} | {score} | {display} |")
                    else:
                        print(f"    {g.get('GradeObjectName', '?')}: {score}")
                print()

            elif section_name == "assignments":
                print(f"{h3} Assignments\n" if md else "  Assignments:")
                if md:
                    print("| Name | Due | Points |")
                    print("| --- | --- | --- |")
                for a in data:
                    due = format_date(a.get("DueDate"))
                    pts = a.get("Assessment", {}).get("ScoreDenominator", "") if a.get("Assessment") else ""
                    if md:
                        print(f"| {a.get('Name', '?')} | {due} | {pts} |")
                    else:
                        print(f"    {a.get('Name', '?')} (due: {due}, pts: {pts})")
                print()

            elif section_name == "news":
                print(f"{h3} Announcements\n" if md else "  Announcements:")
                for n in data[:10]:
                    date = format_date(n.get("StartDate") or n.get("CreatedDate"))
                    title = n.get("Title", "?")
                    if md:
                        body = rich_text(n.get("Body"))[:200]
                        print(f"- **{title}** ({date}): {body}")
                    else:
                        print(f"    [{date}] {title}")
                print()

            elif section_name == "quizzes":
                print(f"{h3} Quizzes\n" if md else "  Quizzes:")
                if md:
                    print("| Name | Due | Time Limit |")
                    print("| --- | --- | --- |")
                for q in data:
                    due = format_date(q.get("DueDate"))
                    tl = f"{q.get('TimeLimitValue', '')} min" if q.get("TimeLimitValue") else ""
                    if md:
                        print(f"| {q.get('Name', '?')} | {due} | {tl} |")
                    else:
                        print(f"    {q.get('Name', '?')} (due: {due}, time: {tl})")
                print()

            elif section_name == "discussions":
                print(f"{h3} Discussion Forums\n" if md else "  Discussion Forums:")
                for f in data:
                    if md:
                        print(f"- {f.get('Name', '?')} (ID: {f.get('ForumId')})")
                    else:
                        print(f"    {f.get('Name', '?')} [ID: {f.get('ForumId')}]")
                print()

            elif section_name == "calendar":
                print(f"{h3} Calendar Events\n" if md else "  Calendar Events:")
                if md:
                    print("| Title | Start | End |")
                    print("| --- | --- | --- |")
                for e in data:
                    if not isinstance(e, dict):
                        continue
                    if md:
                        print(f"| {e.get('Title', '?')} | {format_date(e.get('StartDateTime'))} | {format_date(e.get('EndDateTime'))} |")
                    else:
                        print(f"    {e.get('Title', '?')} ({format_date(e.get('StartDateTime'))})")
                print()

        print()
