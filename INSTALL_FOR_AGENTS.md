# d2l-cli Installation Guide for AI Agents

Read this entire file, then follow the steps. Your job is to install `d2l-cli`, authenticate it with the user's help when needed, verify that it works, and run first-time course onboarding.

Target: 10-20 minutes to a working read-only D2L Brightspace academic assistant.

## Step 0: Operating Rules

Before doing anything else:

1. Read `AGENTS.md` at the repo root. It is the agent operating guide for this CLI.
2. Treat D2L as read-only. Never submit assignments, post discussions, modify grades, change settings, mark items complete/read, or perform actions that mutate D2L state.
3. Browser login is allowed only for authentication. Do not scrape course data through the browser. Use `d2l` CLI/API commands for course data.
4. If required D2L data cannot be fetched because of auth, permissions, or missing access, stop and report the blocker. Do not guess from stale or partial data unless the user explicitly accepts that tradeoff.

If you fetched this file by URL before cloning, companion files live at:

- `https://raw.githubusercontent.com/Aaryan-Kapoor/d2l-cli/main/AGENTS.md`
- `https://raw.githubusercontent.com/Aaryan-Kapoor/d2l-cli/main/QUICKSTART.md`
- `https://raw.githubusercontent.com/Aaryan-Kapoor/d2l-cli/main/README.md`

## Step 1: Install d2l-cli

```bash
git clone https://github.com/Aaryan-Kapoor/d2l-cli.git ~/d2l-cli
cd ~/d2l-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[login]"
playwright install chromium
```

Verify:

```bash
d2l --version
d2l --help
```

If `d2l` is not found, either keep using the venv explicitly:

```bash
~/d2l-cli/.venv/bin/d2l --version
```

or add a shell alias/symlink appropriate for the user's environment.


## Step 2: Install the Agent Skill

This repo ships one canonical portable skill at:

```text
skills/d2l/
```

Install that folder into your own agent system. Do not maintain a separate hand-written adapter unless your runtime requires one. The skill keeps the same working D2L instructions as `AGENTS.md` and adds the onboarding/sentinel workflow.

Common installs:

```bash
# OpenClaw workspace skill (visible to the current workspace agent)
mkdir -p <workspace>/skills
cp -R ~/d2l-cli/skills/d2l <workspace>/skills/d2l

# OpenClaw personal skill (visible to all OpenClaw agents on this machine)
mkdir -p ~/.agents/skills
cp -R ~/d2l-cli/skills/d2l ~/.agents/skills/d2l

# Claude Code project skill
mkdir -p <project>/.claude/skills
cp -R ~/d2l-cli/skills/d2l <project>/.claude/skills/d2l
```

For other agent systems, copy `~/d2l-cli/skills/d2l/` into that system's native skill/plugin/instructions directory. If the system has no skill support, continue following this `INSTALL_FOR_AGENTS.md` file and `AGENTS.md` directly.

Verify the skill folder contains:

```text
skills/d2l/SKILL.md
skills/d2l/scripts/install.sh
skills/d2l/scripts/doctor.sh
skills/d2l/scripts/onboard.sh
skills/d2l/references/
```

Do not copy auth files such as `~/.d2l/token.json` into public repos or shared skill registries.

## Step 3: Configure the Institution

Open `src/d2l/config.py` and verify the Brightspace host/version settings match the user's institution.

For Kennesaw State University, the repo is preconfigured. For other schools, update:

```python
LMS_HOST = "https://your-school.view.usg.edu"
TENANT_ID = "your-tenant-id-here"
```

If the school uses SimpleSyllabus and the user wants syllabus support, update `src/d2l/commands/syllabus.py`:

```python
SYLLABUS_SEARCH_URL = "https://your-school.simplesyllabus.com/api2/syllabus-search"
SYLLABUS_FULL_URL = "https://your-school.simplesyllabus.com/api2/doc-full-page-get"
```

If you are unsure about institution config, ask the user for their Brightspace URL. Do not scrape pages to infer course data.

## Step 4: Authenticate

Check current auth:

