# attune-docs Marketplace — Tasks (Option A: retire + consolidate)

**Status:** complete — all tasks shipped 2026-06-22. T1-T3 +
attune-gui: attune-ai #988 / #989 (+ lessons #990). T4: attune-docs #6
(migration README + moved-signal). T5: attune-docs archived read-only;
attune-gui-plugin was already archived (redirect chains via attune-docs
→ attune-ai), left as-is.

D2 proposed home: `Smart-AI-Memory/attune-ai` marketplace.
D3: archive attune-docs read-only with a migration README (do not
delete).

---

## T1 — Add help/author plugins to the attune-ai marketplace

**Repo:** attune-ai (this repo). **Reversible.**

- Copy the `attune-help` and `attune-author` plugin dirs into this
  repo's marketplace layout (mirror how `attune-docs` packaged them:
  physical plugin dirs + relative-path `source`).
- Register both in `.claude-plugin/marketplace.json` alongside
  `attune-ai`.
- Pin to current versions: attune-help 0.11.1, attune-author 0.21.0
  (also bring attune-gui forward if it moves with them — TBD).
- Validate the manifest (`marketplace.json` parses; sources resolve).

## T2 — Point docs/site at the new home

**Repo:** attune-ai. **Reversible.**

- Update `website/app/docs/page.tsx` and `website/lib/features.ts`
  install commands to `…@attune-ai` (supersedes the #985 interim
  "lead with PyPI + stale-marketplace caveat" once the plugins are
  actually live in attune-ai).
- Update `website/components/Footer.tsx` attune-docs link.
- Update README references to the attune-docs marketplace.
- Refresh the `features.ts` header comment (the "2026-04-10 split"
  mapping) to reflect consolidation.

## T3 — End-to-end install verification

**Reversible.**

- `claude plugin marketplace add Smart-AI-Memory/attune-ai` then
  `claude plugin install attune-help@attune-ai` /
  `attune-author@attune-ai` — confirm they install at current versions
  and the skills/commands surface.

## T4 — Migration note on attune-docs  ⚠️ separate repo

**Repo:** Smart-AI-Memory/attune-docs. **Needs go-ahead.**

- Replace the attune-docs README with a migration note pointing to the
  attune-ai marketplace; keep the marketplace.json or a stub so an
  existing `marketplace add` resolves with a clear "moved" signal.

## T5 — Archive attune-docs  ⚠️ destructive / outward-facing

**Repo:** Smart-AI-Memory/attune-docs. **Needs explicit go-ahead.**

- After T4 lands, set the repo to **archived (read-only)**. Do NOT
  delete it — existing `marketplace add` users must still reach the
  redirect, and archive is reversible where delete is not.

---

## Sequencing

T1 → T2 → T3 (all in attune-ai, one PR) prove the new home works before
touching attune-docs. Only then T4 → T5. Each of T4/T5 is confirmed
with Patrick at execution time (separate-repo + archive are not covered
by spec ratification alone).
