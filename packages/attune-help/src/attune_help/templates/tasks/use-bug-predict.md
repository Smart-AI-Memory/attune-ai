---
type: task
name: use-bug-predict
tags: [skill, task]
source: plugin/skills/bug-predict/SKILL.md
---

# How to Run Bug Prediction

## Quick start

The fastest way: just say what you want to scan.

```
predict bugs in src/
```

Or use the skill directly:

```
/bug-predict src/
```

That's it. You'll get a risk report grouped by severity
with clickable file links and risk scores.

## Guided flow

If you don't specify a path, the skill walks you through
scoping before it runs:

1. **"Which files or directory should I scan?"** — pick a
   file, a directory, or the whole project. Defaults to
   `src/` if you skip this.
2. **"Show all findings, or only HIGH severity?"** — filter
   out noise when you just want the critical stuff.

This Socratic flow keeps the scan focused so you're not
drowning in low-priority TODOs when you only care about
`eval()` usage.

## Choosing what to scan

| Command | What it scans |
|---------|---------------|
| `/bug-predict src/auth.py` | One file |
| `/bug-predict src/` | A directory tree |
| `/bug-predict .` | The whole project |

You can also use natural language:

```
where are bugs most likely in the workflows module?
what might break in src/api/?
find risky code in the auth package
```

## Reading the results

Results come back as a risk report sorted by severity:

```
Bug Prediction Report
Risk Score: 73/100 | Files: 34 | Findings: 8

HIGH (2 findings)
  src/hooks/executor.py:89   dangerous_eval  eval() on user input
  src/plugins/loader.py:142  dangerous_eval  exec() in plugin loader

MEDIUM (3 findings)
  src/api/webhook.py:67      broad_exception bare except: masks errors
  src/config.py:203          broad_exception except Exception without logging
  src/memory/store.py:88     broad_exception swallowed error in write path

LOW (3 findings)
  src/auth/session.py:45     incomplete_code TODO: add token rotation
  src/api/routes.py:112      incomplete_code FIXME: rate limiting
  src/cli_router.py:78       incomplete_code HACK: temporary workaround
```

Each finding shows the file, line number, pattern type,
and a plain-English description. File links are clickable
-- click to jump directly to the issue.

## What to do next

After reviewing the report:

- **Fix the HIGH findings first** — ask "fix the
  dangerous_eval in executor.py" for a guided fix
- **Generate tests** — ask "write tests for the flagged
  files" to prevent regressions
- **Go deeper on one area** — ask "predict bugs in
  src/auth/" for a focused scan
- **Track trends** — run the scan weekly to see if risk
  scores are improving or drifting

## Want to learn more?

- Say **"tell me more"** for the complete reference
  -- every pattern, scoring, configuration
- Say **"what is bug prediction?"** to go back to the
  overview
- Say **"scan for security issues"** to run a security
  audit instead
