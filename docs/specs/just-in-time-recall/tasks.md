# Just-In-Time Recall — Tasks

Independently shippable units. **Phase 0 gates everything** — no
implementation past it until the injection mechanism is logged in
`decisions.md` (D2).

## Phase 0 — verify the injection premise (gate)

- [ ] **T0.1** Instrument a throwaway PreToolUse hook that returns
  `additionalContext` and observe whether the text reaches model context
  while the call still proceeds. Record the exact payload shape that
  works (or fails) for the installed Claude Code version.
- [ ] **T0.2** If T0.1 fails, repeat for UserPromptSubmit
  `additionalContext`. Record which channel injects reliably.
- [ ] **T0.3** Log the chosen mechanism + the working payload shape in
  `decisions.md` (resolve D2). Stop and confirm with Patrick before
  Phase 1 if the only working channel is the degraded "advisory block."

## Phase 1 — proof case: AskUserQuestion → question-shape rule

- [ ] **T1.1** Create the curated map (`plugin/hooks/_recall_map.py` or a
  JSON sidecar) with the single `AskUserQuestion` entry → the
  question-shape one-liner (D3/D4).
- [ ] **T1.2** Create `plugin/hooks/jit_recall.py`: read payload → map
  lookup → `(session_id, rule_id)` surface-once sentinel → inject via the
  Phase 0 channel → allow → fail-safe try/except (R2–R5). Register in
  `hooks.json` for the verified event.
- [ ] **T1.3** Tests: map lookup, surface-once gate (second same-rule fire
  in a session is silent), no-entry silent no-op, crash → exit 0, and the
  injected-text content for the AskUserQuestion case. Mirror the
  `test_session_memory_hooks.py` importlib-loader pattern.
- [ ] **T1.4** Reproduce the 2026-06-03 slip (an AskUserQuestion call) and
  confirm the rule surfaces at the decision point (R6). Record the
  before/after in the PR.

## Phase 2 — grow the map + tune cadence (deferred)

- [ ] **T2.1** Add the next 2–3 highest-value slip-points (e.g. git push
  to a shared branch → fetch-first rule) once the proof case holds.
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
