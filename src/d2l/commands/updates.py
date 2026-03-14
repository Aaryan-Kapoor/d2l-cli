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

    if course:
        resolver = CourseResolver(client)
        org_id = resolver.resolve_id(course)
        data = client.updates(org_id)
    else:
        data = client.updates()

    output(data, title="Updates")
