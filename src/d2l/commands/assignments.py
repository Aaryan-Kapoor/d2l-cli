import click

from d2l.errors import handle_errors
from d2l.formatting import table, format_date
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course")
@click.pass_context
@handle_errors
def assignments(ctx, course):
    """List assignments for a course. COURSE can be a name, code, or ID."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    name = resolver.resolve(course)["OrgUnit"]["Name"]
    data = client.assignments(org_id)
    table(data, columns=[
        ("ID", "Id"),
        ("Name", "Name"),
        ("Due", lambda a: format_date(a.get("DueDate"))),
        ("Points", lambda a: str(a.get("Assessment", {}).get("ScoreDenominator", "")) if a.get("Assessment") else ""),
    ], title=f"Assignments: {name}")
