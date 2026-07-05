import click
from datetime import datetime, timedelta, timezone

from d2l.errors import handle_errors
from d2l.formatting import table, format_date, output
from d2l.resolver import CourseResolver


def _iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _iso_future(days):
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


@click.command()
@click.option("--course", help="Filter to one course (name, code, or ID)")
@click.option("--days", default=7, help="Look ahead N days (default: 7)")
@click.pass_context
@handle_errors
def calendar(ctx, course, days):
    """Show upcoming calendar events."""
    client = ctx.obj["get_client"]()
    start = _iso_now()
    end = _iso_future(days)

    if course:
        resolver = CourseResolver(client)
        org_id = resolver.resolve_id(course)
        data = client.calendar_events(org_id=org_id, start=start, end=end)
    else:
        resolver = CourseResolver(client)
        courses = resolver.list_courses()
        ids_csv = ",".join(str(c["OrgUnit"]["Id"]) for c in courses)
        data = client.calendar_events(start=start, end=end, org_ids_csv=ids_csv)

    items = data if isinstance(data, list) else []
    table(items, columns=[
        ("Title", "Title"),
        ("Start", lambda e: format_date(e.get("StartDateTime"))),
        ("End", lambda e: format_date(e.get("EndDateTime"))),
    ], title=f"Calendar (next {days} days)")


@click.command()
@click.option("--days", default=7, help="Look ahead N days (default: 7)")
@click.pass_context
@handle_errors
def due(ctx, days):
    """Show items due soon (across all courses)."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    courses = resolver.list_courses()
    ids_csv = ",".join(str(c["OrgUnit"]["Id"]) for c in courses)
    start = _iso_now()
    end = _iso_future(days)
    data = client.due_items(org_ids_csv=ids_csv, start=start, end=end)
    table(data, columns=[
        ("Item", "ItemName"),
        ("Course", "OrgUnitName"),
        ("Due", lambda i: format_date(i.get("DueDate") or i.get("EndDate"))),
        ("Type", "ItemType"),
    ], title=f"Due Items (next {days} days)")


@click.command()
@click.pass_context
@handle_errors
def overdue(ctx):
    """Show overdue items."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    courses = resolver.list_courses()
    ids_csv = ",".join(str(c["OrgUnit"]["Id"]) for c in courses)
    data = client.overdue_items(org_ids_csv=ids_csv)
    table(data, columns=[
        ("Item", "ItemName"),
        ("Course", "OrgUnitName"),
        ("Due", lambda i: format_date(i.get("DueDate") or i.get("EndDate"))),
        ("Type", "ItemType"),
    ], title="Overdue Items")
