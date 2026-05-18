# Help IA audit — code-quality feature

**Status:** approved (no files changed yet)
**Date:** 2026-05-14
**Scope:** `.help/templates/code-quality/` only

## Existing kinds

11 templates exist in [.help/templates/code-quality/](.help/templates/code-quality):

| Kind | File | Lines | Generated |
|---|---|---|---|
| concept | [concept.md](.help/templates/code-quality/concept.md) | 40 | 2026-05-04 |
| task | [task.md](.help/templates/code-quality/task.md) | 66 | 2026-05-04 |
| reference | [reference.md](.help/templates/code-quality/reference.md) | 42 | 2026-05-04 |
| quickstart | [quickstart.md](.help/templates/code-quality/quickstart.md) | 63 | 2026-04-19 |
| troubleshooting | [troubleshooting.md](.help/templates/code-quality/troubleshooting.md) | 73 | 2026-04-19 |
| faq | [faq.md](.help/templates/code-quality/faq.md) | 48 | 2026-04-19 |
| comparison | [comparison.md](.help/templates/code-quality/comparison.md) | 64 | 2026-04-19 |
| error | [error.md](.help/templates/code-quality/error.md) | 48 | 2026-04-19 |
| note | [note.md](.help/templates/code-quality/note.md) | 34 | 2026-04-19 |
| tip | [tip.md](.help/templates/code-quality/tip.md) | 16 | 2026-04-19 |
| warning | [warning.md](.help/templates/code-quality/warning.md) | 40 | 2026-04-19 |

This matches the 11-kind canonical set from attune-author. No kinds are missing in the strict "the 11 are all present" sense.

## Kinds genuinely missing (real user gaps)

Two real gaps, neither is a "new kind" but rather **content slots** within existing kinds that don't exist anywhere in the feature today:

