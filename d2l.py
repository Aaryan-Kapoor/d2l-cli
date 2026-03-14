"""
D2L Brightspace API client using a browser-scraped Bearer token.

Usage:
  1. Open DevTools (F12) on kennesaw.view.usg.edu
  2. Go to Network tab, find any XHR request to *.api.brightspace.com
  3. Copy the Bearer token from the Authorization header
  4. Paste it into .env as D2L_TOKEN=<token> (without "Bearer " prefix)
     OR pass it as a command-line argument: python d2l.py <token>
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Run: pip install requests")
    sys.exit(1)

# --- Config ---
LMS_HOST = "https://kennesaw.view.usg.edu"
TENANT_ID = "857f39d7-a377-40a5-9272-5bb63ea6aafe"
BS_API = f"https://{TENANT_ID}.organizations.api.brightspace.com"
LP_VERSION = "1.47"   # learning platform
LE_VERSION = "1.80"   # learning environment


def get_token():
    # CLI arg > ~/.d2l/token.json > .env file > env var
    if len(sys.argv) > 1:
        return sys.argv[1]
    token_file = os.path.join(os.path.expanduser("~"), ".d2l", "token.json")
    if os.path.exists(token_file):
        import time
        data = json.load(open(token_file))
        exp = data.get("exp", 0)
        if exp > time.time():
            return data["token"]
        else:
            print(f"  Token expired at {time.ctime(exp)}. Run: python grab_token.py")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("D2L_TOKEN="):
                return line.strip().split("=", 1)[1]
    return os.environ.get("D2L_TOKEN")


def make_session(token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Origin": LMS_HOST,
        "Referer": f"{LMS_HOST}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    })
    return s


# ---- Brightspace cloud API calls ----

def get_org_info(s, org_id):
    """Get organization info (course name etc.)"""
    r = s.get(f"{BS_API}/{org_id}")
    return r


# ---- LMS-hosted Valence API calls ----

def lms_get(s, path):
    """GET against the LMS Valence API."""
    url = f"{LMS_HOST}{path}"
    return s.get(url)


def get_my_enrollments(s):
    """List all courses you're enrolled in."""
    items = []
    bookmark = ""
    while True:
        path = f"/d2l/api/lp/{LP_VERSION}/enrollments/myenrollments/?sortBy=-StartDate&bookmark={bookmark}"
        r = lms_get(s, path)
        if r.status_code != 200:
            print(f"  enrollments failed ({r.status_code}): {r.text[:300]}")
            break
        data = r.json()
        items.extend(data.get("Items", []))
        if not data.get("PagingInfo", {}).get("HasMoreItems"):
            break
        bookmark = data["PagingInfo"]["Bookmark"]
    return items


def get_course_content(s, org_id):
    """Get the content tree (modules) for a course."""
    r = lms_get(s, f"/d2l/api/le/{LE_VERSION}/{org_id}/content/root/")
    return r


def get_my_grades(s, org_id):
    """Get your grades for a course."""
    r = lms_get(s, f"/d2l/api/le/{LE_VERSION}/{org_id}/grades/values/myGradeValues/")
    return r


def get_upcoming_events(s, org_id):
    """Get calendar events for a course."""
    r = lms_get(s, f"/d2l/api/le/{LE_VERSION}/{org_id}/calendar/events/myEvents/")
    return r


def get_assignments(s, org_id):
    """Get dropbox folders (assignments) for a course."""
    r = lms_get(s, f"/d2l/api/le/{LE_VERSION}/{org_id}/dropbox/folders/")
    return r


def whoami(s):
    """Get current user info."""
    r = lms_get(s, f"/d2l/api/lp/{LP_VERSION}/users/whoami")
    return r


# ---- Main ----

def main():
    token = get_token()
    if not token:
        print("No token found. Pass as arg or put D2L_TOKEN=... in .env")
        sys.exit(1)

    s = make_session(token)

    # 1. Test: who am I?
    print("=== WHO AM I ===")
    r = whoami(s)
    if r.status_code == 200:
        me = r.json()
        print(f"  {me.get('FirstName')} {me.get('LastName')} (ID: {me.get('Identifier')})")
        print(f"  UniqueName: {me.get('UniqueName')}")
    else:
        print(f"  whoami failed ({r.status_code}). Token may be expired or Valence API needs cookie auth.")
        print(f"  Response: {r.text[:300]}")
        print()
        # Try the cloud API as a fallback test
        print("=== TRYING CLOUD API (organizations) ===")
        r2 = get_org_info(s, "3824526")
        print(f"  Status: {r2.status_code}")
        if r2.status_code == 200:
            print(f"  Response: {json.dumps(r2.json(), indent=2)[:500]}")
        else:
            print(f"  Response: {r2.text[:300]}")
        print("\nThe Bearer token works for cloud API but not LMS Valence API.")
        print("You may need to also grab cookies from the browser for LMS endpoints.")
        return

    # 2. Enrollments
    print("\n=== MY COURSES ===")
    enrollments = get_my_enrollments(s)
    active_courses = []
    for e in enrollments:
        info = e.get("OrgUnit", {})
        name = info.get("Name", "?")
        oid = info.get("Id")
        otype = info.get("Type", {}).get("Name", "")
        if otype in ("Course Offering", ""):
            active_courses.append((oid, name))
            print(f"  [{oid}] {name}")
    if not active_courses:
        print("  No courses found (or API version mismatch).")
        if enrollments:
            print(f"  Raw first item: {json.dumps(enrollments[0], indent=2)[:400]}")

    # 3. For first few courses, show grades & assignments
    for oid, name in active_courses[:3]:
        print(f"\n--- {name} [{oid}] ---")

        print("  Grades:")
        r = get_my_grades(s, oid)
        if r.status_code == 200:
            grades = r.json()
            for g in grades if isinstance(grades, list) else []:
                gname = g.get("GradeObjectName", "?")
                pts = g.get("PointsNumerator")
                den = g.get("PointsDenominator")
                print(f"    {gname}: {pts}/{den}")
            if not grades:
                print("    (none)")
        else:
            print(f"    failed ({r.status_code})")

        print("  Assignments:")
        r = get_assignments(s, oid)
        if r.status_code == 200:
            folders = r.json()
            for f in folders if isinstance(folders, list) else []:
                fname = f.get("Name", "?")
                due = f.get("DueDate", "")
                print(f"    {fname} (due: {due or 'n/a'})")
            if not folders:
                print("    (none)")
        else:
            print(f"    failed ({r.status_code})")

    print("\n=== DONE ===")
    print(f"Found {len(enrollments)} enrollments, {len(active_courses)} courses shown.")


if __name__ == "__main__":
    main()
