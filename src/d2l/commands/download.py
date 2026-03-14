import re
from pathlib import Path

import click

from d2l.errors import handle_errors, D2LError, NotFoundError, ForbiddenError
from d2l.resolver import CourseResolver


# --- Content module helpers ---

def _find_modules_recursive(structure, query_lower, results=None):
    """Recursively search a content structure for modules matching query."""
    if results is None:
        results = []
    items = structure if isinstance(structure, list) else []
    for item in items:
        item_type = item.get("Type", -1)
        title = item.get("Title", item.get("Name", "")).lower()
        mid = item.get("Id") or item.get("ModuleId")
        if item_type == 0 and mid:  # Module
            if query_lower in title:
                results.append(item)
            # Recurse into child modules
            children = item.get("Modules", [])
            _find_modules_recursive(children, query_lower, results)
    return results


def _collect_topic_files(client, org_id, module_id):
    """Recursively collect all file topics (TopicType==1) under a module."""
    topics = []
    try:
        children = client.content_module(org_id, module_id)
    except (NotFoundError, ForbiddenError):
        return topics
    if not isinstance(children, list):
        return topics
    for item in children:
        item_type = item.get("Type", -1)
        if item_type == 1 and item.get("TopicType") == 1:  # File topic
            topics.append(item)
        elif item_type == 0:  # Sub-module, recurse
            sub_id = item.get("Id") or item.get("ModuleId")
            if sub_id:
                topics.extend(_collect_topic_files(client, org_id, sub_id))
    return topics


def _filename_from_response(response, fallback):
    """Extract filename from Content-Disposition header, or use fallback."""
    cd = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename[*]?=["\']?(?:UTF-8\'\')?([^"\';]+)', cd)
    if match:
        return match.group(1).strip()
    return fallback


# --- Assignment helpers ---

def _match_assignment(assignments, query):
    """Match an assignment by ID, exact name, or substring."""
    query_str = str(query).strip()

    # Exact ID
    if query_str.isdigit():
        for a in assignments:
            if str(a.get("Id")) == query_str:
                return a

    # Exact name
    query_lower = query_str.lower()
    for a in assignments:
        if a.get("Name", "").lower() == query_lower:
            return a

    # Substring
    matches = [a for a in assignments if query_lower in a.get("Name", "").lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        lines = [f"Multiple assignments match '{query_str}':"]
        for m in matches:
            lines.append(f"  [{m['Id']}] {m['Name']}")
        lines.append("Be more specific or use the numeric ID.")
        raise D2LError("\n".join(lines))

    raise D2LError(f"No assignment matching '{query_str}'. Run 'd2l assignments COURSE' to see available.")


@click.command()
@click.argument("course")
@click.argument("assignment")
@click.option("-o", "--out", "out_dir", default=".", help="Output directory (default: current dir)")
@click.pass_context
@handle_errors
def download(ctx, course, assignment, out_dir):
    """Download assignment attachments. COURSE and ASSIGNMENT accept fuzzy names.

    Downloads all files attached to an assignment (instructions, starter code, etc.)
    into the specified output directory.

    Examples:
      d2l download "data structures" "trees"
      d2l download "data structures" "A06" -o ./assignment6
      d2l download "calc" "review" -o ./calc-review
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    course_name = resolver.resolve(course)["OrgUnit"]["Name"]

    # Find the assignment
    all_assignments = client.assignments(org_id)
    matched = _match_assignment(all_assignments, assignment)
    folder_id = matched["Id"]
    folder_name = matched["Name"]
    attachments = matched.get("Attachments", [])

    if not attachments:
        click.echo(f"No attachments on '{folder_name}'.")
        return

    # Create output directory
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Downloading {len(attachments)} file(s) from '{folder_name}'...")
    for att in attachments:
        file_id = att["FileId"]
        file_name = att["FileName"]
        dest = out_path / file_name

        r = client.assignment_attachment(org_id, folder_id, file_id)
        dest.write_bytes(r.content)
        size_kb = len(r.content) / 1024
        click.echo(f"  {file_name} ({size_kb:.1f} KB) -> {dest}")

    click.echo(f"Done. {len(attachments)} file(s) saved to {out_path.resolve()}")


@click.command("download-content")
@click.argument("course")
@click.argument("module")
@click.option("-o", "--out", "out_dir", default=".", help="Output directory (default: current dir)")
@click.pass_context
@handle_errors
def download_content(ctx, course, module, out_dir):
    """Download files from a content module. COURSE and MODULE accept fuzzy names.

    Recursively finds all file topics in the matched module and downloads them.

    Examples:
      d2l download-content "calc" "Exam Preparation" -o ./exam-prep
      d2l download-content "calc" "Class Notes" -o ./notes
      d2l download-content "data structures" "Big-O" -o ./bigo
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    course_name = resolver.resolve(course)["OrgUnit"]["Name"]

    # Get content root and search for matching module
    root = client.content_root(org_id)
    query_lower = module.strip().lower()

    # First search top-level modules
    matches = _find_modules_recursive(root, query_lower)

    # If no match in root, fetch each root module's structure and search deeper
    if not matches:
        for item in root:
            if item.get("Type", -1) == 0:
                mid = item.get("Id") or item.get("ModuleId")
                if mid:
                    try:
                        children = client.content_module(org_id, mid)
                        if isinstance(children, list):
                            _find_modules_recursive(children, query_lower, matches)
                    except (NotFoundError, ForbiddenError):
                        continue

    if not matches:
        raise D2LError(
            f"No content module matching '{module}' in {course_name}.\n"
            f"Run 'd2l content \"{course}\" --toc' to see available modules."
        )

    if len(matches) > 1:
        # Check for exact match
        exact = [m for m in matches if m.get("Title", m.get("Name", "")).lower() == query_lower]
        if len(exact) == 1:
            matches = exact
        else:
            lines = [f"Multiple modules match '{module}':"]
            for m in matches:
                mid = m.get("Id") or m.get("ModuleId")
                lines.append(f"  [{mid}] {m.get('Title', m.get('Name', '?'))}")
            lines.append("Be more specific or use 'd2l content COURSE --toc' to find the right module.")
            raise D2LError("\n".join(lines))

    matched_module = matches[0]
    mod_id = matched_module.get("Id") or matched_module.get("ModuleId")
    mod_name = matched_module.get("Title", matched_module.get("Name", "?"))

    # Collect all file topics recursively
    topics = _collect_topic_files(client, org_id, mod_id)

    if not topics:
        click.echo(f"No downloadable files in '{mod_name}'.")
        return

    # Download
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Downloading {len(topics)} file(s) from '{mod_name}'...")
    downloaded = 0
    for topic in topics:
        topic_id = topic.get("Id") or topic.get("TopicId")
        title = topic.get("Title", topic.get("Name", f"file_{topic_id}"))
        try:
            r = client.content_topic_file(org_id, topic_id)
        except (NotFoundError, ForbiddenError):
            click.echo(f"  [skip] {title} (not accessible)")
            continue

        file_name = _filename_from_response(r, title)
        dest = out_path / file_name
        dest.write_bytes(r.content)
        size_kb = len(r.content) / 1024
        click.echo(f"  {file_name} ({size_kb:.1f} KB) -> {dest}")
        downloaded += 1

    click.echo(f"Done. {downloaded} file(s) saved to {out_path.resolve()}")
