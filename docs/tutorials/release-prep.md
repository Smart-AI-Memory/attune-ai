---
type: tutorial
name: tutorial-release-prep
tags: [release, publishing, ci]
---

# Tutorial: Release Prep

You want to know whether your project is safe to ship — not just a gut feeling, but a structured verdict backed by code quality scores, security findings, and documentation checks. This tutorial walks you through building a small Python script that runs the full release-prep pipeline against a real codebase and prints a formatted go/no-go report to your terminal.

When you finish, you'll have a running script that:
- Spins up `ReleasePrepTeam` with custom quality-gate thresholds
- Runs four specialized agents in parallel (code quality, test coverage, security, and documentation)
- Prints the formatted assessment, including any blockers, to your console

## Prerequisites

- Python 3.10 or newer
- The `release` package installed in your environment
- A local Python project you want to assess (the current directory works fine)

## What you will build

A single file — `check_release.py` — that you run from the command line:

```
python check_release.py
```

It exits with code `0` on GO and `1` on NO-GO, so you can drop it straight into a CI pipeline later.

---

## Step 1 — Import the public surface

Open a new file called `check_release.py` and add these imports. Each name comes from the `release` package's public API, so you only need one import line for the classes and one for the models.

```python
from release import ReleasePrepTeam, ReleaseReadinessReport
```

`ReleasePrepTeam` orchestrates all four agents; `ReleaseReadinessReport` is the dataclass you'll inspect to read the verdict.

**Verify:** Run `python -c "from release import ReleasePrepTeam, ReleaseReadinessReport; print('OK')"`. You should see `OK` with no import errors.

---

## Step 2 — Define your quality gates

Quality gates tell the team what scores count as a pass. Each gate maps a check area to a minimum threshold between `0.0` and `1.0`. You pass these into `ReleasePrepTeam` at construction time so the agents know what bar to clear.

```python
gates = {
    "coverage":    0.80,   # 80 % line coverage minimum
    "quality":     0.75,   # code-quality score from ruff + type hints
    "security":    0.90,   # security audit score
    "documentation": 0.70, # docstring coverage + README + CHANGELOG
}

team = ReleasePrepTeam(quality_gates=gates)
```

Passing `None` uses the built-in defaults; this explicit dict lets you see exactly which thresholds drive the verdict.

**Verify:** Add `print(team)` temporarily and run the script. Python should print the object representation without raising an error. Remove the `print` before continuing.

---

## Step 3 — Run the assessment

`assess_readiness` is the single method that triggers all agents and blocks until every result is collected. Pass it the path to your project root — `'.'` targets whatever directory you run the script from.

```python
report: ReleaseReadinessReport = team.assess_readiness(codebase_path='.')
```

Under the hood, `ReleasePrepTeam` runs `TestCoverageAgent` (pytest --cov), `CodeQualityAgent` (ruff, type hints, complexity), `SecurityAuditorAgent`, and `DocumentationAgent` in parallel, then aggregates their `ReleaseAgentResult` objects into the report.

**Verify:** While this runs you should see agent activity in your terminal (log output from each agent). The call typically takes 30–90 seconds depending on project size.

---

## Step 4 — Print the formatted report

`ReleaseReadinessReport` has a `format_console_output()` method that renders the full assessment — verdict, per-gate scores, blockers, and warnings — in a human-readable layout.

```python
print(report.format_console_output())
```

Run the script now. You'll see something like:

```
Release Readiness Assessment
Verdict: NO-GO   Confidence: medium
─────────────────────────────────────────────────────
coverage        PASS   actual=0.87  threshold=0.80
quality         PASS   actual=0.79  threshold=0.75
security        FAIL   actual=0.61  threshold=0.90
documentation   PASS   actual=0.72  threshold=0.70

Blockers (1)
  security — 3 high-severity findings in src/auth/tokens.py

Warnings (1)
  coverage — branch coverage below 70%
```

Each `QualityGate` in `report.quality_gates` has `name`, `threshold`, `actual`, and `passed` fields if you want to process results programmatically instead of printing them.

**Verify:** Confirm the verdict line reads either `GO` or `NO-GO`. If it reads `NO-GO`, the `report.blockers` list will be non-empty — that's expected and correct behavior.

---

## Step 5 — Exit with the right code

Wire the verdict to the process exit code so CI treats a NO-GO as a failure.

```python
import sys
sys.exit(0 if report.approved else 1)
```

`report.approved` is a `bool` field on `ReleaseReadinessReport` that is `True` only when every critical quality gate passed.

**Verify:** Run `python check_release.py; echo "Exit code: $?"`. A passing project prints `Exit code: 0`; a project with blockers prints `Exit code: 1`.

---

## Complete script

```python
import sys
from release import ReleasePrepTeam, ReleaseReadinessReport

gates = {
    "coverage":      0.80,
    "quality":       0.75,
    "security":      0.90,
    "documentation": 0.70,
}

team = ReleasePrepTeam(quality_gates=gates)
report: ReleaseReadinessReport = team.assess_readiness(codebase_path='.')

print(report.format_console_output())
sys.exit(0 if report.approved else 1)
```

---

## What you learned

- **Step 1** showed you that `ReleasePrepTeam` and `ReleaseReadinessReport` are the two public names you need — everything else is an implementation detail the team manages internally.
- **Step 2** made quality gates concrete: you saw how `coverage`, `quality`, `security`, and `documentation` thresholds map to the `QualityGate` dataclass fields `threshold` and `actual`.
- **Step 3** revealed what `assess_readiness` actually does — it runs `TestCoverageAgent`, `CodeQualityAgent`, `SecurityAuditorAgent`, and `DocumentationAgent` in parallel and collects their `ReleaseAgentResult` objects.
- **Step 4** showed you the two ways to consume a `ReleaseReadinessReport`: human-readable via `format_console_output()`, and programmatic via fields like `blockers`, `warnings`, and `quality_gates`.
- **Step 5** closed the loop by connecting `report.approved` to a process exit code, turning your script into a real CI gate.

## Next steps

To understand how the individual agents decide their scores — what ruff rules `CodeQualityAgent` enforces, what patterns `SecurityAuditorAgent` flags, and how the `Tier` escalation works when an agent's confidence is too low — read the [release prep reference](../reference/ref-release-prep.md).

<!-- attune-generated: source_hash=154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2 feature=release-prep kind=tutorial generated_at=2026-06-02 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 38 (code fence) | error | `from release import …` — module not importable |
| Line 162 | error | `[release prep reference](../reference/ref-release-prep.md)` — target does not exist |
| Line 60 (python fence) | error | Name "ReleasePrepTeam" is not defined  [name-defined] |
| Line 74 (python fence) | error | Name "ReleaseReadinessReport" is not defined  [name-defined] |
| Line 74 (python fence) | error | Name "team" is not defined  [name-defined] |
| Line 88 (python fence) | error | Name "report" is not defined  [name-defined] |
| Line 121 (python fence) | error | Name "report" is not defined  [name-defined] |
