import click

from d2l.errors import handle_errors
from d2l.formatting import output
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course", required=False)
@click.pass_context
@handle_errors
def updates(ctx, course):
    """Show unread update counts. Optionally filter to a course."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)

    if course:
        org_id = resolver.resolve_id(course)
        data = client.updates(org_id=org_id)
    else:
        courses = resolver.list_courses()
        ids_csv = ",".join(str(c["OrgUnit"]["Id"]) for c in courses)
        data = client.updates(org_ids_csv=ids_csv) if ids_csv else []

    output(data, title="Updates")
