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
