---
name: d2l
description: Fetch read-only academic data from D2L Brightspace (KSU). Use when the user asks about their courses, grades, assignments, due dates, quizzes, syllabus, announcements, or anything related to their classes.
allowed-tools: Bash(d2l *)
argument-hint: [command] [args...]
---

# D2L Brightspace Academic Data

You have access to the `d2l` CLI tool which fetches READ-ONLY data from the user's D2L Brightspace LMS at Kennesaw State University.

## Quick Reference

```bash
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
```

## Output Formats

- Default: human-readable aligned tables
- `--json`: structured JSON (use for programmatic analysis)
- `--md`: AI-optimized markdown with IDs, full text, ISO dates

**Always use `--md` or `--json` when you need to process the data.** Human format is for display only.

## Course Name Resolution

Course arguments accept fuzzy names, codes, or numeric IDs:
- `"data structures"` → matches "Data Structures Section 04 Spring Semester 2026 CO"
- `"econ"` → matches "Contemporary Economic Issues..."
- `"calc"` → matches "Calculus II..."
- `3824526` → exact org unit ID

## When Token Expires

The D2L token expires every ~1 hour. If you see "Token expired. Run: d2l login", tell the user to run `d2l login` — it will open a browser, auto-capture a fresh token, and save it.

## Important

- This tool is **strictly read-only**. It cannot submit assignments, post discussions, or modify anything.
- All data comes from the D2L Brightspace API at kennesaw.view.usg.edu.
- The `d2l dump --md` command is the best way to get full context about the user's academic situation.

## Syllabus

`d2l syllabus COURSE` fetches the full syllabus from KSU's SimpleSyllabus system (separate from D2L, no auth needed). It includes course description, grading breakdown, policies, instructor info, and learning outcomes. Use this when the user asks about course policies, grading weights, prerequisites, or what a course covers.

## Responding to the User

When the user asks about their classes:
1. Run the appropriate `d2l` command to fetch the data
2. Parse the output and present it clearly
3. Offer analysis (grade calculations, upcoming deadline warnings, etc.)
4. If they ask "what's going on with my classes" or similar broad questions, use `d2l --md dump --shallow` first for a quick overview, then drill into specific courses as needed.
5. If they ask about grading policies, what grade they need, or course rules — fetch the syllabus first with `d2l --md syllabus COURSE`.
