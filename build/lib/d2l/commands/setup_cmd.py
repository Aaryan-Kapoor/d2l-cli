import sys

import click

from d2l.config import (
    CONFIG_FILE,
    get_lms_host,
    get_syllabus_host,
    normalize_host,
    save_config,
)
from d2l.errors import handle_errors, D2LError
from d2l.formatting import get_format, OutputFormat, output
from d2l.schools import SCHOOLS, find_school


def _current_config():
    return {
        "config_file": str(CONFIG_FILE),
        "lms_host": get_lms_host(required=False),
        "syllabus_host": get_syllabus_host(),
    }


def _echo_config(cfg):
    if get_format() == OutputFormat.JSON:
        output(cfg)
        return
    click.echo(f"Config file:    {cfg['config_file']}")
    click.echo(f"Brightspace:    {cfg['lms_host'] or '(not set — run: d2l setup)'}")
    click.echo(f"SimpleSyllabus: {cfg['syllabus_host'] or '(not set — syllabus command disabled)'}")


def _echo_schools():
    rows = [
        {"key": key, "name": p["name"], "lms_host": p["lms_host"], "aliases": p["aliases"]}
        for key, p in SCHOOLS.items()
    ]
    if get_format() == OutputFormat.JSON:
        output(rows)
        return
    click.echo("Known schools (any Brightspace school works via --host):")
    for r in rows:
        click.echo(f"  {r['key']:<10} {r['name']} — {r['lms_host']}")


def _interactive_pick():
    click.echo("Which school do you attend?")
    keys = list(SCHOOLS)
    for i, key in enumerate(keys, 1):
        click.echo(f"  {i}. {SCHOOLS[key]['name']}")
    click.echo(f"  {len(keys) + 1}. Other (enter your school's Brightspace URL)")
    choice = click.prompt("Choice", type=click.IntRange(1, len(keys) + 1))
    if choice <= len(keys):
        return SCHOOLS[keys[choice - 1]], None
    host = click.prompt("Brightspace URL (e.g. https://your-school.view.usg.edu)")
    return None, host


@click.command()
@click.option("--school", help="Known school preset (see --list-schools), e.g. 'ksu' or 'georgia state'")
@click.option("--host", help="Brightspace URL, e.g. https://kennesaw.view.usg.edu")
@click.option("--syllabus-host", help="SimpleSyllabus URL, e.g. https://kennesaw.simplesyllabus.com")
@click.option("--list-schools", is_flag=True, help="List known school presets")
@click.option("--show", is_flag=True, help="Show current configuration")
@handle_errors
def setup(school, host, syllabus_host, list_schools, show):
    """Configure which school's Brightspace this CLI talks to.

    Interactive when run with no options; agents should pass --school or
    --host. Settings are stored in ~/.d2l/config.json (override per-run
    with the D2L_HOST / D2L_SYLLABUS_HOST environment variables).
    """
    if list_schools:
        _echo_schools()
        return
    if show:
        _echo_config(_current_config())
        return

    preset = None
    if school:
        matched = find_school(school)
        if not matched:
            known = ", ".join(SCHOOLS)
            raise D2LError(
                f"Unknown school '{school}'. Known presets: {known}. "
                "For any other school, pass --host with your Brightspace URL."
            )
        preset = matched[1]

    if not preset and not host:
        if not sys.stdin.isatty():
            raise D2LError(
                "No school given. Pass --school NAME or --host URL "
                "(run 'd2l setup --list-schools' for presets)."
            )
        preset, host = _interactive_pick()

    updates = {}
    if preset:
        updates["school"] = preset["name"]
        updates["lms_host"] = preset["lms_host"]
        updates["syllabus_host"] = preset["syllabus_host"]
    if host:
        lms_host = normalize_host(host)
        if not lms_host:
            raise D2LError(f"'{host}' does not look like a valid URL.")
        updates["lms_host"] = lms_host
        updates.setdefault("school", None)
    if syllabus_host:
        normalized = normalize_host(syllabus_host)
        if not normalized:
            raise D2LError(f"'{syllabus_host}' does not look like a valid URL.")
        updates["syllabus_host"] = normalized

    save_config(updates)
    cfg = _current_config()
    if get_format() == OutputFormat.JSON:
        output({"status": "configured", **cfg})
    else:
        _echo_config(cfg)
        click.echo("\nNext step: d2l login")
