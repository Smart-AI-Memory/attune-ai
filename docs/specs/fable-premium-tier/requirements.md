# Spec: Fable Premium Tier (attune-ai)

> Companion spec to the attune workspace spec
> [`specs/fable-model-tiers/`](https://github.com/Smart-AI-Memory/attune)
> (approved 2026-07-09), which moved the attune-rag / attune-author
> premium tier to `claude-fable-5`. This spec covers the same decision
> for the attune-ai plugin, which already has a cheap/capable/premium
> tier system of its own.

---

## Phase 1: Requirements

**Status**: draft

### Problem statement

The attune-ai plugin routes work through three model tiers
(`ModelTier` in `src/attune/config/agent_config.py`):
cheap → `claude-haiku-4-5`, capable → `claude-sonnet-5`,
premium → `claude-opus-4-8`. The workspace-wide decision
(specs/fable-model-tiers, attune repo) is that "premium" now means
`claude-fable-5` with a server-side fallback to `claude-opus-4-8` —
attune-rag and attune-author have adopted it. The plugin's premium
tier is now inconsistent with the rest of the product: users paying
for "highest quality" agent runs get opus-4-8 while the docs
platform's premium paths get fable-5.

Fable-5 brings constraints opus never had: it requires ≥30-day org
data retention, rejects explicit `thinking`/sampling params, can end
with `stop_reason: "refusal"`, and its server-side fallback opt-in
(`betas: ["server-side-fallback-2026-06-01"]` + `fallbacks` in
`extra_body`) is **beta-namespace only and rejected by the Batch
API** — which the plugin's bulk skill is built on.

### Scope

**In scope:**
- Premium tier default `claude-opus-4-8` → `claude-fable-5` across the
  plugin's tier surfaces:
  - `src/attune/config/agent_config.py` — `ModelTier` mapping (~:153)
  - `src/attune/config/sections/routing.py` — `premium_model` default (:37, :71)
  - `src/attune/agent_factory/base.py` — tier→model map (~:305)
  - `src/attune/config/xml_config.py` — `"very_complex"` complexity route (~:61)
  - agent template defaults (`template_defs_basic.py` and friends)
- Fable request handling at the plugin's LLM chokepoint(s): beta
  namespace + `betas`/`extra_body.fallbacks`, refusal → typed error,
  30-day-retention hint on 400 (mirror the pattern shipped in
  `attune_rag.model_tiers` / `attune_author.model_tiers`).
- **Batch API refusal story for the bulk skill** (see decision table —
  this is the question this spec exists to answer).
- Env override parity: respect `ATTUNE_MODEL_PREMIUM` (same var the
  platform packages use) or document why the plugin's own routing
  config is the only override surface.

**Out of scope:**
- attune-rag / attune-author changes (shipped under the workspace spec).
- Cheap/capable tier changes (already haiku-4-5 / sonnet-5 — aligned).
- Fine-grained per-agent model pinning beyond the existing tier system.

### User stories

1. As a plugin user, I want premium-tier agents to use the best
   available model (fable-5) so that "premium" means the same thing
   across the whole attune product.
2. As a bulk-skill user, I want batch premium jobs to complete
   predictably (no silent per-item refusal losses) even though the
   Batch API cannot do server-side fallback.
3. As a cost-conscious user, I want my existing routing config
   (`premium_model` override) to keep winning over any new default.
4. As an org admin with <30-day retention, I want a clear, actionable
   error (not an opaque 400) when premium calls can't use fable.

### Affected components

- [ ] Skills (`plugin/skills/`) — bulk skill docs/behavior
- [ ] Agents (`plugin/agents/`) — premium-tier agent defaults
- [x] Plugin config (`plugin.json`) — version bump on release
- [ ] Help templates (`plugin/help/generated/`) — tier docs regeneration
- [x] PyPI package (`pyproject.toml`, release pipeline)
- [ ] Personal command (`~/.claude/commands/`) — N/A

Cross-repo dependency: pattern (not code) reuse from
`attune_rag.model_tiers` — the plugin does not depend on attune-rag,
so it mirrors the fable-handling contract the way attune-author does,
with the same `extra_body.fallbacks` deviation (no shipped anthropic
SDK types `fallbacks` as a named param — verified through 0.96).

### Invocation & triggers

No new invocation surface. Existing tier selection paths
(`model_tier` in agent configs, complexity routing, bulk skill) pick
up the new default transparently.

### Tool scope

N/A — no new skill/agent; changes are in the Python package the MCP
server runs.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Above |
| **Skill/agent contracts** | addressed | No SKILL.md interface changes; bulk skill docs must state the batch premium policy |
| **User interaction** | addressed | Transparent default change; refusal surfaces as a typed, per-item error in workflow output |
| **Edge cases** | addressed | See table below — retention 400, refusal, batch, thinking params |
| **Plugin compatibility** | addressed | `premium_model` config overrides keep winning; rollback = config pin, no reinstall |
| **Error handling** | addressed | `ModelRefusalError`-equivalent typed error; retention hint on fable 400s |
| **Tradeoffs & alternatives** | addressed | Batch decision table below |
| **Rollback strategy** | addressed | Config pin (`premium_model: claude-opus-4-8`) is a no-deploy rollback; PyPI version pin is the hard rollback |

### The Batch API refusal question (decision required)

The bulk skill submits premium work through the Anthropic **Batch
API**, where the `fallbacks` param is **rejected** — there is no
server-side fable→opus fallback for batch jobs. A fable batch item
that refuses is simply a lost item unless we handle it. Options:

| Option | Pros | Cons | Recommended? |
|--------|------|------|--------------|
| **A. Batch premium stays opus-4-8** (interactive premium moves to fable) | Zero new failure modes; keeps 50% batch discount economics predictable; matches attune-author's shipped `_batch_polish_model()` precedent | "Premium" means different models in batch vs interactive (documented) | ✅ recommended for v1 |
| B. Batch uses fable + client-side re-queue: refused items resubmitted in a second batch pinned to opus-4-8 | True fable quality where it succeeds | Doubles worst-case latency; re-queue machinery + state tracking; refusal rate unknown (no telemetry yet) | Phase 2 candidate, after telemetry |
| C. Batch uses fable, refusals reported as errored items only | Simplest fable-everywhere story | Silently degrades bulk results; violates the workspace spec's "errored, never skipped" principle only barely — items error out with no recovery | ❌ |

**Recommendation:** Option A now (mirrors attune-author's batch
policy, shipped 2026-07-09), with a follow-up item to collect refusal
telemetry from interactive premium calls and revisit Option B once a
real refusal rate is known.

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Org has <30-day retention → fable 400s | Append retention hint to the 400 (mirror platform packages); document config pin `premium_model: claude-sonnet-5` as the workaround |
| `stop_reason: "refusal"` after full fallback chain | Typed error surfaced per-item in workflow output; never a silent skip |
| Explicit `thinking`/sampling params on a premium call | Fable rejects them — strip/downgrade with a logged warning (attune-rag judge precedent) or raise; decide in design |
| Batch API rejects `fallbacks` | Decision table above — Option A recommended |
| User's routing config already pins `premium_model` | Explicit config always wins; no behavior change |
| Anthropic SDK floor | `fallbacks` must ride in `extra_body` (not typed through SDK 0.96); no floor bump needed |
| `ATTUNE_MODEL_PREMIUM` env var vs plugin routing config | Open: adopt the env var for parity, or keep routing config authoritative? Leans config-authoritative with env as fallback — decide in design |

### Gaps (if any)

- Refusal-rate telemetry does not exist yet; Option B (re-queue)
  cannot be costed until it does.
- `plugin/help/generated/` tier documentation regeneration is assumed
  cheap but unverified.
- Status is **draft** — needs Patrick's approval on the Batch
  decision (Option A) before Phase 2.

---

## Cross-references

- Workspace spec: `specs/fable-model-tiers/` in the attune repo
  (requirements, design, tasks — approved 2026-07-09).
- Shipped platform implementations:
  - attune-rag PR #188 (`attune_rag/model_tiers.py`, provider/judge wiring)
  - attune-author PR #87 (mirror module + drift test, polish/doc-gen
    wiring, `_batch_polish_model()` batch policy, rag-gate CI pin)
