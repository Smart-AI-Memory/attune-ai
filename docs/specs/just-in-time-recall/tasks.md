# Just-In-Time Recall — Tasks

**Status:** in progress (2026-06-09) — Phase 0 RESOLVED + Phase 1
**built**: the injection mechanism is **PreToolUse `additionalContext`**
(docs-verified D2, then **empirically smoke-tested on the current CC
version 2026-06-09** — a throwaway PreToolUse hook's injected sentinel
token appeared verbatim in a headless `claude -p` reply while the call
proceeded). Shipped: `plugin/hooks/_recall_map.py` (curated map, the
`AskUserQuestion` proof entry), `plugin/hooks/jit_recall.py`
(surface-once sentinel, fail-safe, `ATTUNE_JIT_RECALL=0` off-switch),
`hooks.json` registration, 12 tests. T1.4 live-proven 2026-06-10;
Phase 2 started: optional `match_substring` content filter + the
`release-verify-merge-sha` Bash entry (first T2.1 slip-point).

Independently shippable units. **Phase 0 gates everything** — no
implementation past it until the injection mechanism is logged in
`decisions.md` (D2). *(Gate cleared 2026-06-09.)*

## Phase 0 — verify the injection premise (gate)

- [x] **T0.1** Instrument a throwaway PreToolUse hook that returns
  `additionalContext` and observe whether the text reaches model context
  while the call still proceeds. Record the exact payload shape that
  works (or fails) for the installed Claude Code version.
- [x] **T0.2** (moot — T0.1 succeeded) If T0.1 fails, repeat for UserPromptSubmit
  `additionalContext`. Record which channel injects reliably.
- [x] **T0.3** Log the chosen mechanism + the working payload shape in
  `decisions.md` (resolve D2). Stop and confirm with Patrick before
  Phase 1 if the only working channel is the degraded "advisory block."

## Phase 1 — proof case: AskUserQuestion → question-shape rule

- [x] **T1.1** Create the curated map (`plugin/hooks/_recall_map.py` or a
  JSON sidecar) with the single `AskUserQuestion` entry → the
  question-shape one-liner (D3/D4).
- [x] **T1.2** Create `plugin/hooks/jit_recall.py`: read payload → map
  lookup → `(session_id, rule_id)` surface-once sentinel → inject via the
  Phase 0 channel → allow → fail-safe try/except (R2–R5). Register in
  `hooks.json` for the verified event.
- [x] **T1.3** Tests: map lookup, surface-once gate (second same-rule fire
  in a session is silent), no-entry silent no-op, crash → exit 0, and the
  injected-text content for the AskUserQuestion case. Mirror the
  `test_session_memory_hooks.py` importlib-loader pattern.
- [x] **T1.4** Reproduce the 2026-06-03 slip (an AskUserQuestion call) and
  confirm the rule surfaces at the decision point (R6). **Live-proven
  2026-06-10** (8.1.0 release session): the session's first
  AskUserQuestion — the pypi-approval question — received the
  question-shape rule via PreToolUse `additionalContext`, and the
  question conformed (one question, '(Recommended)' first option).

## Phase 2 — grow the map + tune cadence (deferred)

- [x] **T2.1** Add the next 2–3 highest-value slip-points (e.g. git push
  to a shared branch → fetch-first rule) once the proof case holds.
  *(Done 2026-06-20: 3 corpus-backed `Bash` slip-points added —
  `git-commit-verify-landed` (`git commit`), `admin-merge-verify-remote`
  (`pr merge`), `rebase-resigns-gpg` (`rebase`) — each `match_substring`-
  scoped and text-only (no dangling `lesson_ref`); +5 tests, live
  round-trip dogfood confirmed. Earlier: `release-verify-merge-sha` on
  `gh release create`, 2026-06-10.)*
- [ ] **T2.2** Decide the surface-once vs decay question (D5) from proof-
  case evidence; implement decay only if once-per-session proves too
  sparse.
- [ ] **T2.3** (Maybe) auto-derive map entries from lesson frontmatter
  tags — only if the curated map outgrows a single file.

## Notes

- Each phase is its own PR. Phase 0 may be a tiny throwaway-hook PR or
  even just a logged measurement; the build is Phase 1.
- Distinct from the P2 memory hooks — different corpus (rules vs
  findings), different trigger (decision-point vs door). No dependency
  either way.
