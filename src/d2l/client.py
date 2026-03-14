import time

from d2l.config import LMS_HOST, LP_VERSION, LE_VERSION, BAS_VERSION
from d2l.errors import raise_for_status, RateLimitError


class D2LClient:
    """Read-only D2L Brightspace API client. All methods are GET only."""

    MAX_RETRIES = 3

    def __init__(self, session):
        self._s = session

    # --- Low-level ---

    def _get(self, url, params=None, raw=False):
        """GET with retry on 429."""
        for attempt in range(self.MAX_RETRIES):
            r = self._s.get(url, params=params)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 5))
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(retry_after)
                    continue
            break
        if raw:
            raise_for_status(r)
            return r
        raise_for_status(r)
        return r.json()

    def lms_get(self, path, params=None):
        """GET against LMS Valence API, returns parsed JSON."""
        return self._get(f"{LMS_HOST}{path}", params=params)

    def lms_get_raw(self, path, params=None):
        """GET returning raw response (for file downloads)."""
        return self._get(f"{LMS_HOST}{path}", params=params, raw=True)

    # --- Path builders ---

    def lp(self, path):
        return f"/d2l/api/lp/{LP_VERSION}{path}"

    def le(self, path):
        return f"/d2l/api/le/{LE_VERSION}{path}"

    def bas(self, path):
        return f"/d2l/api/bas/{BAS_VERSION}{path}"

    # --- Pagination ---

    def paginate_bookmark(self, path, params=None):
        """Walk bookmark-paginated endpoint, return flat list of Items."""
        items = []
        p = dict(params or {})
        p["bookmark"] = ""
        while True:
            data = self.lms_get(path, p)
            items.extend(data.get("Items", []))
            paging = data.get("PagingInfo", {})
            if not paging.get("HasMoreItems"):
                break
            p["bookmark"] = paging["Bookmark"]
        return items

    def paginate_pages(self, path, page_size=50, params=None):
        """Walk page-number pagination (discussions), return flat list."""
        items = []
        p = dict(params or {})
        p["pageSize"] = page_size
        page = 1
        while True:
            p["pageNumber"] = page
            data = self.lms_get(path, p)
            batch = data if isinstance(data, list) else []
            if not batch:
                break
            items.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
        return items

    # --- High-level data fetchers ---

    def whoami(self):
        return self.lms_get(self.lp("/users/whoami"))

    def my_enrollments(self, active_only=True):
        params = {"sortBy": "-StartDate"}
        if active_only:
            params["isActive"] = "true"
            params["canAccess"] = "true"
        return self.paginate_bookmark(self.lp("/enrollments/myenrollments/"), params)

    def grades(self, org_id):
        return self.lms_get(self.le(f"/{org_id}/grades/values/myGradeValues/"))

    def grade_objects(self, org_id):
        return self.lms_get(self.le(f"/{org_id}/grades/"))

    def final_grade(self, org_id):
        try:
            return self.lms_get(self.le(f"/{org_id}/grades/final/values/myGradeValue"))
        except Exception:
            return None

    def final_grades_bulk(self, org_ids_csv):
        return self.lms_get(
            self.le("/grades/final/values/myGradeValues/"),
            {"orgUnitIdsCSV": org_ids_csv},
        )

    def grade_statistics(self, org_id, grade_object_id):
        try:
            return self.lms_get(self.le(f"/{org_id}/grades/{grade_object_id}/statistics"))
        except Exception:
            return None

    def assignments(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/dropbox/folders/"))
        return data if isinstance(data, list) else []

    def my_submissions(self, org_id, folder_id):
        data = self.lms_get(self.le(f"/{org_id}/dropbox/folders/{folder_id}/submissions/mysubmissions/"))
        return data if isinstance(data, list) else []

    def content_root(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/content/root/"))
        return data if isinstance(data, list) else []

    def content_module(self, org_id, module_id):
        return self.lms_get(self.le(f"/{org_id}/content/modules/{module_id}/structure/"))

    def content_toc(self, org_id):
        return self.lms_get(self.le(f"/{org_id}/content/toc"))

    def content_topic_file(self, org_id, topic_id):
        return self.lms_get_raw(self.le(f"/{org_id}/content/topics/{topic_id}/file"))

    def assignment_attachment(self, org_id, folder_id, file_id):
        """Download an assignment folder attachment (returns raw response)."""
        return self.lms_get_raw(self.le(f"/{org_id}/dropbox/folders/{folder_id}/attachments/{file_id}"))

    def quizzes(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/quizzes/"))
        if isinstance(data, dict) and "Objects" in data:
            return data["Objects"]
        return data if isinstance(data, list) else []

    def quiz_attempts(self, org_id, quiz_id):
        data = self.lms_get(self.le(f"/{org_id}/quizzes/{quiz_id}/attempts/"))
        if isinstance(data, dict) and "Objects" in data:
            return data["Objects"]
        return data if isinstance(data, list) else []

    def discussion_forums(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/discussions/forums/"))
        return data if isinstance(data, list) else []

    def discussion_topics(self, org_id, forum_id):
        data = self.lms_get(self.le(f"/{org_id}/discussions/forums/{forum_id}/topics/"))
        return data if isinstance(data, list) else []

    def discussion_posts(self, org_id, forum_id, topic_id, page_size=50):
        return self.paginate_pages(
            self.le(f"/{org_id}/discussions/forums/{forum_id}/topics/{topic_id}/posts/"),
            page_size=page_size,
        )

    def news(self, org_id, since=None):
        params = {}
        if since:
            params["since"] = since
        data = self.lms_get(self.le(f"/{org_id}/news/"), params or None)
        return data if isinstance(data, list) else []

    def user_feed(self, since=None, until=None):
        params = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        data = self.lms_get(self.lp("/feed/"), params or None)
        return data if isinstance(data, list) else []

    def calendar_events(self, org_id=None, start=None, end=None, org_ids_csv=None):
        params = {}
        if start:
            params["startDateTime"] = start
        if end:
            params["endDateTime"] = end
        if org_id:
            return self.lms_get(self.le(f"/{org_id}/calendar/events/myEvents/"), params or None)
        if org_ids_csv:
            params["orgUnitIdsCSV"] = org_ids_csv
        data = self.lms_get(self.le("/calendar/events/myEvents/"), params or None)
        return data if isinstance(data, list) else []

    def due_items(self, org_ids_csv=None, start=None, end=None):
        params = {}
        if org_ids_csv:
            params["orgUnitIdsCSV"] = org_ids_csv
        if start:
            params["startDateTime"] = start
        if end:
            params["endDateTime"] = end
        data = self.lms_get(self.le("/content/myItems/due/"), params or None)
        if isinstance(data, dict) and "Objects" in data:
            return data["Objects"]
        return data if isinstance(data, list) else []

    def overdue_items(self, org_ids_csv=None):
        params = {}
        if org_ids_csv:
            params["orgUnitIdsCSV"] = org_ids_csv
        data = self.lms_get(self.le("/overdueItems/myItems"), params or None)
        if isinstance(data, dict) and "Objects" in data:
            return data["Objects"]
        return data if isinstance(data, list) else []

    def updates(self, org_id=None):
        if org_id:
            return self.lms_get(self.le(f"/{org_id}/updates/myUpdates"))
        return self.lms_get(self.le("/updates/myUpdates/"))

    def classlist(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/classlist/paged/"))
        if isinstance(data, dict) and "Objects" in data:
            return data["Objects"]
        return data if isinstance(data, list) else []

    def checklists(self, org_id):
        data = self.lms_get(self.le(f"/{org_id}/checklists/"))
        return data if isinstance(data, list) else []

    def course_overview(self, org_id):
        try:
            return self.lms_get(self.le(f"/{org_id}/overview"))
        except Exception:
            return None
