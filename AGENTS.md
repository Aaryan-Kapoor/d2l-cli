# D2L Brightspace Academic Data

You have access to the `d2l` CLI tool which fetches READ-ONLY data from the user's D2L Brightspace LMS.

## Quick Reference

```bash
# Setup & diagnosis
d2l --json doctor                  # Full setup state + the exact next command to run
d2l setup --list-schools           # Known school presets
d2l setup --school gsu             # Configure a preset school
d2l setup --host https://your-school.view.usg.edu   # Any Brightspace school

# Identity & auth
d2l token                          # Check if token is valid
d2l whoami                         # Current user info

# Courses
d2l courses                        # List enrolled courses
d2l courses --all                  # Include inactive/past

# Grades
d2l grades "data structures"       # Grades for a course (fuzzy name match)
d2l grades --final                 # Final grades across all courses
d2l --json grades "econ"           # JSON output

# Assignments
d2l assignments "calc"             # Assignments + due dates

# Due dates & overdue
d2l due                            # Items due in next 7 days
d2l due --days 14                  # Items due in next 14 days
d2l overdue                        # Overdue items

# Calendar
d2l calendar                       # Events next 7 days
d2l calendar --course "data structures" --days 30

# News / Announcements
d2l news "data structures"         # Course announcements
d2l news                           # Activity feed

# Quizzes
d2l quizzes "data structures"      # Quiz list + dates

# Discussions
d2l discussions "data structures"  # Discussion forums
d2l discussions "data structures" --forum 12345    # Topics in forum
d2l discussions "data structures" --posts 12345 67890  # Posts

# Content
d2l content "data structures"      # Course modules
d2l content "data structures" --toc  # Full table of contents

# Download assignment files (starter code, instructions, etc.)
d2l download "data structures" "A06" -o ./assignment6
d2l download "calc" "review" -o ./calc-review

# Download content files (lecture notes, slides, study guides)
d2l download-content "calc" "Exam Preparation" -o ./exam-prep
d2l download-content "calc" "Unit 3 Materials" -o ./unit3   # recursive
d2l download-content "data structures" "Big-O" -o ./bigo

# Syllabus (fetched from SimpleSyllabus, no auth needed)
d2l syllabus "data structures"     # Full syllabus text
d2l --md syllabus "calc"           # Markdown format
d2l --json syllabus "econ"         # JSON with all fields

# Updates
d2l updates                        # Unread counts across courses

# Full AI snapshot
d2l --md dump                      # Everything, markdown format
d2l --md dump --course "data structures"  # One course
d2l --md dump --shallow            # Just enrollments + due/overdue
d2l --md dump --since 24           # Only new stuff from last 24 hours
d2l --md dump --since 48           # Last 2 days
d2l --json dump                    # Machine-readable JSON

# First-time course workflow setup
d2l onboard                        # Interactive course SOP setup
d2l onboard --yes                  # Starter SOP, only if the user declines the interview
```

## First-Time Setup

Run `d2l --json doctor` before anything else. It reports every setup check
(config, token, API access, courses, onboarding) with a `next_step` command —
follow it instead of guessing state.

If no school is configured, ask the user which school they attend, then run
`d2l setup --school NAME` (see `d2l setup --list-schools`) or
`d2l setup --host <their Brightspace URL>`. Never edit source files to
configure a school.

## Agent Defaults

1. **Read-only only.** Use `d2l` only for read-only Brightspace data. Never submit assignments, post discussions, modify grades, change settings, or perform actions that mutate D2L state.
2. **Prefer structured output.** Use `--md` or `--json` when processing data. Human/table output is for display only.
3. **Put global flags before the command.** Use `d2l --md grades "calc"`, not `d2l grades --md "calc"`.
4. **Auth maintains itself.** The CLI silently refreshes expired tokens using the saved browser session before any command fails. If a command still reports a sign-in error, the saved session has fully expired — ask the user whether you may launch `d2l login`, then run it so they can log in interactively. Never ask them to copy tokens or open DevTools.
5. **No browser scraping.** Do not use browser automation, page scraping, or in-page JavaScript to retrieve D2L course data. Browser login is only for authentication; course data should come from the CLI/API paths.
6. **Resolve courses carefully.** Course arguments can be fuzzy names, course codes, or numeric org unit IDs. If multiple courses match, ask the user to disambiguate or use the numeric ID.
7. **Fetch policy sources first.** For grading policies, course rules, grading weights, prerequisites, or instructor policies, fetch the syllabus first with `d2l --md syllabus COURSE` when available.
8. **Stop on required-source blockers.** If required D2L data cannot be fetched because of auth, permissions, or missing access, stop and report the blocker. Do not answer from stale, partial, or guessed data unless the user explicitly accepts that tradeoff.

