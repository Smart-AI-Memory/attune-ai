# Usage Signals — Phase 2 Design: Opt-In Phone-Home Ping

**Status:** scoped (2026-06-15) · **Owner:** Patrick + agent
**Decided in:** scoping session 2026-06-15 (D4). Closes the gap D2
named — "which workflows/skills do external users run?" — which no
zero-instrumentation source can answer.

## Premise

Phase 0 (D1–D3) proved public data answers *how many installs* but
not *what users actually run*. The opt-in ping is the only path to
that signal. This design takes it, staying inside the rails the
spec already froze (R2 privacy, R3 one dashboard surface).

## Decisions locked (D4)

- **Architecture:** a *sync layer* on top of the existing local
  `usage.jsonl`, not a parallel pipeline. Phone-home = "flush new
  local events to an endpoint, mark them sent." Reuses the
  local-first buffer, gives offline resilience free, honors the
  non-goal "don't replace local telemetry."
- **Backend:** a Vercel serverless function (`/api/usage` on the
  attune-ai.dev project) writing to **Vercel Postgres (Neon)**.
  Relational store chosen for `GROUP BY workflow` / retention /
  per-version queries. AMS Redis stays focused on memory/RAG.
- **Identity:** a **rotating anonymous install-ID** (random UUIDv4
  in config; user can reset). Unlocks retention / returning-user
  signal. Documented as anonymous and rotatable — a deliberate,
  recorded softening of the spec's original "no identification
  ever" (see Privacy note below).
- **Consent:** ships OFF; one-time first-run Socratic prompt to
  enable; `ATTUNE_USAGE_PING=0/1` and `attune telemetry
  enable/disable` overrides; `DO_NOT_TRACK` honored.
- **Transport:** fire-and-forget, async, ~2 s hard timeout, all
  errors swallowed. Never blocks, slows, or crashes the CLI.

## Frozen payload (schema v1)

One auditable source file owns this struct. `attune telemetry
status` prints exactly this. Adding a field requires bumping
`schema` and updating the freeze test.

```json
{
  "schema": 1,
  "package": "attune-ai",
  "version": "8.5.0",
  "install_id": "<rotating uuid4>",
  "event": "workflow.security_audit",
  "os": "darwin",
  "py": "3.12",
  "ts": "2026-06-15T12:00:00Z"
}
```

- `event` is `workflow.<name>` — the name comes from the local
  `usage.jsonl` record's `workflow` field (registry-sourced), never
  free-text. (`skill.<name>` / `command.<name>` are reserved for a
  later schema once those surfaces emit local records.)
- **`outcome` is NOT in v1.** The shipped v1 payload (Phase 2a) maps
  only what the local emit path actually records — workflow name +
  timestamp. The local `UsageTracker` records LLM-call cost/token
  data, not a success/error outcome, so emitting `outcome` would mean
  fabricating it. Capturing a real outcome requires instrumenting the
  workflow-execution path and is deferred to a `schema: 2` bump (the
  freeze test guards against silent addition). The Postgres `outcome`
  column below is reserved/nullable for that future bump.
- **NEVER carried:** paths, code, prompts, args, filenames, env
  vars, project names, cost/token/model data, any free-text. Enforced
  by `PAYLOAD_KEYS` + `FORBIDDEN_RECORD_FIELDS` and a regression test.

## Postgres schema

```sql
create table usage_events (
  id          bigserial primary key,
  received_at timestamptz not null default now(),
  package     text not null,
  version     text not null,
  install_id  uuid not null,
  event       text not null,
  outcome     text,          -- reserved for schema:2 (see payload note)
  os          text,
  py          text,
  client_ts   timestamptz
);
create index on usage_events (package, event);
create index on usage_events (install_id);
create index on usage_events (received_at);
```

- The function stores **no IP and no headers** — drop them before
  insert. Retention: raw events 90 days, then roll up to daily
  aggregates (deferred until volume warrants).

## Client flow (Phase 2a)

