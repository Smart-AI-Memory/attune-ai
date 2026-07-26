# memory-claim-verification — decisions

## D1 (2026-07-26): the extraction prompt is NOT the control

**Ruled.** The prompt already carries a PROVENANCE rule instructing the
model to record only what the session concluded. Both bad findings on
2026-07-25 violated it anyway.

Tightening the prompt, or making `/recall review` mandatory, were both
considered and REJECTED as patches:

- Prompt-tightening leaves an 8B model writing unverified assertions,
  just fewer of them. The failing component cannot be its own control.
- Mandatory review adds friction to every session to catch a minority of
  bad records — and `/recall review` already exists and is not run, which
  is the empirical answer to whether more optional review works.

Verification must live **outside** the model, in code that resolves
entities against ground truth.

## D2 (2026-07-26): apply the claim-drift architecture, don't invent one

**Ruled.** The claim-drift gate and the capability projector both refuse
to trust a written value and derive it from a live source. Both caught
real drift on 2026-07-25. The memory store is the last surface in the
repo still trusting written prose about mutable state.

This spec is therefore **not a new technique** — it is the existing
derive-don't-store discipline applied to `session_stash`. Design reviews
should check consistency with those two mechanisms before adding
machinery.

## D3 (2026-07-26): read-time annotation ships first and alone

**Ruled.** P1 (refs + read-time re-resolution) is independently
shippable, carries no write-path risk, requires no model change, and
catches the motivating failure. Seeing `⟨pr:1666 → MERGED⟩` beside "open
for reviewing" defeats the bad finding **without any natural-language
understanding**.

Write-time rejection (P2) is strictly more invasive and depends on OQ1.
Do not bundle them.

## D4 (2026-07-26): unreachable is never contradicted

**Ruled.** A resolver that cannot reach `gh`, git, or the filesystem must
store the finding ungrounded, never reject it. The memory layer degrades
silently and never blocks a session — this is existing contract, restated
here because a verification step is exactly where it would be broken.

## D5 (2026-07-26): the golden set pins BOTH directions

**Ruled.** The acceptance test replays all four real 2026-07-25 findings
and requires the two bad ones to be caught **and the two good ones to
survive**. A change that rejects everything is as wrong as one that
accepts everything.

Same discipline as `tests/unit/ci/test_platform_compat_scanner.py`, where
each false-positive class is pinned to its true positive so a later
re-broadening fails loudly instead of silently refilling the store.

---

## Open, for the chair

- **OQ1** — does `llama3.1:8b` reliably emit `refs`? Measure before
  building P2; if not, heuristic back-fill from `content` becomes the
  permanent mechanism and R3 may not be viable.
- **OQ2** — on contradiction, reject or demote? Proposal: demote to
  `interpretation` with the contradiction recorded.
- **OQ3** — should a grounded finding outlive the 30-day TTL? Changes the
  store's character from working-memory to durable.
