import click

from d2l.errors import handle_errors
from d2l.formatting import table, format_date, rich_text, output
from d2l.resolver import CourseResolver


@click.command()
@click.argument("course")
@click.option("--forum", type=int, help="Show topics in a specific forum ID")
@click.option("--posts", nargs=2, type=int, help="Show posts: FORUM_ID TOPIC_ID")
@click.pass_context
@handle_errors
def discussions(ctx, course, forum, posts):
    """Browse discussion forums. COURSE can be a name, code, or ID.

    Examples:
      d2l discussions "data structures"
      d2l discussions "data structures" --forum 12345
      d2l discussions "data structures" --posts 12345 67890
    """
    client = ctx.obj["get_client"]()
    resolver = CourseResolver(client)
    org_id = resolver.resolve_id(course)
    name = resolver.resolve(course)["OrgUnit"]["Name"]

    if posts:
        forum_id, topic_id = posts
        data = client.discussion_posts(org_id, forum_id, topic_id)
        table(data, columns=[
            ("ID", "PostId"),
            ("Author", lambda p: p.get("PostingUserId", "")),
            ("Date", lambda p: format_date(p.get("DatePosted"))),
            ("Subject", lambda p: p.get("Subject", "")),
            ("Body", lambda p: rich_text(p.get("Message"))[:120] if p.get("Message") else ""),
        ], title=f"Posts: {name}")
    elif forum:
        data = client.discussion_topics(org_id, forum)
        table(data, columns=[
            ("ID", "TopicId"),
            ("Name", "Name"),
            ("Posts", lambda t: str(t.get("Stats", {}).get("NumPosts", "")) if t.get("Stats") else ""),
            ("Unread", lambda t: str(t.get("Stats", {}).get("NumUnread", "")) if t.get("Stats") else ""),
        ], title=f"Topics: {name}")
    else:
        data = client.discussion_forums(org_id)
        table(data, columns=[
            ("ID", "ForumId"),
            ("Name", "Name"),
            ("Description", lambda f: rich_text(f.get("Description"))[:80] if f.get("Description") else ""),
        ], title=f"Forums: {name}")
