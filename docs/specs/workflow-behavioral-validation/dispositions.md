# Probe dispositions — hand-authored intentional gaps

The ONE hand-authored piece of the registry (D3): workflows that have
no run-record yet, and why. Per the spec, a workflow with neither a
record nor an entry here renders in `registry.md` as needing attention
— absence is "not yet probed", never "clean". Remove an entry when its
workflow gains a probe + record.

Format (parsed by `scripts/project_probe_registry.py`):
`- **workflow-name** — reason`.

- **bug-predict** — exercised as a discovery-sweep lane (8 findings in
  the 2026-08-23 sweep record); no standalone probe yet. Candidate for
  the analytical batch's next increment.
- **doc-gen** — BROKEN class from the fleet roundtable (Sev3,
  deterministic SDK failure); generative probes come last (D5): fix
  first, then probe by executing the emitted output.
- **doc-orchestrator** — fail-open group (roundtable Sev5, "no gaps"
  after its scout failed); probe lands with the gate-group batch and
  must assert the DEGRADED behavior #2209 adds.
- **fix** — requires a `goal` argument (dashboard-unrunnable class from
  the roundtable); needs a purpose-built fixture + invocation, not the
  shared analytical workdir.
- **health-check** — fail-open group (roundtable Sev2, fabricated
  100/100); probe lands with the gate-group batch and must assert
  DEGRADED/N-A rendering per #2209, not a numeric score.
- **orchestrated-health-check** — same gate-group batch as
  health-check (it is the orchestrated variant of the same surface).
- **rag-code-gen** — requires a `query` argument (dashboard-unrunnable
  class); generative batch (D5), probe must execute/resolve the cited
  output.
- **release-gate** — deterministic rule-based gate (the roundtable's
  honest-degrade counterexample); a planted failing-gate fixture probe
  is planned with the gate-group batch.
- **release-prep** — same deterministic gate family as release-gate;
  covered indirectly by release-notes' metric-crosscheck probe until
  the gate-group batch lands.
- **research-synthesis** — BROKEN class from the fleet roundtable
  (Sev6, dies after ~229s); fix first, then probe.
- **secure-release** — fail-open group (roundtable Sev1, GO on a dead
  gate — fixed in #2208); its probe is the highest-teeth one in the
  gate-group batch: a fixture whose sub-workflow fails MUST yield
  NO_GO.