```bash
d2l token
```

If there is no valid token, try headless login first:

```bash
d2l login --headless
```

If headless login fails, hangs, or cannot capture a token, ask the user:

> I need you to complete D2L login in a browser so I can capture a read-only API token. May I launch `d2l login` for you?

If they agree, run:

```bash
d2l login
```

The user completes browser/SSO login interactively. After login, verify:

```bash
d2l token
d2l whoami
```

Do not inspect or scrape course data through the browser. Once auth works, return to CLI commands.

## Step 5: Verify Data Access

Run:

```bash
d2l --md courses
d2l --md dump --shallow
```

Expected result:

- `courses` lists active enrollments.
- `dump --shallow` returns a compact academic snapshot with enrollments and due/overdue information.

If these fail due to auth or permissions, stop and report the blocker. If a specific command fails but others work, continue only with commands that are relevant and clearly available.

## Step 6: Run Course Onboarding

Run the interactive onboarding command:

```bash
d2l onboard
```

This creates:

```text
D2L_COURSE_SOP.md
.d2l/onboarding.json
```

The SOP captures how the agent should work with each active course. The state file stores a fingerprint of the active course list so future agents can tell whether onboarding has already been completed.

If the user wants a non-interactive starter file, run:

```bash
d2l onboard --yes
```

Then tell the user the SOP contains placeholders and should be reviewed.

## Step 7: How to Use the Onboarding State

Before repeating onboarding, check:

```bash
ls D2L_COURSE_SOP.md .d2l/onboarding.json
```

Then run:

```bash
d2l onboard
```

If the active course fingerprint still matches, the command reports that onboarding is already complete. Read `D2L_COURSE_SOP.md` and follow it instead of interviewing the user again.

If the course fingerprint changed, ask the user whether to refresh onboarding. This usually means a new term, added/dropped course, or renamed course.

## Step 8: Agent Usage Defaults

Use these command patterns:

```bash
# Broad overview
d2l --md dump --shallow

# Full snapshot
d2l --md dump

# One course
d2l --md dump --course "course name"

# Grades and policy context
d2l --md grades "course name"
d2l --md syllabus "course name"

# Due dates and activity
d2l --md due --days 14
d2l --md overdue
d2l --md updates

# Course materials
d2l --md content "course name" --toc
d2l download-content "course name" "module or file name" -o ./notes
```

Important:

- Put global flags before the command: `d2l --md grades "calc"`, not `d2l grades --md "calc"`.
- Use `--md` or `--json` when processing output.
- Use human output only for display.
- Course arguments can be fuzzy names, course codes, or numeric org unit IDs.
- If multiple courses match, ask the user to disambiguate or use the numeric ID.
- Fetch the syllabus before answering grading-policy, course-rule, prerequisite, or instructor-policy questions when available.

## Step 9: Optional Project Integration

If the user wants their agent project to remember how to use D2L, copy or reference:

- `skills/d2l/` as the canonical portable agent skill
- `AGENTS.md` for repo-level agent behavior and full command reference
- `QUICKSTART.md` for short setup/reference
- `D2L_COURSE_SOP.md` after onboarding

Do not copy `.d2l/onboarding.json` or `~/.d2l/token.json` into public repos. They are local state/auth files.

## Step 10: Upgrade

To update the CLI later:

```bash
cd ~/d2l-cli
git pull origin main
source .venv/bin/activate
pip install -e ".[login]"
d2l --version
d2l token
```

If commands or active courses changed, run:

```bash
d2l onboard
```

and refresh the SOP if the user approves.

## Final Verification Checklist

Before declaring setup complete, verify:

- [ ] `d2l --version` works
- [ ] `d2l token` is valid
- [ ] `d2l whoami` identifies the user
- [ ] `d2l --md courses` lists active courses
- [ ] `d2l --md dump --shallow` works
- [ ] `D2L_COURSE_SOP.md` exists or the user explicitly skipped onboarding
- [ ] `.d2l/onboarding.json` exists if onboarding was run
- [ ] You told the user where the SOP file is