1. **Output-interpretation guide.** None of the 11 templates explain how to *read* a returned report. quickstart.md shows a sample report (line 27–51) but doesn't decode it. The faq.md "What do the health scores mean?" answer is one line. A user looking at "Health Score: 78/100 ⚠ Broad exception handling masks errors" has no in-help path to "what should I do next, in what order, and which findings are safe to defer." This belongs in either an expanded **task** ("Triage a code-quality report") or a second task file. **Justification:** the feature's value is the report; the help corpus barely indexes how to act on it.

   **Surface (per Patrick's annotation: "expand documentation on this in help and mkDocs"):** write the canonical content in `.help/templates/code-quality/` so the RAG corpus indexes it, then surface it on the public docs site by either (a) adding a nav entry under `docs/code-quality/triage.md` that mirrors the help template, or (b) letting the existing `attune-author` mkdocs pipeline pick up the new template if that integration is already wired. I'll confirm which during execution and pick the lighter path; no second authoring of content.

2. **Scope/depth selection.** faq.md mentions quick/standard/deep depths in a single answer (line 24–26) and tip.md repeats one tradeoff. quickstart.md doesn't show the depth knob at all and reference.md doesn't document it as a parameter. A user choosing between "review one file" and "review whole repo" has no decision page. **Justification:** scope is the #1 lever for cost/time and is currently underdocumented across exactly the kinds (reference, task, quickstart) where it should live.

   **Suggested addresses (per Patrick's "open to suggestions"):** three options, cheapest first.
   - **Option A — extend reference.md (lowest cost).** Add a "Parameters" subsection that documents `path`, `depth`, and `focus` with valid values, defaults, and a 1-line tradeoff per depth. Keeps everything in one file the user already lands on. ~15 lines.
   - **Option B — promote tip.md into a decision matrix (medium cost).** Replace the single tip with a small table: rows = depth, columns = "best for / catches / typical time / when to skip." The tip kind is the right shape for "pick one of these on purpose." ~25 lines, displaces 0 content.
   - **Option C — fold it into the new triage task (zero-extra-file cost).** Add a "Pick your scope first" step at the top of the new triage task. Works because triaging a report and choosing scope are the same decision viewed from opposite ends. ~10 extra lines inside the file we're already writing.
   - **Recommendation: do C now**, since we're writing the triage task anyway and the depth choice is genuinely upstream of "how do I read the report I got." Defer A and B to the follow-up sweep — they become cheaper once C exists to link to.

I am explicitly **not** proposing new kinds (e.g. tutorial, runbook). The 11-kind set is the right shape; the gaps are content gaps inside existing kinds.

## One IA issue per existing kind

| Kind | Issue (one) |
|---|---|
| concept | Leads with implementation ("four subagents that run in parallel") before the user value. Should lead with "what you get" not "what's inside." |
| task | Task is "Extend the workflow" — internals audience, not user audience. There's no task for "review my code" (the actual user task). |
| reference | Only documents the orchestrator class. `_SUBAGENT_NAMES` is listed but each subagent's actual contract is not. Missing: depth parameter, focus parameter, return shape. |
| quickstart | Sample output (line 27–51) is shown but never cross-linked to the troubleshooting/faq pages that decode it. Dead-ends. |
| troubleshooting | Symptom table conflates user errors (path issues) with internal failures (subagent unavailable). A user can't tell which row applies to them. |
| faq | Mixes audience tiers: "What is code quality review?" sits next to "Where can I learn more?" — orientation and exit-link Q&As should bookend, not interleave. |
| comparison | Compares against external tools but not against attune's adjacent features (`/security-audit`, `/deep-review`, `/bug-predict`). That's the comparison users actually need to disambiguate inside the product. |
| error | Lists error signatures but does not link any of them to the matching row in troubleshooting.md. Two pages, zero cross-refs. |
| note | Duplicates the concept.md "four subagents" framing nearly verbatim (concept lines 11–17 vs note lines 9–16). Pick one home. |
| tip | Single tip ("start with a quick scan") is good but isolated — should link to the depth-selection content that doesn't exist yet (see gap #2). |
| warning | Two warnings, both about output size / score-averaging. Missing the warning that actually bites: subscription cost / budget when running depth=standard on whole repo. |

## First attainable goal — pick ONE

**Add an audience-correct task: "Triage a code-quality report."** (Approved by Patrick 2026-05-14.)

Why this one over the others:

- It closes gap #1 (output interpretation) directly.
- It rehomes [task.md](.help/templates/code-quality/task.md) — currently the only task is "Extend the workflow," which is the wrong audience for the only user-facing task slot. Either replace task.md or add a second task file under the same kind (attune-author supports either).
- It is the one change that improves the RAG retrieval signal *and* the human readability of the report at the same time. Every other IA fix (cross-links, lead reordering, comparison expansion) is downstream of having a real user-facing task page to link to.
- It is roughly one file, ~80 lines, copy-able from the sample output that already exists in quickstart.md.

**Scope adjustment from Patrick's annotations:**

- Include a short "Pick your scope first" step at the top of the new task (Option C from gap #2 above). Folds depth selection into the same file at marginal cost.
- After writing the help template, verify it surfaces on the mkdocs site — wire a nav entry or confirm the attune-author pipeline picks it up. One concrete check, not a separate docs-authoring pass.

**Out of scope for this first goal:** the comparison expansion, the cross-link sweep, the warning rewrite, the standalone depth-selection rewrite (Options A and B above). Each of those is a follow-up — none of them block this one and this one informs how they should be shaped.

## Execution plan for the approved goal

1. Decide replace-vs-add for task.md. Default: **replace**. The "Extend the workflow" content has internals audience and low search value; it can move to a `developer/` subtree later if needed.
2. Write the new task with this skeleton (max ~100 lines):
   - **Pick your scope** — 1 short paragraph + tiny table (file / module / repo → depth).
   - **Read the summary score** — what 90/75/50/0 thresholds actually mean for next action.
   - **Triage by section** — Security > Quality > Performance > Architecture, with "fix now / fix this PR / defer / probably ignore" guidance per finding shape.
   - **What to do next** — link forward to fix-test, refactor-plan, security-audit when findings cross feature boundaries.
3. Update the new task's frontmatter (`type: task`, `feature: code-quality`) and let attune-author regenerate `source_hash`.
4. Add an mkdocs nav entry (or verify auto-pickup); confirm `mkdocs build` is clean.
5. Spot-check RAG retrieval: query "how do I read a code-quality report" against the local help corpus and confirm the new task ranks in top-3.

## Not doing

- Not regenerating any templates.
- Not editing features.yaml.
- Not rewriting the feature's help wholesale (per brief).
- Not proposing new kinds.
- Not proposing changes outside `.help/templates/code-quality/`.
