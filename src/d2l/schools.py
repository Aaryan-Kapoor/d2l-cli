"""Known-school presets for `d2l setup`.

Each preset maps a school to its Brightspace host and, when known, its
SimpleSyllabus host. Any Brightspace school works via a raw URL; presets
just make setup a one-word answer for schools we've verified.
"""

SCHOOLS = {
    "kennesaw": {
        "name": "Kennesaw State University",
        "aliases": ["ksu", "kennesaw state"],
        "lms_host": "https://kennesaw.view.usg.edu",
        "syllabus_host": "https://kennesaw.simplesyllabus.com",
    },
    "gastate": {
        "name": "Georgia State University",
        "aliases": ["gsu", "georgia state"],
        "lms_host": "https://gastate.view.usg.edu",
        "syllabus_host": None,
    },
}


def find_school(query):
    """Match a school by key, alias, or name substring. Returns (key, preset) or None."""
    q = query.strip().lower()
    if not q:
        return None
    for key, preset in SCHOOLS.items():
        if q == key or q in (a.lower() for a in preset["aliases"]):
            return key, preset
    for key, preset in SCHOOLS.items():
        if q in preset["name"].lower():
            return key, preset
    return None
