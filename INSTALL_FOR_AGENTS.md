# d2l-cli Installation Guide for AI Agents

You are an AI agent setting up `d2l-cli` — a read-only CLI for the user's D2L Brightspace courses — so that you and future agent sessions can answer questions about the user's classes.

This file is self-contained: everything you need is in here and in the skill you will install in Step 2. Follow the steps in order. The user should only be needed twice: to tell you their school, and to complete a browser login.

## Step 0: Operating Rules

These rules apply during setup and forever after:

1. Treat D2L as read-only. Never submit assignments, post discussions, modify grades, change settings, mark items complete/read, or perform actions that mutate D2L state.
2. The browser is for authentication only. Never scrape course data through the browser — all course data comes from `d2l` commands.
3. Never ask the user to open DevTools, copy tokens, or paste credentials. `d2l login` captures the token automatically while they log in normally.
4. If required D2L data cannot be fetched because of auth, permissions, or missing access, stop and report the blocker. Do not guess from stale or partial data unless the user explicitly accepts that tradeoff.

## Step 1: Install the CLI

No repo clone is needed — install straight from git:

```bash
python -m pip install --user "d2l-cli[login] @ git+https://github.com/Aaryan-Kapoor/d2l-cli.git"
export PATH="$(python -m site --user-base)/bin:$PATH"
d2l --version
```

If `d2l` is not found, persist the user scripts directory on PATH:

```bash
printf '\nexport PATH="%s:$PATH"\n' "$(python -m site --user-base)/bin" >> ~/.profile
```

Notes:

- `playwright install chromium` is **not** required: `d2l login` automatically falls back to the user's installed Chrome or Edge. Only run `python -m playwright install chromium` if login later reports that no browser could be launched.
- To update later: `d2l update`.

## Step 2: Install the Skill — Into Your Own Skill Directory

The package bundles a portable agent skill (SKILL.md + reference docs). Install it into **your own agent system's skill directory** right now, before continuing — it is your permanent reference for commands, safety rules, and workflows, and it makes every future session productive without this file.

```bash
d2l skill install ~/.claude/skills/d2l      # Claude Code (user-level)
d2l skill install .claude/skills/d2l        # Claude Code (project-level)
d2l skill install ~/.agents/skills/d2l      # OpenClaw (personal)
d2l skill install <your-skill-dir>/d2l      # any other agent system
```

Pick the location that matches the system you are running in. If your runtime has no skill support, run `d2l skill cat` and keep its contents in your working context instead.

## Step 3: Configure the User's School

Ask the user: **"Which school do you attend?"** Then:

```bash
d2l setup --list-schools                    # known presets (kennesaw/ksu, gastate/gsu)
d2l setup --school gsu                      # configure a preset
d2l setup --host https://their-school.view.usg.edu    # any other Brightspace school
```

If their school is not a preset, ask for their Brightspace URL — it's the website they open to see their courses. Configuration is stored in `~/.d2l/config.json`. Never edit source files to configure a school.

If the school uses SimpleSyllabus and the user wants syllabus support:

```bash
d2l setup --syllabus-host https://their-school.simplesyllabus.com
```

## Step 4: Authenticate

Ask the user:

> I need you to log in to D2L in a browser window so the CLI can capture a read-only API token — you just log in like normal. May I open the browser?

When they agree, run:

```bash
d2l login
```

A browser opens; the user completes their normal SSO login; the token is captured and saved automatically. Verify:

```bash
d2l token
d2l whoami
```

**After this one login, auth maintains itself.** Tokens expire hourly, but every `d2l` command automatically refreshes the token in the background using the saved browser session. You should almost never see an auth error again — if you do, the saved session has fully expired, and the fix is to ask the user for one more `d2l login`.

## Step 5: Verify Data Access

```bash
d2l --json doctor
d2l --md courses
d2l --md dump --shallow
```

Expected: doctor reports `"status": "ready"`, `courses` lists active enrollments, and `dump --shallow` returns a compact academic snapshot.

`d2l --json doctor` is your compass for this entire setup: it reports every check (config, token, API, courses, onboarding) with a `next_step` command. Whenever you are unsure what state things are in — during setup or months from now — run it and follow `next_step`.

## Step 6: Onboard the Courses

```bash
d2l onboard
```

This briefly interviews the user about each active course (source of truth for deadlines, grading style, what help they want) and writes:

```text
D2L_COURSE_SOP.md      # how to work with this user's courses
.d2l/onboarding.json   # state + fingerprint of the active course list
```

If the user prefers no interview right now, run `d2l onboard --yes` for a starter SOP with placeholders, and tell them to review it later.

On any future run: if doctor's `onboarding` check says complete and current, read `D2L_COURSE_SOP.md` and follow it — do not re-interview the user. If it says stale (course list changed — new term, added/dropped course), ask the user before refreshing with `d2l onboard`.

## Step 7: Daily Usage Patterns

```bash
d2l --md dump --shallow                 # broad overview
d2l --md dump --since 24                # what changed in the last 24h
d2l --md dump --course "course name"    # full context for one course
d2l --md grades "course name"           # grades
d2l --md syllabus "course name"         # policies, grading weights
d2l --md due --days 14                  # upcoming deadlines
d2l --md overdue                        # overdue items
d2l --md content "course name" --toc    # course materials index
d2l download-content "course name" "module name" -o ./notes    # lecture files
```

Rules of thumb:

- Global flags go **before** the command: `d2l --md grades "calc"`, never `d2l grades --md "calc"`.
- Use `--md` or `--json` whenever you process output; bare human tables are for display only.
- Course arguments accept fuzzy names, course codes, or numeric IDs. If multiple courses match, ask the user or use the numeric ID.
- Fetch the syllabus before answering any grading-policy, course-rule, prerequisite, or instructor-policy question.

## Final Checklist

Before declaring setup complete:

- [ ] `d2l --version` works
- [ ] The skill is installed in your skill directory (Step 2)
- [ ] `d2l setup --show` shows the user's school
- [ ] `d2l whoami` identifies the user
- [ ] `d2l --json doctor` reports `"status": "ready"`
- [ ] `D2L_COURSE_SOP.md` exists (or the user explicitly skipped onboarding)
- [ ] You told the user where the SOP file is and that login now refreshes itself
