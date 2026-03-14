from d2l.errors import D2LError


class CourseResolver:
    """Resolves course names/codes/IDs to org unit enrollment records."""

    def __init__(self, client):
        self._client = client
        self._enrollments = None

    def _load(self):
        if self._enrollments is None:
            self._enrollments = self._client.my_enrollments(active_only=True)
        return self._enrollments

    def list_courses(self):
        """Return active course enrollments (Course Offering type)."""
        return [
            e for e in self._load()
            if e.get("OrgUnit", {}).get("Type", {}).get("Name", "") == "Course Offering"
        ]

    def all_enrollments(self):
        """Return all active enrollments (any type)."""
        return self._load()

    def resolve(self, query):
        """Resolve a query to a single enrollment dict.

        Priority: exact ID > exact code > substring name > word overlap.
        Raises D2LError on 0 or ambiguous matches.
        """
        enrollments = self._load()
        query_lower = query.strip().lower()

        # 1. Exact org unit ID
        if query.isdigit():
            for e in enrollments:
                if str(e.get("OrgUnit", {}).get("Id")) == query:
                    return e
            raise D2LError(f"No enrollment found with org unit ID: {query}")

        # 2. Exact code match
        for e in enrollments:
            code = e.get("OrgUnit", {}).get("Code", "")
            if code and code.lower() == query_lower:
                return e

        # 3. Substring match on name
        matches = []
        for e in enrollments:
            name = e.get("OrgUnit", {}).get("Name", "").lower()
            if query_lower in name:
                matches.append(e)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return self._disambiguate(query, matches)

        # 4. Word overlap
        query_words = set(query_lower.split())
        scored = []
        for e in enrollments:
            name = e.get("OrgUnit", {}).get("Name", "").lower()
            name_words = set(name.split())
            overlap = len(query_words & name_words)
            if overlap > 0:
                scored.append((overlap, e))
        scored.sort(key=lambda x: -x[0])
        if scored:
            best_score = scored[0][0]
            best = [e for s, e in scored if s == best_score]
            if len(best) == 1:
                return best[0]
            if len(best) > 1:
                return self._disambiguate(query, best)

        raise D2LError(f"No course matching '{query}'. Run 'd2l courses' to see available courses.")

    def _disambiguate(self, query, matches):
        """Handle multiple matches — pick the best or raise with options."""
        # If one is a Course Offering and others aren't, prefer it
        courses = [m for m in matches if m.get("OrgUnit", {}).get("Type", {}).get("Name") == "Course Offering"]
        if len(courses) == 1:
            return courses[0]
        if courses:
            matches = courses

        lines = [f"Multiple matches for '{query}':"]
        for i, m in enumerate(matches, 1):
            ou = m.get("OrgUnit", {})
            lines.append(f"  {i}. [{ou.get('Id')}] {ou.get('Name')}")
        lines.append("Be more specific or use the numeric ID.")
        raise D2LError("\n".join(lines))

    def resolve_id(self, query):
        """Resolve query to org unit ID."""
        return self.resolve(query)["OrgUnit"]["Id"]
