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
- **doc-gen** — fixed-and-validated 2026-08-24: the "deterministic
  SDK failure" class was the #2227 runner-path condition (API key at
  its usage cap wearing the is_error-on-success mask); with #2229 on
  main and the cap raised, the exact runner command completed live
  (exit 0, $1.06, 148s, real report). The D5 generative probe
  (execute the emitted output) is still owed — this entry records the
  fix receipt, not a probe.
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
- **research-synthesis** — fixed-and-validated 2026-08-24: same
  #2227 class as doc-gen; runner-path run completed live (exit 0,
  $1.18, 189s, substantive analysis). D5 generative probe still owed.
