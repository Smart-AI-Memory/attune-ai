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
