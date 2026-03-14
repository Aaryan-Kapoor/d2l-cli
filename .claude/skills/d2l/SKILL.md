---
name: d2l
description: Fetch read-only academic data from D2L Brightspace. Use when the user asks about their courses, grades, assignments, due dates, quizzes, syllabus, announcements, or anything related to their classes.
allowed-tools: Bash(d2l *)
argument-hint: [command] [args...]
---

Read the full command reference from `AGENTS.md` at the repo root, then use the `d2l` CLI to answer the user's question.

Key commands: `d2l --md dump --shallow` for overview, `d2l grades COURSE`, `d2l assignments COURSE`, `d2l due`, `d2l overdue`, `d2l syllabus COURSE`, `d2l download COURSE ASSIGNMENT -o DIR`, `d2l download-content COURSE MODULE -o DIR`.

Always use `--md` or `--json` flags when processing data. Token expires hourly — if expired, tell user to run `d2l login`.
