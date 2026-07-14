# Decisions — Ops mutating-endpoint auth (per-process token gate)
**Status:** done (2026-06-05) — implemented, live-smoke verified; reconciled at 2026-07-14 triage (was: approved)
**Owner:** Patrick
**Context:** [`docs/specs/ops-specs-features/phase4-findings.md`](../ops-specs-features/phase4-findings.md) (Finding 0)

---

## Problem

`attune ops`' mutating endpoints (`PUT /api/specs/{slug}/{phase}/status`, `POST /api/specs/{slug}/completion-candidates/dismiss`, `POST /workflows/{name}/run`, and any future ones) are gated only by `config.allow_run` (the `--read-only` flag). Once `--allow-run` is on (the default), **any client that can reach the loopback bind can issue mutations**. Browsing the dashboard with an a11y-traversing tool flipped status on multiple specs without explicit user action — see Finding 0.

[PR #446](https://github.com/Smart-AI-Memory/attune-ai/pull/446) addressed the specific JS trigger (commit-on-blur → cancel-on-blur). That eliminates the observed trigger but doesn't reduce the **blast radius** of any future trigger: a misconfigured client, a Chrome extension, a stray `curl`, a different a11y interaction.

`attune-gui` solves this with a **per-process session token**: a `secrets.token_urlsafe(32)` minted at startup, exposed via `GET /api/session/token`, required as the `X-Attune-Client` header on every mutating route. The page JS reads it once at load and echoes it. The contract: any client that didn't first see the page (e.g., raw `curl`, automation that didn't bootstrap from `/api/session/token`) cannot mutate.

Port that pattern to `attune ops`. Defense in depth: the page's UX flow is unchanged; the bug class of "accidental mutation from non-page client" is eliminated.

## Decision

Mirror attune-gui's `security.py` module verbatim:

- `_SESSION_TOKEN = secrets.token_urlsafe(32)` generated once at process start
- `current_session_token()` returns the in-process token
- `require_client_token` is a FastAPI `Depends(...)` that 403s on missing/mismatched `X-Attune-Client`
- New route `GET /api/session/token` returns `{"token": "..."}` — read-only, no auth (it's the way pages bootstrap)

Apply `Depends(require_client_token)` to **every existing mutating endpoint**:

| Endpoint | File | Method |
|---|---|---|
| `PUT  /api/specs/{slug}/{phase}/status` | `routes/specs.py` | rewrite phase-file status |
| `POST /api/specs/{slug}/completion-candidates/dismiss` | `routes/specs.py` | dismiss-store write |
| `POST /workflows/{name}/run` | `routes/runner.py` | start workflow run |
| `POST /runs/{run_id}/cancel` (if exists) | `routes/runs_history_routes.py` | cancel run |

(Inventory to be finalized in Phase 1 task 1.1 by `grep -rn '@router\.(put\|post\|delete\|patch)' src/attune/ops/routes/`.)

## What's NOT in scope (firm)

- Multi-user auth / OAuth / OIDC — the dashboard is single-user localhost.
- Encryption at rest of the token — in-memory only, dies with the process.
- Long-lived tokens / refresh tokens — new server = new token; pages reload.
- Server-side CSRF state — the token IS the CSRF defense.
- Cookie-based auth — explicit header keeps the surface minimal and curl-debuggable.
- Tightening `--read-only` defaults to read-only — separate UX/CLI decision.

## Alternatives considered

1. **Origin-header check only**: cheap, but the preview MCP tool's requests ARE from a browser context with a same-origin Origin header. Doesn't block the observed trigger class.
2. **`X-Requested-With: XMLHttpRequest` header**: even cheaper, blocks naive `curl`/scripts. Doesn't block tools that mimic a browser's header set. Lower barrier than tokens.
3. **CSRF cookie + double-submit token**: standard web pattern but introduces cookie storage. Not worth the surface area for a localhost-only dashboard.
4. **Drop the gate; rely on PR #446's JS fix**: cheapest, but leaves the blast radius open to the next trigger.

Token gate wins on defense-in-depth + already-validated-by-attune-gui + minimal new infrastructure.

## Acceptance criteria

- `GET /api/session/token` exists and returns `{"token": "<32-char-url-safe>"}`.
- Every mutating endpoint listed above 403s on missing or wrong `X-Attune-Client`.
- Every mutating client-side fetch (in `specs.js`, `completion_candidates.js`, `runner.js`, and any others) reads the token at page load and includes it.
- The token is delivered to the page via a `<meta name="attune-client-token" content="...">` tag in `base.html` (avoids an extra fetch on every page load).
- Tests cover: missing header → 403, wrong token → 403, correct token → 2xx, GET `/api/session/token` is reachable without auth.
- `--read-only` still 403s mutating endpoints (existing behavior preserved).

## Execution gate

Not urgent. Don't start until:

1. PR #446 merged (Finding 0's JS trigger fixed first, so this isn't gated on the bug it defends against).
2. No active CI debt in attune-ai.
3. A reviewable inventory of mutating endpoints has been produced (see tasks.md task 1.1).

PR #446 alone closes the immediate observable bug. This spec is the structural follow-up.
