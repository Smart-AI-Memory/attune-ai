# release-16-manifest — decisions

## D1 — Architecture direction: harness-lite with Codex's extension system (chair-ruled 2026-08-26)

**Ruled via the full round table**, thread
`q-core-plugins-vs-post-framework-001` (3 seats — Claude,
Antigravity, Codex — 2 rounds; full transcript machine-local at
`~/.attune/reports/roundtable/q-core-plugins-vs-post-framework-001.md`;
promoted board message ids: 8, 11, 12).

**The deliberation's shape mattered and is recorded:**

- **Round 1 was unanimously POST-FRAMEWORK** — collapse the
  speculative seams (`attune.plugins`, `attune.wizards`, the empty
  `attune.workflows` group), keep only `attune.memory_backends`
  (2 real implementations, user-facing degradation). Shared decision
  rule: *a seam exists when a second implementation exists or
  absence-degradation is user-facing behavior.*
- **The chair's lean was harness-shaped**, so the steelman-round
  provision fired rather than a bare overrule-or-capitulate choice.
  The chair injected one new fact, taken as given: **in-process
  Python extension (custom workflows, custom memory backends) is
  expected as real demand within roughly two releases.**
- **The steelman round dissolved the consensus: 3/3 seats produced
  a concrete harness-shaped design** — none took the "no
  harness-shaped design exists" exit. The round-1 rule did not
  flip; its inputs did (a second implementation is now forecast,
  and the cheap moment to open a seam is the breaking release
  already shipping).

**What all three round-2 designs agreed on (adopted as the
consensus core):**

1. Bundling stays — packaging is not the contract boundary;
   attune-redis stays in the wheel (the retraction is honored).
2. Exactly two capability contracts: workflows + memory backends.
   Round 1's collapses stand (plugins/wizards direct-import; empty
   entry-point group deleted).
3. Dependency-light contract modules frozen at 16.0.0,
   semver-stable.
4. Contract test kits ship with the seam.
5. Built-ins dogfood the public door, drift-guarded — the "second
   implementer" is attune itself, day one.
6. Fail-open loading with diagnosable degradation.

**The chair's mechanism ruling:** Codex's full extension system
(board message 11) — one unified `attune.extensions` entry-point
group with a frozen `Extension` manifest dataclass; **trust gating**
(installed ≠ executed until `attune extension enable`);
`list / inspect / enable / disable / doctor` CLI;
`attune.memory_backends` carried through 16.x as a compatibility
adapter; four named receipts prove the loop.

**Dissent register:** the Claude seat recommended the smaller
config-key loader (`extensions:` key naming modules; entry-point
discovery deferred to a 16.x minor) — declined in favor of
first-class trust gating from day one. Antigravity recommended a
dual programmatic + entry-point path — declined for re-creating an
entry-point group the table had just deleted and doubling the
frozen surface. Both designs remain in the transcript; the Claude
seat's contract-freeze + dogfooding elements are absorbed into the
consensus core.

**Basis note:** the external-consumer evidence (calibrated GitHub
code search ≈ 0 importers, control query ~30) is verified; the
in-process-extension demand is the chair's forecast, stated as such
— the design is sized so that if the demand never materializes, the
carrying cost is the extension module + CLI, not a framework.

## D2 — D1's mechanism CONFIRMED on the author-experience criterion (chair-ruled 2026-08-27)

After 16.0.0's destructive half shipped, the chair revisited the
extension-system mechanism (a downsized config-key-loader revision
had been drafted in-session on 2026-08-26 and deliberately slept on).
The lead put the question as WHICH CRITERION RULES — security posture
from day one, smallest frozen surface, or third-party author
experience — with the full argument set already on the round-table
board (threads `q-core-plugins-vs-post-framework-001` and
`q-16-release-reliability-001`). **The chair ruled: author
experience.** Under that criterion D1 stands as written: the unified
`attune.extensions` system with trust gating and the
`enable`/`doctor` CLI ships as passenger 4, because the polished
`pip install` + `enable` path is the ecosystem-creating surface the
config-key loader cannot offer.

Recorded against the counter-cases (all argued in-session, held on
the board): the security delta between the designs is ~zero until
third-party wheels exist; the reliability round located the
least-tested layer exactly where D1 lives (mitigated by the
now-permanent `scripts/release_artifact_smoke.py` gate); and the
smallest-frozen-surface argument favored the downsize. The chair
weighed the author-experience criterion as dominant with those
counter-cases in front of them — the fourth and final lean on this
decision, resolved by naming the criterion rather than re-litigating
the designs. The phased-shipping open question in requirements.md
remains open (contracts-first within 16.x is compatible with D1).

**Amended on the chair's cold re-read (2026-08-27, post-release —
"stands, amended"):**

- **The affirmative case is a strategic bet, stated as such.** "The
  polished install-and-enable path creates the ecosystem" is an
  inference about how ecosystems form, not a verified fact — made
  knowing the calibrated external-author population currently
  measures zero and the community-directory listing is still absent.
  Its falsifier is named: if no external extension exists by the end
  of the 16.x line, the criterion is re-examinable at 17.0.0
  planning.
- **The criterion sequences the phases.** Under
  author-experience-as-dominant, the author-facing surface (the
  `enable` UX, the extension-author docs page, a working example
  extension) ships in the FIRST constructive increment, not the
  last — contracts-first phasing may not defer it.
