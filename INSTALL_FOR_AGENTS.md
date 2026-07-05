# d2l-cli Installation Guide for AI Agents

Read this entire file, then follow the steps. Your job is to install `d2l-cli`, configure the user's school, authenticate with the user's help when needed, verify that it works, and run first-time course onboarding.

Target: 5-15 minutes to a working read-only D2L Brightspace academic assistant. The user's only jobs are telling you their school and completing SSO login in a browser window.

## Step 0: Operating Rules

Before doing anything else:

1. Treat D2L as read-only. Never submit assignments, post discussions, modify grades, change settings, mark items complete/read, or perform actions that mutate D2L state.
2. Browser login is allowed only for authentication. Do not scrape course data through the browser. Use `d2l` CLI/API commands for course data.
3. Never ask the user to open DevTools, copy tokens, or paste credentials. `d2l login` captures the token automatically while they log in normally.
4. If required D2L data cannot be fetched because of auth, permissions, or missing access, stop and report the blocker. Do not guess from stale or partial data unless the user explicitly accepts that tradeoff.

Companion files (fetch by URL if you have not cloned anything):

- `https://raw.githubusercontent.com/Aaryan-Kapoor/d2l-cli/main/AGENTS.md` — agent operating guide and full command reference
- `https://raw.githubusercontent.com/Aaryan-Kapoor/d2l-cli/main/QUICKSTART.md` — short reference

## Step 1: Install d2l-cli

No repo clone is needed — install straight from git (or PyPI when published):

```bash
python -m pip install --user "d2l-cli[login] @ git+https://github.com/Aaryan-Kapoor/d2l-cli.git"
export PATH="$(python -m site --user-base)/bin:$PATH"
```

Verify:

```bash
d2l --version
d2l --json doctor
```

`doctor` reports every setup check with a `next_step` command. Use it whenever you are unsure what state the setup is in — after every step below, it tells you the next one.

If `d2l` is not found, persist the user scripts directory on PATH:

```bash
printf '\nexport PATH="%s:$PATH"\n' "$(python -m site --user-base)/bin" >> ~/.profile
```

`playwright install chromium` is optional: `d2l login` automatically falls back to the user's installed Chrome or Edge. Only run `python -m playwright install chromium` if login later reports that no browser could be launched.

## Step 2: Configure the School

Ask the user which school they attend. Then:

```bash
d2l setup --list-schools          # known presets (e.g. kennesaw/ksu, gastate/gsu)
d2l setup --school gsu            # configure a preset
d2l setup --host https://their-school.view.usg.edu   # any other Brightspace school
```

If the school is not a preset, ask the user for their Brightspace URL — it is the site they open to see their courses. Configuration is stored in `~/.d2l/config.json`; never edit source files to configure a school.

If the school uses SimpleSyllabus and the user wants syllabus support:

```bash
d2l setup --syllabus-host https://their-school.simplesyllabus.com
```

## Step 3: Authenticate

```bash
d2l token
```

If there is no valid token, try headless login first (reuses saved session cookies):

```bash
d2l login --headless
```

If headless login fails, hangs, or cannot capture a token, ask the user:

> I need you to log in to D2L in a browser so the CLI can capture a read-only API token — you just log in like normal. May I open the browser?

If they agree, run:

```bash
d2l login
```

The user completes browser/SSO login; the token is captured and saved automatically. After login, verify:

```bash
d2l token
d2l whoami
```

Do not inspect or scrape course data through the browser. Once auth works, return to CLI commands.

## Step 4: Verify Data Access

```bash
d2l --json doctor
d2l --md courses
d2l --md dump --shallow
```

Expected: doctor reports `"status": "ready"`, `courses` lists active enrollments, and `dump --shallow` returns a compact academic snapshot. If a required check fails, follow doctor's `next_step`. If a specific command fails but others work, continue only with commands that are relevant and clearly available.

## Step 5: Install the Agent Skill

The skill ships inside the package — install it into your own skill system:

```bash
d2l skill install ~/.claude/skills/d2l      # Claude Code (user-level)
d2l skill install .claude/skills/d2l        # Claude Code (project)
d2l skill install ~/.agents/skills/d2l      # OpenClaw (personal)
d2l skill install <your-skill-dir>/d2l      # any other agent system
```

`d2l skill cat` prints the SKILL.md if you only need the instructions. If your runtime has no skill support, keep following this file and `AGENTS.md` directly.

Do not copy auth files such as `~/.d2l/token.json` into public repos or shared skill registries.

## Step 6: Run Course Onboarding

```bash
d2l onboard
```

This interviews the user briefly about each active course and creates:

```text
D2L_COURSE_SOP.md
.d2l/onboarding.json
```

The SOP captures how the agent should work with each course. The state file stores a fingerprint of the active course list so future agents can tell whether onboarding has already been completed.

If the user wants a non-interactive starter file, run `d2l onboard --yes`, then tell them the SOP contains placeholders and should be reviewed.

## Step 7: How to Use the Onboarding State

Before repeating onboarding, check `d2l --json doctor` — its `onboarding` check reports whether onboarding is complete, stale (course list changed), or missing in the current directory.

If the course fingerprint still matches, read `D2L_COURSE_SOP.md` and follow it instead of interviewing the user again. If it changed (new term, added/dropped course), ask the user whether to refresh with `d2l onboard`.

## Step 8: Agent Usage Defaults

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
- Use `--md` or `--json` when processing output. Human output is for display only.
- Course arguments can be fuzzy names, course codes, or numeric org unit IDs. If multiple courses match, ask the user to disambiguate or use the numeric ID.
- Fetch the syllabus before answering grading-policy, course-rule, prerequisite, or instructor-policy questions when available.

## Step 9: Upgrade

```bash
d2l update
d2l --json doctor
```

`update` detects the install style automatically: a git checkout is pulled in place, package installs (pip/pipx) are reinstalled from the latest GitHub release.

If commands or active courses changed, refresh the SOP with `d2l onboard` if the user approves.

## Final Verification Checklist

Before declaring setup complete, verify:

- [ ] `d2l --version` works
- [ ] `d2l setup --show` shows the user's school
- [ ] `d2l token` is valid
- [ ] `d2l whoami` identifies the user
- [ ] `d2l --md courses` lists active courses
- [ ] `d2l --json doctor` reports `"status": "ready"`
- [ ] The skill is installed in your agent system (or your runtime has none)
- [ ] `D2L_COURSE_SOP.md` exists or the user explicitly skipped onboarding
- [ ] You told the user where the SOP file is
