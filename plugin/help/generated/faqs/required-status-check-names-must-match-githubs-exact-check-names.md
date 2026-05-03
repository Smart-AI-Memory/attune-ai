---
name: required-status-check-names-must-match-githubs-exact-check-names
source: .claude/CLAUDE.md
summary: This template explains how to resolve silent merge blocks caused by required
  status check names that don't exactly match GitHub's reported check names, and provides
  instructions for retrieving and correctly configuring the exact check name strings.
tags:
- git
type: faq
---

# FAQ: Required Status Check Names Must Match GitHub's Exact Check Names

## Answer

If a required status check name doesn't exactly match the name GitHub reports, merges will be silently blocked — the expected check never appears as passing, even if the underlying job succeeds.

**Example:** A branch protection rule configured with `Analyze Python` will never be satisfied if the actual check name is `Analyze (python)` (note the parentheses). GitHub treats these as two different checks.

## How to Fix

Before adding a check to your branch protection rules, retrieve the exact check name as GitHub reports it:

```sh
gh pr checks <PR>
```

Copy the check name character-for-character from the output — including parentheses, capitalization, and spacing — and use that exact string in your branch protection configuration.

**Incorrect (will silently block merges):**
```
Analyze Python
```

**Correct:**
```
Analyze (python)
```

## Related Topics

- **Error:** `Required status check names must match GitHub's exact check names`
