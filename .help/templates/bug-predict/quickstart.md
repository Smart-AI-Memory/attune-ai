---
type: quickstart
name: bug-predict-quickstart
feature: bug-predict
depth: quickstart
generated_at: 2026-05-16T06:19:45.792794+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Quickstart: Bug Prediction

Scan a directory for likely bug locations based on code patterns and complexity.

```
/bug-predict src/
```

You'll see a risk report like this in your Claude Code conversation:

```
Bug Prediction Report
Risk Score: 73/100 | Files: 34 | Findings: 8

HIGH (2 findings)
  src/hooks/executor.py:89   dangerous_eval  eval() on user input
  src/plugins/loader.py:142  dangerous_eval  exec() in plugin loader

MEDIUM (3 findings)
  src/api/webhook.py:67      broad_exception bare except: masks errors
  ...
```

## Steps

### 1. Choose your scan target

Run the command with the path you want to analyze:

| Command | What it scans |
|---------|---------------|
| `/bug-predict src/auth.py` | One file |
| `/bug-predict src/` | A directory tree |
| `/bug-predict .` | The whole project |

If you omit the path, the skill asks which files to scan and whether to show all findings or only HIGH severity results.

### 2. Read the report

The report groups findings by severity — HIGH, MEDIUM, and LOW — and includes the file path, line number, pattern type, and a plain-English description for each finding. File links are clickable so you can jump directly to the flagged line.

The three pattern types are:

- **dangerous_eval** — `eval()`, `exec()`, or `compile()` on input (HIGH)
- **broad_exception** — bare `except:` or unlogged `except Exception:` that silently swallows errors (MEDIUM)
- **incomplete_code** — TODO, FIXME, HACK, or XXX comments marking unfinished paths (LOW)

### 3. Act on HIGH findings first

Ask Claude Code to fix the most critical results:

```
fix the dangerous_eval in src/hooks/executor.py
```

The orchestrator coordinates three subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — to produce prioritized, actionable refactoring and testing recommendations alongside each finding.

**Next:** Run a focused scan on your highest-risk module: `/bug-predict src/auth/` to see whether risk scores improve after your fixes.
