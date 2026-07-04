---
paths:
  - "website/**"
  - "content/**"
  - "attune-ai-dev/**"
---

# Website Content Accuracy Rule

**Created:** 2026-02-27
**Source:** Session — workflow count divergence (14 fictional vs 10 real)

---

## Rule

Before publishing or updating any website page that lists features,
counts, or capabilities, **verify the claim against the live Python
code**.

---

## Required Verification Commands

| Claim | Verification |
|-------|-------------|
| Workflow count / names | `python -c "from attune.workflows import list_workflows; [print(w['name']) for w in list_workflows() if w.get('stages')]"` |
| Wizard count / names | `python -c "from attune.wizards import WizardRegistry; r = WizardRegistry(); print(r.list_wizards())"` |
| Agent templates | Check `src/attune/agents/` for registered templates |
| Version number | `python -c "from attune import __version__; print(__version__)"` |

---

## What Went Wrong

The `/workflows` page was manually authored and listed 14 workflows,
6 of which were fictional (Debug, Explain Code, Morning Briefing,
Test Coverage Boost, Test Maintenance, Documentation Management).
None existed in the Python registry.

This was discovered only when a user noticed the discrepancy.

---

## Apply This Rule When

- Adding a new page that lists workflows, wizards, or agent features
- Updating counts in `lib/features.ts`, `lib/metadata.ts`, or
  `components/Navigation.tsx`
- Writing blog posts that reference specific workflow or wizard names
- Creating comparison pages that list Attune AI capabilities

---

## Single Source of Truth

`website/lib/features.ts` is the canonical feature list for the
website. All pages should import from it rather than hardcoding
counts. When the Python registry changes, update `features.ts` first,
then verify all pages that consume it.
