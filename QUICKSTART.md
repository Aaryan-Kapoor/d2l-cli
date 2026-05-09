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

If the token is expired or invalid, first try:

```bash
d2l login --headless
```

If that fails, hangs, or cannot capture a token, ask the user whether you may launch the browser for them. If they agree, run:

```bash
d2l login
```

The user can complete browser/SSO login interactively. Do not scrape D2L course data through the browser; use the CLI/API after login.

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
d2l onboard                                 # interactive course SOP setup
d2l onboard --yes                           # non-interactive starter SOP
```

Course names are fuzzy — `"calc"`, `"data structures"`, `"econ"` all work.

## Output flags

- No flag: human-readable tables (for display)
- `--md`: markdown optimized for AI consumption (use this)
- `--json`: structured JSON (for parsing)

Put the flag before the command: `d2l --md grades "calc"`

## Safety defaults

- Use `d2l` only for read-only Brightspace data.
- Never submit assignments, post discussions, modify grades, change settings, or perform actions that mutate D2L state.
- Do not use browser automation, page scraping, or in-page JavaScript to retrieve D2L course data.
- If required D2L data cannot be fetched because of auth, permissions, or missing access, stop and report the blocker instead of guessing.
- For grading policies, course rules, grading weights, prerequisites, or instructor policies, fetch the syllabus first with `d2l --md syllabus COURSE` when available.

## Course onboarding

For a first-time setup, use:

```bash
d2l onboard
```

This interviews the user about active courses and writes:

```text
D2L_COURSE_SOP.md
.d2l/onboarding.json
```

The state file stores a fingerprint of the active course list. On future runs, if the state file and SOP exist and the fingerprint still matches, onboarding is already done. Read the SOP instead of repeating setup. If the active course list changes, refresh onboarding with user confirmation.

Recommended flow:

1. Check auth with `d2l token`.
2. Run `d2l onboard` for interactive setup, or `d2l onboard --yes` for a starter SOP without prompts.
3. Ask about each course's real source of truth, weekly rhythm, grading style, external tools, and what help the user wants.
4. Let the generated SOP capture course IDs, source-of-truth hierarchy, per-course workflow, check cadence, grading/policy notes, common commands, ambiguities, and stop/ask rules.

## Skill file

Copy `.claude/skills/d2l/SKILL.md` into your project's skills directory for full integration with Claude Code / OpenClaw / other Agent framework.
