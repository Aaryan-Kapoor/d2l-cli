import click

from d2l.auth import load_token, make_session
from d2l.client import D2LClient
from d2l.formatting import set_format, OutputFormat


def _make_client_factory():
    """Returns a callable that creates D2LClient on first call, caches it."""
    state = {}

    def factory():
        if "client" not in state:
            token = load_token()
            session = make_session(token)
            state["client"] = D2LClient(session)
        return state["client"]

    return factory


@click.group()
@click.option("--json", "fmt", flag_value="json", help="Output as JSON")
@click.option("--md", "fmt", flag_value="md", help="Output as Markdown (for AI)")
@click.version_option(package_name="d2l-cli")
@click.pass_context
def cli(ctx, fmt):
    """D2L Brightspace CLI — read-only student API client."""
    ctx.ensure_object(dict)
    if fmt:
        set_format(OutputFormat(fmt))
    ctx.obj["get_client"] = _make_client_factory()


# Register commands
from d2l.commands.auth_cmd import login, whoami, token
from d2l.commands.courses import courses
from d2l.commands.grades import grades
from d2l.commands.assignments import assignments
from d2l.commands.content import content
from d2l.commands.calendar_cmd import calendar, due, overdue
from d2l.commands.news import news
from d2l.commands.quizzes import quizzes
from d2l.commands.discussions import discussions
from d2l.commands.dump import dump
from d2l.commands.updates import updates
from d2l.commands.syllabus import syllabus
from d2l.commands.download import download, download_content

cli.add_command(login)
cli.add_command(token)
cli.add_command(whoami)
cli.add_command(courses)
cli.add_command(grades)
cli.add_command(assignments)
cli.add_command(content)
cli.add_command(calendar)
cli.add_command(due)
cli.add_command(overdue)
cli.add_command(news)
cli.add_command(quizzes)
cli.add_command(discussions)
cli.add_command(dump)
cli.add_command(updates)
cli.add_command(syllabus)
cli.add_command(download)
cli.add_command(download_content)
