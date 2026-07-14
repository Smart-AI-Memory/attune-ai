# Redis & Anthropic Best-Practice Alignment

> What attune-ai can **verifiably** claim about following Redis's and
> Anthropic's recommended patterns for agent memory — and the small
> gaps to close before that claim goes into external copy.

**Created:** 2026-06-08 (overnight autonomous pass)
**Owner:** Patrick + agent
**Status:** findings for morning review — claims verified against
current vendor sources; wording flagged where it should be softened.

---

## TL;DR

attune-ai is already well-aligned with both vendors' reference
architectures. The strongest claim — *"built on Redis's official
Agent Memory Server (RedisVL) and integrated through Anthropic's
Claude Agent SDK + MCP + Skills"* — is **true today**. One concrete
bridge (implement Anthropic's Memory tool backend over the AMS
backend) makes the Anthropic half demonstrable rather than
analogous. The "contribute back" upstream PR (RedisVL datatype
settings) is the highest-integrity alignment move and is still
needed (upstream hasn't shipped it as of v0.15.2).

---

## Redis alignment — verified

| Claim | Evidence | Status |
|---|---|---|
| Built **on** Redis's official Agent Memory Server (not a hand-rolled Redis integration) | `attune_redis.AMSMemoryBackend` is a thin client over `redis/agent-memory-server`; controls no schema/index config | ✅ true |
| Uses **RedisVL** for vector search the way Redis recommends | All vector-index decisions live server-side in AMS + RedisVL; attune sets none | ✅ true |
| Uses the documented **extension seam**, not a fork | int8 quantization ships via the `MEMORY_VECTOR_DB_FACTORY` plug-in point (a documented pluggable factory), not a patched fork | ✅ true |
| Rides Redis's **vector-quantization** investment | int8 embedding quantization shipped in attune v7.4.0 (a Redis 8 / RedisVL capability) | ✅ true |
| **Contributes back** upstream | Planned PR to make `_build_redis_schema`'s datatype settings-driven so the consumer-side override can retire | 🔜 planned — still needed (upstream hasn't shipped it as of v0.15.2) |

**Source notes (2026-06-08):**

- Redis positions Agent Memory Server as the dual-tier
  (working + long-term) memory stack, with RedisVL as the
  recommended Python abstraction for storing memories as vector
  embeddings.
- Redis publishes vector benchmarks reporting higher throughput at
  recall ≥ 0.98 than other vector DBs in their tests.
- A 2025 Stack Overflow survey reported Redis as the most-used tool
  for AI-agent memory (~43% of developers).
- agent-memory-server latest release is **v0.15.2** (2026-04-10);
  attune pins **0.14.0**. The vector datatype is not yet
  settings-driven upstream, so the int8 factory override remains
  load-bearing.

**Wording to soften before external copy:**

- Don't claim "fastest vector DB" — cite Redis's own benchmark
  framing ("higher throughput at recall ≥ 0.98 in Redis's published
  tests"), attributed, not as our independent result.
- Don't imply attune contributes to RedisVL core — our contribution
  target is `agent-memory-server` (the datatype-settings PR), which
  is the accurate, verifiable statement.

---

## Anthropic alignment — verified, with one bridge to add

| Claim | Evidence | Status |
|---|---|---|
| Built on the **Claude Agent SDK** (native) | Workflows are SDK-native; `claude-agent-sdk` is a core dependency | ✅ true |
| Exposes capabilities through an **MCP server** | `attune.mcp.server` ships the MCP tool surface | ✅ true |
| Uses **Skills** for progressive disclosure | The plugin ships Skills (`/coach`, `/recall`, workflow skills, …) | ✅ true |
| Cross-session memory follows Anthropic's **"give agents memory"** direction | SessionStart recall + Stop-hook stash + searchable long-term findings | ✅ true (pattern-level) |
| attune's memory is a **drop-in backend for Anthropic's Memory tool** (`memory_20250818`) | — | 🔜 **bridge to build** (see spec) |

**The one gap worth closing.** Anthropic's **Memory tool**
(`memory_20250818`) is a *client-side* tool: Claude issues
`view`/`create`/`str_replace`/`insert`/`delete`/`rename` commands
against a `/memories` directory, and *you* implement the storage
backend (subclass `BetaAbstractMemoryTool`). attune already has a
durable, Redis-backed memory store (`AMSMemoryBackend`). Wiring
that store behind Anthropic's Memory tool interface turns an
*analogous* claim ("we do memory the way Anthropic suggests") into
a *demonstrable* one ("our memory layer is a drop-in backend for
Anthropic's Memory tool, persisted on Redis's Agent Memory
Server"). Spec: [`anthropic-memory-tool-backend`](../specs/archive/anthropic-memory-tool-backend/requirements.md).

---

## How this resolves the dormant-coordination question

The best-practice lens settles what to do with the old in-tree
Redis coordination mixins better than "user demand" did:

- **Coordination mixins** (conflict-negotiation, signals, shared
  sessions) → **retire.** Anthropic now ships native multi-agent
  coordination — **subagents** (Agent SDK / Claude Code) and the
  **Managed Agents `multiagent` coordinator** (threads +
  cross-thread messaging). Reviving custom Redis pub/sub
  coordination primitives would reimplement a vendor-native
  capability — the opposite of "align with best practice."
- **PatternStaging** (stage → review → promote/reject) → **capture.**
  No vendor-native equivalent; it's an attune-domain workflow.
  Spec: [`pattern-review-queue`](../specs/archive/pattern-review-queue/requirements.md).
- **AMS/Redis memory path** → **invest.** Strongest alignment, most
  claimable; add the Memory-tool bridge.

See [`redis-facade-direction/decisions.md`](../specs/archive/redis-facade-direction/decisions.md)
for the proposed direction (relabel-not-remove; retire mixins;
keep PatternStaging) — a proposal to ratify, not yet executed.

---

## Follow-ups surfaced

1. **Bump `agent-memory-server` 0.14.0 → 0.15.2** and re-verify the
   int8 factory override + the working-memory behaviors (PR #667/#668
   findings) against the newer release. Separate, scoped change.
2. **Ship the RedisVL datatype contribute-back PR** to
   `agent-memory-server` — the highest-integrity alignment move.
3. **Build the Anthropic Memory-tool backend bridge** (the one item
   that makes the claim true on both vendor sides at once).

---

## Sources

- [Redis — A developer's guide to agent memory (whitepaper)](https://redis.io/resources/redis-whitepaper-ai-agent-memory.pdf)
- [Redis — AI Agent Architecture: Build Systems That Work in 2026](https://redis.io/blog/ai-agent-architecture/)
- [Redis — Build smarter AI agents: short- and long-term memory with Redis](https://redis.io/blog/build-smarter-ai-agents-manage-short-term-and-long-term-memory-with-redis/)
- [Redis Agent Memory docs](https://redis.io/docs/latest/develop/ai/context-engine/agent-memory/)
- [redis/agent-memory-server (GitHub)](https://github.com/redis/agent-memory-server)
- Anthropic Memory tool (`memory_20250818`) — `claude-api` skill reference (Anthropic SDK docs)
