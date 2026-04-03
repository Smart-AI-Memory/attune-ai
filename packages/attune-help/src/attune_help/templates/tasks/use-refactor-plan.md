---
type: task
name: use-refactor-plan
tags: [refactoring, skill, task]
source: plugin/skills/refactor-plan/SKILL.md
---

# How to Run a Refactor Plan

## Quick start

The fastest way: just say what you want to analyze.

```
analyze src/auth/ for refactoring opportunities
```

Or use the skill directly:

```
/refactor-plan src/auth/
```

That's it. You'll get a prioritized roadmap with effort
estimates and suggested fixes.

## Choosing what to analyze

You can analyze a single file, a directory, or a specific
area of concern:

| Command | What it scans |
|---------|---------------|
| `/refactor-plan src/models.py` | One file |
| `/refactor-plan src/workflows/` | A directory tree |
| `/refactor-plan .` | The whole project |

If you don't specify a path, you'll be asked:

> "Which file or directory needs refactoring analysis?"

## Choosing a focus

By default, the plan covers everything. If you have a
specific concern, say so:

- "simplify src/engine.py" — reduce complexity only
- "find duplication in src/" — just copy-paste detection
- "check coupling between auth and models" — dependency
  analysis
- "full refactoring roadmap for src/" — everything
  (default)

## Reading the roadmap

Results come back as a prioritized table:

```
Refactoring Roadmap
Score: 64/100 | Files: 23 | Issues: 11

Priority 1 (High Impact, Low Effort)
  src/engine.py:45       God class — 14 responsibilities
                         Fix: Split into Engine + Parser + Validator
                         Effort: ~2 hours | Risk: Medium

  src/utils.py:89        Duplicated in 4 places
                         Fix: Extract to shared helper
                         Effort: ~30 min | Risk: Low

Priority 2 (High Impact, High Effort)
  src/workflows/base.py  Cyclomatic complexity 28
                         Fix: Extract strategy pattern
                         Effort: ~4 hours | Risk: High

Priority 3 (Low Impact)
  src/config.py:12       Unclear naming (cfg, mgr, proc)
                         Fix: Rename to intent
                         Effort: ~15 min | Risk: Low
```

Each item includes the file, line, description, suggested
fix, effort estimate, and risk level. Clickable file links
let you jump straight to the issue.

## Acting on recommendations

After reviewing the roadmap, you have several options:

- **Start with the top item** — ask "refactor the god
  class in engine.py" and it generates the refactored code
- **Simplify one file** — ask "simplify src/engine.py"
  for targeted complexity reduction
- **Generate tests first** — ask "write tests for
  src/engine.py" before making structural changes
- **Go deeper** — ask "deep analysis of the coupling
  between auth and models"
- **Get the full reference** — say "tell me more" for
  every debt type and scoring detail

## Want to learn more?

- Say **"tell me more"** for the complete reference —
  every debt type, scoring, and configuration
- Say **"what is refactor plan?"** to go back to the
  overview
- Say **"review my code"** to run a code quality review
  instead