## Output Formats

- Default: human-readable aligned tables
- `--json`: structured JSON (use for programmatic analysis)
- `--md`: AI-optimized markdown with IDs, full text, ISO dates

**Always use `--md` or `--json` when you need to process the data.** Human format is for display only.

Put the flag before the command: `d2l --md grades "calc"`

## Course Name Resolution

Course arguments accept fuzzy names, codes, or numeric IDs:
- `"data structures"` → matches "Data Structures Section 04..."
- `"econ"` → matches "Contemporary Economic Issues..."
- `"calc"` → matches "Calculus II..."
- `3824526` → exact org unit ID

## When Token Expires

Tokens expire hourly, but you normally never notice: every `d2l` command
auto-refreshes the token in the background from the saved browser session.

If a command still fails with a sign-in error, the saved session itself has
expired. Ask the user whether you may launch the browser for them; if they
agree, run:

```bash
d2l login
```

The user completes browser/SSO login interactively, and the CLI saves the
refreshed token. (`d2l login --headless` and `D2L_NO_AUTO_LOGIN=1` exist for
manual control, but are rarely needed.)

## Important

- This tool is **strictly read-only**. It cannot submit assignments, post discussions, modify grades, or change D2L state.
- Browser login is allowed only for authentication. Do not inspect or scrape course data through the browser.
- The `d2l dump --md` command is the best way to get full context about the user's academic situation.

## Syllabus

`d2l syllabus COURSE` fetches the full syllabus from SimpleSyllabus (separate from D2L, no auth needed). It includes course description, grading breakdown, policies, instructor info, and learning outcomes. Use this when the user asks about course policies, grading weights, prerequisites, or what a course covers.

## Responding to the User

When the user asks about their classes:
1. Run the appropriate `d2l` command to fetch the data.
2. Parse the output and present it clearly.
3. Offer analysis (grade calculations, upcoming deadline warnings, etc.).
4. If they ask "what's going on with my classes" or similar broad questions, use `d2l --md dump --shallow` first for a quick overview, then drill into specific courses as needed.
5. If they ask about grading policies, what grade they need, or course rules, fetch the syllabus first with `d2l --md syllabus COURSE`.
6. If required D2L data cannot be fetched, stop and explain the blocker instead of guessing.

## Course Onboarding SOP

When the user asks to onboard their courses or set up an academic workflow, use:

```bash
d2l onboard
```

The command creates a course-operations SOP file for the current term and a sentinel state file:

```text
D2L_COURSE_SOP.md
.d2l/onboarding.json
```

The state file stores a fingerprint of the active course list. On future runs, if `.d2l/onboarding.json` exists, the SOP file exists, and the course fingerprint still matches, onboarding is already complete. Read the SOP instead of repeating the interview. If the fingerprint changed, ask the user whether to refresh onboarding.

Onboarding flow:

1. Check auth with `d2l token`. If needed, follow the auth flow above.
2. Run `d2l onboard` and interview the user — that conversation is the default. Use `d2l onboard --yes` (starter SOP, no prompts) only if the user declines.
3. Interview the user briefly about each course: grading style, professor quirks, where deadlines are authoritative, recurring weekly rhythm, external tools, and what kind of help they want from an agent.
4. The generated SOP includes:
   - course list and IDs
   - source-of-truth hierarchy for each course (D2L due dates, syllabus, weekly modules, external docs, etc.)
   - per-course workflow/check cadence
   - grading/policy notes
   - common commands to run
   - known ambiguities or missing info
   - explicit rules for when to stop and ask the user
5. Keep the SOP factual and user-specific, but avoid hard-coding private credentials or secrets.
6. Finish with a hand-off: run `d2l --md due --days 14`, mention one concrete thing you found, and offer 2–3 things the user could ask right now, built from their actual courses — not generic examples.
