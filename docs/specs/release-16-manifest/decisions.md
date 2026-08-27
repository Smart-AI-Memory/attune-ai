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
