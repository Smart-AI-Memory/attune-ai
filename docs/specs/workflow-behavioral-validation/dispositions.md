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
- **fix** — requires a `goal` argument (dashboard-unrunnable class from
  the roundtable); needs a purpose-built fixture + invocation, not the
  shared analytical workdir.
- **orchestrated-health-check** — same class as `health-check`
  (`OrchestratedHealthCheckWorkflow` serves both registry names); the
  health-check probe + record covers this surface.
- **rag-code-gen** — requires a `query` argument (dashboard-unrunnable
  class); generative batch (D5), probe must execute/resolve the cited
  output.
- **release-gate** — same class as `release-prep`
  (`ReleasePrepTeamWorkflow` serves both registry names); covered by
  the release-prep probe + record (currently FAIL — #2221).
