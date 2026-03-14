import json
from datetime import datetime, timezone
from enum import Enum


class OutputFormat(Enum):
    HUMAN = "human"
    JSON = "json"
    MARKDOWN = "md"


_format = OutputFormat.HUMAN


def set_format(fmt):
    global _format
    _format = fmt


def get_format():
    return _format


def _resolve_path(obj, path):
    """Resolve a dot-separated path or callable on a dict."""
    if callable(path):
        return path(obj)
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
        if obj is None:
            return None
    return obj


def output(data, human_fn=None, title=None):
    """Universal output — adapts to current format."""
    if _format == OutputFormat.JSON:
        print(json.dumps(data, indent=2, default=str))
    elif _format == OutputFormat.MARKDOWN:
        if title:
            print(f"## {title}\n")
        print(json.dumps(data, indent=2, default=str))
    else:
        if title:
            print(f"=== {title} ===")
        if human_fn:
            print(human_fn(data))
        else:
            print(json.dumps(data, indent=2, default=str))


def table(rows, columns, title=None):
    """Render a list of dicts as a formatted table.

    columns: list of (header, key_or_callable) tuples.
    """
    if not rows:
        if _format == OutputFormat.JSON:
            print("[]")
        elif _format == OutputFormat.MARKDOWN:
            if title:
                print(f"## {title}\n")
            print("(none)\n")
        else:
            if title:
                print(f"=== {title} ===")
            print("  (none)")
        return

    if _format == OutputFormat.JSON:
        print(json.dumps(rows, indent=2, default=str))
        return

    # Build string grid
    headers = [c[0] for c in columns]
    grid = []
    for row in rows:
        grid.append([str(_resolve_path(row, c[1]) or "") for c in columns])

    if _format == OutputFormat.MARKDOWN:
        if title:
            print(f"## {title}\n")
        # Markdown table
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for row_vals in grid:
            print("| " + " | ".join(row_vals) + " |")
        print()
    else:
        # Human: aligned columns
        if title:
            print(f"=== {title} ===")
        widths = [len(h) for h in headers]
        for row_vals in grid:
            for i, val in enumerate(row_vals):
                widths[i] = max(widths[i], len(val))
        fmt_str = "  ".join(f"{{:<{w}}}" for w in widths)
        print("  " + fmt_str.format(*headers))
        print("  " + fmt_str.format(*("-" * w for w in widths)))
        for row_vals in grid:
            print("  " + fmt_str.format(*row_vals))


def section(title, body=""):
    """Output a titled section."""
    if _format == OutputFormat.MARKDOWN:
        print(f"## {title}\n")
        if body:
            print(body)
            print()
    elif _format == OutputFormat.JSON:
        pass  # JSON mode handles structure differently
    else:
        print(f"\n=== {title} ===")
        if body:
            print(f"  {body}")


def format_date(iso_str):
    """Parse ISO 8601 UTC datetime to readable string."""
    if not iso_str:
        return "n/a"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if _format == OutputFormat.MARKDOWN:
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        return dt.astimezone().strftime("%b %d, %Y %I:%M %p")
    except (ValueError, AttributeError):
        return str(iso_str)


def format_grade(numerator, denominator):
    """Format grade as '85/100 (85.0%)'."""
    if numerator is None or denominator is None:
        return "n/a"
    if denominator == 0:
        return f"{numerator}/0"
    pct = (numerator / denominator) * 100
    return f"{numerator}/{denominator} ({pct:.1f}%)"


def rich_text(obj):
    """Extract text from D2L RichText { Text, Html } objects."""
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    return obj.get("Text") or obj.get("Html", "")
