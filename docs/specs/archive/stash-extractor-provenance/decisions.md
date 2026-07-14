# Stash Extractor Provenance — Decisions

## D1 — Filter at tail construction (2026-07-06)

**Decision:** `_text_of` skips `tool_result`/`tool_use` blocks,
emitting `[tool output omitted]`; consecutive markers collapse.
Deterministic, model-free, and fixes the heuristic fallback for free.

**Rejected:** filtering only in the Ollama path (leaves the
heuristic poisoned); post-extraction filtering (the model has
already seen mislabeled text — garbage in, plausible garbage out).

## D2 — Prompt provenance rules (2026-07-06)

**Decision:** the extraction prompt additionally instructs: extract
only assistant conclusions / user decisions; never restate file or
tool contents. Belt-and-suspenders on top of D1 — now truthful
because the tail really is role-faithful.

## D3 — No schema change (2026-07-06)

**Decision:** drop ambient content at extraction; no `provenance`
field on stash records. Smallest blast radius (stash schema, recall
digest, and hydration untouched). Revisit as its own evidence pass
if post-fix stashes still carry ambient findings.

**Decided by:** Patrick, via AskUserQuestion ("Go as proposed" over
the provenance-field variant), 2026-07-06.

## D4 — Eval is a deterministic unit replay (2026-07-06)

**Decision:** no live-Ollama eval. Synthetic transcript JSONL
reproducing the failure shape; assertions on the tail builder, the
heuristic, and the prompt text. The real-model behavior is bounded
by what it can no longer see.