1. **Consent gate.** On first interactive run, Socratic prompt:
   *"Help improve attune-ai? Share anonymous usage (version, which
   workflows you run, your OS — never code, paths, or prompts).
   [Yes / No / Show me exactly what's sent]."* Persist
   `usage_ping.enabled` + a freshly minted `usage_ping.install_id`
   to config. Env / `DO_NOT_TRACK` short-circuit the prompt.
2. **Emit.** `UsageTracker` already writes each event locally —
   unchanged.
3. **Sync.** A flush (atexit / Stop hook) reads local events past a
   cursor, maps each to the frozen payload, batches one POST, and
   advances the cursor on `204`. Timeout 2 s; any failure leaves the
   cursor unmoved (retry next run) and is silently dropped from the
   user's view.

## Endpoint (Phase 2b)

- `POST /api/usage`, public + unauthenticated (a CLI can't hold a
  secret). Validates against schema v1, **rejects unknown fields**
  (defense against future free-text creep), size-caps the body,
  rate-limits per IP, drops IP/headers, inserts, returns `204`.
- **Known limitation:** an unauthenticated public endpoint is
  spoofable — anyone can POST fake events. Stakes are low (usage
  counts, not money/auth). Mitigation is rate-limit + strict schema
  validation; the data is best-effort, not adversarially trusted.
  Documented, not engineered away.

## Dashboard (Phase 2c — this is R3)

The existing ops dashboard gains a "Reach" panel reading
`usage_events`: events/workflow, returning-install retention curve,
per-version adoption, opt-in rate. Sits beside the public-signal
snapshot (D3) and the watchdog/spend panels (R5/R6).

## Privacy note (amends R2)

R2 said "no per-user identification, ever." Phase 2 adopts a
**rotating anonymous install-ID** — coarse, anonymous, user-resettable,
carrying no PII and no linkage to identity. This is a recorded,
deliberate softening to unlock retention, the highest-value product
signal. Mitigations keeping it trustworthy: default-OFF, explicit
consent, frozen auditable payload, `status` command, one-command
opt-out, deletion-by-install-id on request, documented in README +
SECURITY.md.

## Concerns / work breakdown

| Concern | Work |
|---|---|
| `impl` 2a | consent + config + frozen payload + fire-and-forget sync client + `attune telemetry status/enable/disable` |
| `impl` 2b | Vercel `/api/usage` function + Neon schema + validation/rate-limit |
| `impl` 2c | dashboard Reach panel (R3) |
| `test` | freeze-test asserting payload keys exactly (regression-guard against scope creep); sync cursor/offline/timeout paths; consent-default-OFF test |
| `docs` | README opt-in section + SECURITY.md privacy/payload disclosure + frozen-payload reference |
| `release-notes` | CHANGELOG: user-facing trust change; announce default-OFF + how to opt in |

Additive — no `migration`.

## Risks

| Severity | Risk | Mitigation |
|---|---|---|
| high | Silent exfiltration would torch trust | default-OFF + explicit consent + auditable payload + `status` |
| medium | Payload scope-creep over releases | frozen schema-version int + exact-keys regression test |
| medium | Blocking/crashing the CLI | fire-and-forget + 2 s timeout + swallow all errors |
| low | Spoofable public endpoint | rate-limit + schema validation; data treated as best-effort |
| low | GDPR/PII exposure | anonymous + opt-in + no PII + deletable + documented |

## Rough effort

~3 focused days: 2a ~1 d, 2b ~0.5 d, 2c ~0.5–1 d, docs/tests ~0.5 d.
Each ships as its own PR; 2a is usable (default-OFF, endpoint
stubbed) before 2b lands.

## Done when (Phase 2)

- Opt-in ping ships default-OFF with auditable frozen payload and a
  passing freeze regression test.
- `/api/usage` ingests to Neon; the dashboard Reach panel shows
  events-by-workflow and a retention curve from real opt-in data.
- README + SECURITY.md disclose the payload and opt-in/opt-out.
- One release later, you can answer "which workflows do external
  users actually run?" with evidence — the question D2 left open.
