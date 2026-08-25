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

One command per key in `CAPABILITIES` (`website/lib/features.ts`).
Each is the same derivation the CI guard asserts — if a command here
and the guard disagree, the guard wins and this table is the bug.

| Claim | Verification |
|-------|-------------|
| `workflows` | `python -c "from attune.workflows import discover_workflows; print(len(set(discover_workflows().values())))"` |
| `skills` | `ls -d plugin/skills/*/ \| wc -l` |
| `mcpTools` | `python -c "from attune.mcp import tool_schemas as t; print(sum(len(getattr(t, n)()) for n in dir(t) if n.startswith('get_') and n.endswith('_tools')))"` |
| `templateKinds` | `python -c "from attune.authoring.generator import _ALL_TEMPLATE_NAMES as a; print(len(a))"` |
| `wizards` | `python -c "from attune.wizards import list_wizards; print(len(list_wizards()))"` |
| Version number | `python -c "from attune import __version__; print(__version__)"` |

**`workflows` counts distinct classes, never `stages`.** D4
(claim-drift-gates, ratified 2026-07-12) chose
`len(set(discover_workflows().values()))` and explicitly *rejected*
`list_workflows()` filtered on a truthy `stages` field. Almost every
workflow sets some `stages` value, so that filter counts nearly all of
them while implying they are multi-stage — only three actually declare
more than one stage. `release-prep`/`release-gate` and
`orchestrated-health-check`/`health-check` are deliberate alias pairs
and count once each.

---

## The website-only CI gap

Website-only PRs (nothing changed outside `website/`) **skip the Python
test suite** — the `changes` job in `.github/workflows/tests.yml` emits
`website_only=true` and the full-suite jobs report green without running
pytest (see `website/CLAUDE.md`).

`tests/unit/test_website_version_accuracy.py` — the guard that owns
these counts — is therefore **not enforced on the PRs most likely to
change them**. The failure surfaces later, on whatever unrelated
full-suite PR merges next.

So on a website-only PR, running the commands above is not belt-and-
braces. It is the only check that will run. To force the guard locally:

```bash
python -m pytest tests/unit/test_website_version_accuracy.py -q
```

---

## What Went Wrong

The `/workflows` page was manually authored and listed 14 workflows,
6 of which were fictional (Debug, Explain Code, Morning Briefing,
Test Coverage Boost, Test Maintenance, Documentation Management).
None existed in the Python registry.

This was discovered only when a user noticed the discrepancy.

### 2026-07-28 — this rule caused the regression it exists to prevent

PR #1703 changed `CAPABILITIES.workflows` from 20 to 19, citing the
"stage-filtered registry" — the derivation D4 had rejected sixteen days
earlier. The number came from following the command in this table,
which was never updated when D4 landed. Because #1703 was website-only,
the guard that would have caught it never ran; `main` went red on the
next full-suite PR and stayed red until #1704.

Two failure modes stacked: a stale verification command, and a CI gap
that hid the result. Both are addressed above. The durable lesson is
that a rule doc prescribing a command is load-bearing — when a decision
changes a derivation, the doc that teaches it has to change in the same
breath, or it keeps handing out the old answer with full authority.

---

## Apply This Rule When

- Adding a new page that lists workflows, wizards, or agent features
- Updating counts in `lib/features.ts`, `lib/metadata.ts`, or
  `components/Navigation.tsx`
- Writing blog posts that reference specific workflow or wizard names
- Creating comparison pages that list Attune AI capabilities
- Writing launch copy, release announcements, or README prose that
  repeats a capability count

---

## Single Source of Truth

`website/lib/features.ts` is the canonical feature list for the
website. All pages should import from it rather than hardcoding
counts. When the Python registry changes, update `features.ts` first,
then verify all pages that consume it.