- **Process note, recorded honestly:** the criterion answer arrived
  mid-CI-firefight and was recorded within minutes; the ruling was
  then re-read cold by the chair after the release closed, with the
  lead's critical read (four findings, all record-completeness, none
  attacking the criterion) in front of them, and ratified. Durable
  copies of both cited board threads are machine-local at
  `~/.attune/reports/roundtable/` (the board itself is TTL'd).

## D3 — Passenger 4 phasing (PROPOSED 2026-08-28 — NOT RULED)

**PROPOSED by the lead — the chair has not ruled this.**
Resolves the requirements.md open question "whether passenger 4
ships whole in 16.0.0 or contracts-first with the CLI following in
a 16.x minor."

### The question as written can no longer be answered as written

Both of its options are foreclosed, for different reasons:

- **"Whole in 16.0.0" is moot.** 16.0.0 shipped 2026-08-27 without
  passenger 4, and 16.1.0 followed. Verified: no
  `src/attune/extensions` module exists on `main`, and
  `pyproject.toml` declares no `attune.extensions` entry-point
  group.
- **"Contracts-first, CLI following" is forbidden by D2.** D2's
  cold-re-read amendment requires the author-facing surface — the
  `enable` UX, the author docs page, a working example extension —
  in the FIRST constructive increment. `enable` IS the author
  surface. A phasing that lands contracts in 16.2.0 and the CLI in
  16.3.0 defers exactly what the ruling criterion protects.

So the answer is **neither**. The proposal below slices the work
**vertically by capability** — each increment a complete
install-to-enable author path — rather than **horizontally by
layer**, which is the split D2 rules out.

### Phase A — memory backends, whole loop (target 16.2.0)

One capability contract, the entire author path working end to end.

Ships:

- `attune.extensions` public API module; frozen `Extension`
  manifest dataclass at `api_version = 1`
- the single `attune.extensions` entry-point group
- loader with trust gating: discovery reads distribution metadata
  without importing; only an enabled extension is imported
- `list / inspect / enable / disable / doctor` — the complete CLI,
  not a subset
- enablement persisted in attune config (the `attune config`
  surface already exists)
- the memory-backend capability contract (see D3a below)
- `attune.memory_backends` compatibility adapter, translating
  legacy entries into manifests internally
- `attune.testing` contract test kit for memory backends
- a minimal example extension in-repo, plus the extension-author
  docs page
- all four D1 receipts, with receipt 2 reading "enablement loads
  and constructs its BACKEND in-process"

Why memory backends lead: the seam is the only one D1 kept on its
own merits, and it is already real on disk — `resolve_backend()` at
[session_stash.py:45](src/attune/memory/session_stash.py:45)
resolves `attune.memory_backends` today, with two live
implementations and fail-open degradation. Phase A therefore
freezes a contract over behavior that already works, and needs no
change to any of the 72 workflow modules.

### Phase B — workflow contract (target 16.3.0, additive)

Adds `WorkflowRequest` / `WorkflowContext` / `WorkflowResult` and
populates the manifest's `workflows` field. Additive: the field
already carries a default in D1's dataclass, so no `api_version`
bump.

The containment that makes B affordable is stated as a constraint,
not left to the implementer: **built-ins dogfood the public
workflow contract through an adapter at the runner boundary, not
by rewriting workflow modules.** `BaseWorkflow` today is
stage-based (`_scan` / `_analyze` / `_report` via `run_stage`) and
does not match `async def run(request, context)`; 72 modules
subclass it. Codex's migration step 4 already says "keep the
implementations in their current modules" — this names the
mechanism that honors it.

Dogfooding is proven by a **ratcheted count** of built-ins actually
resolved through the public path, drift-guarded, starting small.
Not all 72 at once.

### Phase C — hardening (demand-gated, unscheduled)

Raise the dogfooding ratchet; emit the `attune.memory_backends`
deprecation warning on read; re-examine whether `api_version` stays
`1`. Opens only when a real extension exists, per D2's named
falsifier.

### D3a — freeze the NARROW memory contract, not today's protocol

The public frozen surface should be the small contract Codex
specified (construct / store / retrieve / health, with optional
operations advertised as capabilities), **not** the protocol at
[memory/backend.py](src/attune/memory/backend.py) as it stands —
`MemoryBackend` carries 10 methods and `SearchableMemoryBackend`
adds 6 more. Freezing 16 methods as semver-stable contradicts D1
consensus core item 3 (dependency-light contracts, small frozen
surface) and would bind attune to every accident of the current
interface. The bundled backends keep the fat protocol internally;
the compatibility adapter bridges. No breaking change to either
bundled backend.

### D3b — the freeze anchor moved

D1 reads "contract modules frozen at 16.0.0, semver-stable."
16.0.0 has shipped without them, so the anchor is now whichever
release first ships the contracts — 16.2.0 under this proposal.
This is a spec-text correction, not a change of intent.

### Open, deliberately not proposed

Timing. The other requirements.md open question (whether 16.x
carries the 15-manifest's shipped-by urgency) stays unruled here.
Phase A has no external dependency and no forced date; it is
schedulable whenever the chair wants it.
