# Requirements: Extended Cache TTL — Sibling Packages

**Status**: complete (2026-06-22) — both tasks shipped; reconciled at 2026-07-14 triage (was: approved)
**Owner**: patrick + agent

---

## Problem

`attune-rag` shipped an env-driven extended prompt-cache TTL:
`ATTUNE_RAG_CACHE_TTL=1h` flips the Anthropic `cache_control`
marker from the default 5-minute ephemeral window to a 1-hour
window at the same per-token rate
(`attune_rag/providers/claude.py:26` `_cache_control()`).

The sibling packages that also attach `cache_control` markers to
Claude requests hardcode `{"type": "ephemeral"}` and cannot opt
into the longer window. Dashboards and benchmark sweeps that issue
clusters of related queries within an hour pay repeated cache-write
cost they could avoid.

---

## Goal

Mirror the shipped `attune-rag` `_cache_control()` helper into the
sibling packages so the 1-hour window is reachable via an
environment variable, with behavior byte-identical to today when
the variable is unset.

---

## Scope

- **Task A — attune-ai** (this repo): add `_cache_control()` to
  `src/attune/llm/providers/anthropic.py` and route every
  `cache_control` emit site through it. Env var `ATTUNE_CACHE_TTL`.
- **Task B — attune-author** (separate repo, separate PR): same
  mirror in its Claude provider path. Deferred — not in this
  session.

Out of scope: changing the default window; any non-Anthropic
provider; any caller-facing API change.

---

## Acceptance criteria

1. `_cache_control()` returns `{"type": "ephemeral", "ttl": "1h"}`
   when the package env var is `1h` (case/whitespace insensitive),
   and `{"type": "ephemeral"}` for unset / `5m` / any other value.
2. Every existing `cache_control` emit site in the target provider
   routes through the helper — no remaining hardcoded marker.
3. Default behavior (env unset) is byte-identical to the prior
   wire shape; existing tests stay green.
4. Wire-shape tests lock both the default and the `1h` marker at
   every emit site, mocked — no live API.

---

## Non-goals

- A shared cross-package helper module. Each package keeps its own
  small copy with its own env var name (`ATTUNE_RAG_CACHE_TTL`,
  `ATTUNE_CACHE_TTL`), matching the existing rag precedent. The
  duplication is ~16 lines and deliberate.
