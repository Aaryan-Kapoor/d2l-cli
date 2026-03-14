import click

from d2l.errors import handle_errors
from d2l.formatting import table, format_date
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course")
@click.pass_context
@handle_errors
def quizzes(ctx, course):
    """List quizzes for a course. COURSE can be a name, code, or ID."""
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    name = resolver.resolve(course)["OrgUnit"]["Name"]
    data = client.quizzes(org_id)
    table(data, columns=[
        ("ID", "QuizId"),
        ("Name", "Name"),
        ("Due", lambda q: format_date(q.get("DueDate"))),
        ("Start", lambda q: format_date(q.get("StartDate"))),
        ("End", lambda q: format_date(q.get("EndDate"))),
        ("Attempts", lambda q: str(q.get("AttemptsAllowed", {}).get("NumberOfAttemptsAllowed", "")) if isinstance(q.get("AttemptsAllowed"), dict) else str(q.get("NumberOfAttemptsAllowed", ""))),
        ("Time Limit", lambda q: f"{q.get('TimeLimitValue', '')} min" if q.get("TimeLimitValue") else ""),
    ], title=f"Quizzes: {name}")
