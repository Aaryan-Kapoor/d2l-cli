import click

from d2l.errors import handle_errors
from d2l.formatting import output, get_format, OutputFormat
from d2l.resolver import CourseResolver


def _print_tree(items, indent=0):
    """Recursively print content tree in human mode."""
    prefix = "  " * indent
    for item in items:
        typ = item.get("Type", -1)
        title = item.get("Title", "?")
        if typ == 0:  # Module
            click.echo(f"{prefix}- [M] {title}")
            children = item.get("Modules", []) + item.get("Topics", [])
            if children:
                _print_tree(children, indent + 1)
        else:  # Topic
            topic_type = "file" if item.get("TopicType") == 1 else "link"
            click.echo(f"{prefix}- [{topic_type}] {title}")


def _print_toc(toc, indent=0):
    """Print table of contents tree."""
    if isinstance(toc, dict):
        modules = toc.get("Modules", [])
        topics = toc.get("Topics", [])
    elif isinstance(toc, list):
        modules = toc
        topics = []
    else:
        return

    prefix = "  " * indent
    for m in modules:
        title = m.get("Title", m.get("Name", "?"))
        click.echo(f"{prefix}- {title}")
        _print_toc(m, indent + 1)
    for t in topics:
        title = t.get("Title", t.get("Name", "?"))
        topic_type = "file" if t.get("TopicType") == 1 else "link"
        click.echo(f"{prefix}  - [{topic_type}] {title}")


@click.command()
@click.argument("course")
@click.option("--toc", is_flag=True, help="Show full table of contents")
@click.pass_context
@handle_errors
def content(ctx, course, toc):
    """Browse course content. COURSE can be a name, code, or ID."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    name = resolver.resolve(course)["OrgUnit"]["Name"]

    if toc:
        data = client.content_toc(org_id)
        if get_format() == OutputFormat.JSON:
            output(data)
        else:
            if get_format() == OutputFormat.MARKDOWN:
                click.echo(f"## Content: {name}\n")
            else:
                click.echo(f"=== Content: {name} ===")
            _print_toc(data)
            click.echo()
    else:
        data = client.content_root(org_id)
        if get_format() == OutputFormat.JSON:
            output(data)
        else:
            if get_format() == OutputFormat.MARKDOWN:
                click.echo(f"## Content: {name}\n")
            else:
                click.echo(f"=== Content: {name} ===")
            _print_tree(data)
