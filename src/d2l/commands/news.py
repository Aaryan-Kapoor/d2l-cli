import click

from d2l.errors import handle_errors
from d2l.formatting import table, format_date, rich_text
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course", required=False)
@click.option("--since", help="Only show news since date (YYYY-MM-DD)")
@click.pass_context
@handle_errors
def news(ctx, course, since):
    """Show announcements. Optionally filter to a course."""
    client = ctx.obj["get_client"]()

    if course:
        resolver = CourseResolver(client)
        org_id = resolver.resolve_id(course)
        name = resolver.resolve(course)["OrgUnit"]["Name"]
        since_iso = f"{since}T00:00:00.000Z" if since else None
        data = client.news(org_id, since=since_iso)
        title = f"News: {name}"
    else:
        me = client.whoami()
        user_id = me["Identifier"]
        data = client.user_feed(since=f"{since}T00:00:00.000Z" if since else None)
        title = "Activity Feed"

    table(data, columns=[
        ("Date", lambda n: format_date(n.get("StartDate") or n.get("CreatedDate") or n.get("PublicationDate"))),
        ("Title", lambda n: n.get("Title", n.get("title", ""))),
        ("Body", lambda n: rich_text(n.get("Body"))[:100] if n.get("Body") else ""),
    ], title=title)
