# Tasks — Ops mutating-endpoint auth

**Status:** done (2026-06-05) — implemented; live-smoke verified


## Phase 1 — Inventory + scaffold

- [x] **1.1** Inventory every `@router.(put|post|delete|patch)` route under `src/attune/ops/routes/`. Produce a table in this file: route, method, file:line, "needs token?" (default yes; document any "no" with reason).

  Inventory (all gated — no exceptions):

  | Route | Method | File | Gated |
  |---|---|---|---|
  | `/api/specs/{slug}/{phase}/status` | PUT | `routes/specs.py` | yes |
  | `/api/specs/{slug}/completion-candidates/dismiss` | POST | `routes/specs.py` | yes |
  | `/workflows/{name}/run` | POST | `routes/runner.py` | yes |
  | `/api/help/regen` | POST | `routes/help.py` | yes |
  | `/api/telemetry/interaction` | POST | `routes/interaction_counters.py` | yes |
  | `/curator/dismiss` | POST | `routes/curator.py` | yes |
  | `/curator/answer` | POST | `routes/curator.py` | yes |
- [x] **1.2** Add `src/attune/ops/security.py` (mirror `attune-gui/sidecar/attune_gui/security.py`):
  - `_SESSION_TOKEN = secrets.token_urlsafe(32)`
  - `current_session_token()` getter
  - `require_client_token` Depends function (reads `x_attune_client: str | None = Header(default=None)`)
  - Unit tests: consolidated into `tests/unit/ops/test_mutating_endpoint_auth.py` (covers token + endpoint + gate together) rather than a separate `test_security.py`.

## Phase 2 — Session-token endpoint

- [x] **2.1** New route `GET /api/session/token` returning `{"token": "..."}`. No auth. Place in a new file `src/attune/ops/routes/session.py` or inline in `server.py` near the app factory.
- [x] **2.2** Inject the token into the rendered page via a `<meta name="attune-client-token" content="...">` tag in `templates/base.html`. Reading via meta avoids a second fetch on every page load.
- [x] **2.3** Tests: the endpoint returns 200 with a non-empty token; the meta tag appears on every server-rendered page.

## Phase 3 — Apply the gate

For each mutating route surfaced in 1.1:

- [x] **3.1** Add `Depends(require_client_token)` to the route signature.
- [x] **3.2** Add tests: PUT/POST without header → 403; with wrong token → 403; with correct token → expected 2xx.

Workflows already covered if 1.1 surfaces them.

## Phase 4 — Wire the client side

- [x] **4.1** Add a tiny helper at the top of every JS file that does mutating fetches: read the meta tag once at module load, store in a module-scoped const. Inject `X-Attune-Client` on every mutating `fetch()`.
  - Files known so far: `static/js/specs.js`, `static/js/completion_candidates.js`, `static/js/runner.js`. Confirm via grep for `method: "PUT"`, `method: "POST"`, `method: "DELETE"`.
- [x] **4.2** Manual smoke: launch ops, do each mutating action via the dashboard (status flip, completion-confirm, completion-dismiss, workflow run, run cancel). All should still work.

## Phase 5 — Docs + close

- [x] **5.1** README section: "Localhost security model" — explain the layered approach (loopback bind, trusted Host, read-only flag, X-Attune-Client token).
- [x] **5.2** Close `docs/specs/ops-specs-features/phase4-findings.md` Finding 0 with a forward reference to this spec.

## Out of scope (firm — do not creep)

- Multi-user / network-exposed auth.
- Token rotation / refresh.
- Cookie-based auth.
- A token-aware curl wrapper / CLI helper (could be a follow-up if it turns out to be friction).
