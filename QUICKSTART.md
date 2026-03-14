# Agent Quick Start

You are an AI agent. This file tells you how to use the `d2l` CLI tool to access the user's D2L Brightspace academic data. Everything is read-only.

## Setup (run once)

```bash
cd /path/to/d2l-cli
pip install -e .
d2l login          # user must do this — opens browser for SSO
```

## Check auth

```bash
d2l token          # shows token status + time remaining
```

If token is expired, tell the user to run `d2l login`.

## Commands

```bash
d2l whoami                                  # verify identity
d2l courses                                 # list enrolled courses
d2l grades "course name"                    # grades for a course
d2l grades --final                          # final grades across all courses
d2l assignments "course name"               # assignments + due dates
d2l due                                     # items due in next 7 days
d2l due --days 14                           # items due in next 14 days
d2l overdue                                 # overdue items
d2l quizzes "course name"                   # quiz list
d2l news "course name"                      # announcements
d2l syllabus "course name"                  # full syllabus (grading, policies)
d2l content "course name" --toc             # table of contents
d2l discussions "course name"               # discussion forums
d2l updates                                 # unread counts
d2l download "course" "assignment" -o DIR   # download assignment files
d2l download-content "course" "module" -o DIR  # download content files
d2l --md dump                               # full academic snapshot
d2l --md dump --since 24                    # what's new in last 24 hours
d2l --md dump --course "course name"        # one course only
d2l --json dump                             # machine-readable JSON
```

Course names are fuzzy — `"calc"`, `"data structures"`, `"econ"` all work.

## Output flags

- No flag: human-readable tables (for display)
- `--md`: markdown optimized for AI consumption (use this)
- `--json`: structured JSON (for parsing)

Put the flag before the command: `d2l --md grades "calc"`

## Skill file

Copy `.claude/skills/d2l/SKILL.md` into your project's `.claude/skills/d2l/` directory for full integration with Claude Code / OpenClaw.
