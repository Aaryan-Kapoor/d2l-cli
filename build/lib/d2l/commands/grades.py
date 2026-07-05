import click

from d2l.errors import handle_errors
from d2l.formatting import table, format_grade
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course", required=False)
@click.option("--final", "show_final", is_flag=True, help="Show final grades across all courses")
@click.pass_context
@handle_errors
def grades(ctx, course, show_final):
    """Show grades. COURSE can be a name, code, or ID.

    Examples:
      d2l grades "data structures"
      d2l grades --final
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)

    if show_final:
        courses = resolver.list_courses()
        ids_csv = ",".join(str(c["OrgUnit"]["Id"]) for c in courses)
        data = client.final_grades_bulk(ids_csv)
        items = data if isinstance(data, list) else data.get("Objects", [])
        table(items, columns=[
            ("Course", "OrgUnitName"),
            ("Grade", lambda g: format_grade(g.get("PointsNumerator"), g.get("PointsDenominator"))),
            ("Display", "DisplayedGrade"),
        ], title="Final Grades")
        return

    if not course:
        raise click.UsageError("Provide a course name/ID, or use --final")

    org_id = resolver.resolve_id(course)
    name = resolver.resolve(course)["OrgUnit"]["Name"]
    data = client.grades(org_id)
    items = data if isinstance(data, list) else []
    table(items, columns=[
        ("Item", "GradeObjectName"),
        ("Score", lambda g: format_grade(g.get("PointsNumerator"), g.get("PointsDenominator"))),
        ("Display", "DisplayedGrade"),
    ], title=f"Grades: {name}")
