---
paths:
  - "docs/**"
  - "mkdocs.yml"
---

# Documentation Patterns

Auto-generated from session evaluation.
**Created:** 2026-01-24
**Source:** Documentation reorganization session

---

## Preferences

### Consolidate over scatter
**Confidence:** High

When documentation is fragmented across multiple files with similar content (e.g., multiple "quickstart" guides), consolidate into a single clear location rather than keeping multiple overlapping versions.

**Apply when:**
- Multiple files cover the same topic
- Users report confusion about "which doc to read"
- Onboarding content is scattered

**Example:**
```
Before: 6 scattered quickstart files
After:  1 getting-started/ directory with clear progression
```

---

### Clear user journey
**Confidence:** High

Documentation should have explicit progression with time estimates. Users should know exactly what to read in what order.

**Pattern:**
```
Step 1 (X min) → Step 2 (Y min) → Step 3 (Z min)
```

**Apply when:**
- Creating onboarding docs
- Reorganizing tutorials
- Building learning paths

**Example:**
```markdown
| Step | What You'll Do | Time |
|------|----------------|------|
| 1. Installation | Install and configure | 2 min |
| 2. First Steps | Run first workflow | 5 min |
| 3. Choose Path | Pick your approach | 3 min |
```

---

### Shorter is better
**Confidence:** Medium

Prefer concise documentation over comprehensive. Long docs get cancelled or skimmed. Break into smaller focused pages if needed.

**Apply when:**
- Writing new documentation
- First draft feels too long
- Covering multiple topics in one file

**Guideline:** If a doc exceeds ~150 lines, consider splitting or trimming.

---

## Workflows

### Delete + redirect
**Confidence:** High

When reorganizing documentation:
1. Delete original content (don't leave duplicates)
2. Create redirect pages at old URLs for backward compatibility
3. Use HTML meta refresh when redirects plugin isn't available

**Redirect template:**
```markdown
---
title: Redirecting...
---

<meta http-equiv="refresh" content="0; url=../new-location/">

# This page has moved

You're being redirected to [New Location](../new-location/).
```

**Apply when:**
- Renaming or moving documentation files
- Consolidating scattered content
- Reorganizing navigation structure

---

## Feature naming — two names, one binding

**Ratified with the Fix Receipts / Spec Ladders rulings
(2026-08-02; outcome-first-fix D9, spec-lifecycle-gates
decisions).**

Features are named by their **artifact** (Fix Receipts, Spec
Ladders); commands stay **verbs** (`attune fix`, `/spec`). Both
names are correct — they are different parts of speech doing
different jobs, and neither replaces the other.

**The binding rule:** in any document, the FIRST mention binds
name to command — "**Fix Receipts** (`attune fix`)" — and later
mentions use the command alone. Never alternate freely between
them; never rename a command to match a brand noun (breaks the
verb grammar and shipped CLIs); never introduce a feature name
without its command anchor.

New feature names are chair-ratified and logged in the owning
spec's decisions.md BEFORE landing (see outcome-first-fix D9 for
the worked pattern: candidates considered, artifact-over-process
principle, scope of the ruling). Skill-description edits that
carry a new name must stay under the 250-char frontmatter cap.
