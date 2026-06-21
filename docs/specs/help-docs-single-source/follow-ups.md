# Follow-ups: Single-Source Help + Docs

Tracked items deferred out of the T1 pilot. Each is a real piece of
work with enough context to act on cold.

---

## FG1 — Build the FAQ Generator (post-pilot)

**Status:** open · **Raised:** 2026-06-21 (D6/D7) · **Blocks:** FAQ
single-sourcing (not the pilot)

Build the four-channel **FAQ Generator** that decisions.md D6
describes and D7 defers past the pilot. It consumes each feature's
`## FAQ seeds` (author-curated, channel 4) and merges them with the
three dynamic channels — unmatched user queries, telemetry
error-frequency, GitHub issues — then deduplicates and ranks by
frequency to produce both the in-tool `.help/<feature>/faq.md` and
the global mkdocs FAQ page.

**Why deferred:** verified 2026-06-21 the Generator does not exist in
either repo; `.help/faq.md` is LLM-generated today. The pilot proves
the projection chain for the other 10 kinds; the Generator is a
distinct subsystem (telemetry ingestion, dedup, ranking) that would
balloon pilot scope.

**Where to look:** doc-stack spec
(`.claude/plans/documentation-stack-spec.md`) D3 (~line 659), the
architecture diagram's "FAQ Generator" transformer (~line 590), the
"Error frequency from telemetry | FAQ candidates" mapping (~line
459); this spec's decisions.md D6 + D7;
`plugin/help/generated/notes/decision-d3-faq-sourcing-four-channels.md`.

**Done when:** the Generator produces `.help/faq` + the global FAQ
page from seeds + dynamic channels, and spec-engine's `faq` entry is
removed from the LLM generator manifest (completing DD5 for the
faq kind).

---

## FM1 — Failure-modes sourcing review (before rollout)

**Status:** open · **Raised:** 2026-06-21 (D6 fallout) · **Blocks:**
R7 rollout playbook

**The question:** Is the master file's `## Failure modes` section the
same "static copy vs dynamic source-of-truth" problem we just fixed
for the FAQ (decisions.md D6)?

**Why it's suspect:** The earlier documentation-stack spec
(`.claude/plans/documentation-stack-spec.md`) routes **telemetry
error-frequency** into *both* error templates *and* FAQ candidates
(see its decision D3 and the architecture diagram's "FAQ Generator
<- Dynamic FAQ from patterns", plus the line "Error frequency from
telemetry | FAQ candidates"). If error/troubleshooting/warning
content is meant to be partly sourced from live telemetry —
"errors that appear frequently get promoted" — then the master
file's hand-authored `## Failure modes` section has the same three
regressions D6 names for the FAQ:

1. duplication (a frozen copy alongside the telemetry-sourced one),
2. discards the dynamic channel (telemetry frequency can't feed a
   static block),
3. inverts the data flow (the feature emits what should be pulled).

**What to decide:** One of —

- **(a) Failure modes is fully author-owned** (canonical, static):
  telemetry error-frequency informs *which* failure modes the author
  documents, but the rendered content is authored, not generated.
  No regression; close the item.
- **(b) Failure modes is partly sourced** (like the FAQ): the master
  file contributes author-curated seed failure-modes (channel 4),
  and an Error Generator merges them with telemetry-frequency signal,
  dedupes, and ranks. Then re-cut `## Failure modes` to seeds and
  amend design.md's projection map (mirror the D6 treatment).

**Recommended starting hypothesis:** lean toward (a). Failure-mode
*prose* (symptom / cause / fix) is genuinely author-knowledge, unlike
FAQ phrasing which tracks how real users ask. Telemetry's role is
likely *prioritization* (which failure modes matter most), not
*authoring* — which is a weaker coupling than the FAQ's. But verify
against the doc-stack spec's actual intent before committing; do not
assume.

**Where to look:**

- `.claude/plans/documentation-stack-spec.md` — Feature 1 (error
  templates, "Source of truth" section ~line 241), the architecture
  diagram (~line 575), D3 (~line 659), and the "Error frequency from
  telemetry | FAQ candidates" mapping (~line 459).
- `plugin/help/generated/notes/decision-d3-faq-sourcing-four-channels.md`
- This spec: `decisions.md` D6, `design.md` projection map + FAQ
  exception note.
- The current `## Failure modes` section in
  `content/features/spec-engine.md` (the thing under review).

**Done when:** a decision (D7) is recorded choosing (a) or (b); if
(b), `content/features/spec-engine.md`'s `## Failure modes` section is
re-cut to seeds and design.md amended to match.

---

## Starter prompt for a fresh session (FM1)

> Paste this into a new Claude Code session rooted in the attune-ai
> worktree to pick up FM1 cold.

```text
Resume the help-docs-single-source spec: do the Failure-modes
sourcing review (follow-up FM1 in
docs/specs/help-docs-single-source/follow-ups.md).

Context: In T1 we found the master file's FAQ section was a static
copy that regressed the FAQ-as-source-of-truth design (four-channel
FAQ Generator). We fixed it (decisions.md D6) by re-cutting FAQ to
author-curated channel-4 seeds. FM1 asks whether `## Failure modes`
has the same problem, because the doc-stack spec
(.claude/plans/documentation-stack-spec.md, D3 + architecture
diagram) routes telemetry error-frequency into error/FAQ templates.

Task:
1. Read follow-ups.md FM1, decisions.md D6, and design.md (FAQ
   exception note + projection map) in
   docs/specs/help-docs-single-source/.
2. Read the doc-stack spec's error-template / source-of-truth design
   (Feature 1, ~line 241; architecture ~line 575; D3 ~line 659; the
   "Error frequency from telemetry | FAQ candidates" mapping
   ~line 459). Establish the ACTUAL intended coupling between
   telemetry error-frequency and authored failure-mode content — do
   not assume; ground it in the spec text.
3. Decide (a) Failure modes is fully author-owned (telemetry only
   prioritizes which modes to document) OR (b) it is partly sourced
   like the FAQ (author seeds + Error Generator merge/dedupe/rank).
   Recommended starting hypothesis is (a) — failure-mode prose is
   author-knowledge, telemetry's role is likely prioritization not
   authoring — but verify.
4. Record the outcome as decision D7 in decisions.md. If (b), re-cut
   the `## Failure modes` section in content/features/spec-engine.md
   to seeds (mirror the D6 FAQ treatment) and amend design.md's
   projection map + add a Failure-modes exception note.

Done when: D7 recorded; if (b), spec-engine.md and design.md amended
to match. This unblocks the R7 rollout playbook.
```
