import click

from d2l.errors import handle_errors
from d2l.formatting import table
from d2l.resolver import CourseResolver


@click.command()
@click.option("--all", "show_all", is_flag=True, help="Include inactive/past courses")
@click.pass_context
@handle_errors
def courses(ctx, show_all):
    """List enrolled courses."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    data = resolver.all_enrollments() if show_all else resolver.list_courses()
    table(data, columns=[
        ("ID", "OrgUnit.Id"),
        ("Name", "OrgUnit.Name"),
        ("Code", "OrgUnit.Code"),
        ("Active", "Access.IsActive"),
    ], title="My Courses")
