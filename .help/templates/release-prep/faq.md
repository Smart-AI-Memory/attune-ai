---
type: faq
name: release-prep-faq
feature: release-prep
depth: faq
status: manual
---

# Release Prep FAQ

## What is release-prep?

Release-prep is the **deterministic gate** for shipping. Four agents
run real tools — `bandit`, `ruff`, `pytest --cov`, and a docstring /
README / CHANGELOG check — in parallel, measure the results against
hard quality-gate thresholds, and return an APPROVED or BLOCKED
verdict. It is the enforcement half of the release pair.

## What's the difference between release-prep and release-notes?

Release-prep is the deterministic gate — real bandit/ruff/pytest
against hard thresholds, returning APPROVED or BLOCKED. Release-notes
is advisory — it drafts a changelog and an LLM go/no-go and never
blocks. Run the gate with `attune workflow run release-gate`.

## How much does the gate cost?

$0 by default. `RELEASE_LLM_MODE` defaults to `"simulated"`, so the
agents score real tool output with rule-based logic and make no API
calls. Set `RELEASE_LLM_MODE=real` plus an `ANTHROPIC_API_KEY` to let
the security and quality agents classify their output with an LLM.

## What checks does it run?

Four agents run in parallel:

- **`SecurityAuditorAgent`** — `uv run bandit -r src/ -f json
  --severity-level medium`; `critical_issues` = CRITICAL + HIGH.
- **`TestCoverageAgent`** — `uv run pytest --cov=<target>`; parses the
  TOTAL coverage percentage.
- **`CodeQualityAgent`** — `uv run ruff check src/ --statistics`;
  maps violations to a 0–10 quality score.
- **`DocumentationAgent`** — AST walk of `src/**/*.py` for docstring
  coverage, plus README/CHANGELOG presence.

## Why did a BLOCKED run still exit 0?

`WorkflowResult.success` means the assessment **ran**, not that the
release was approved. The verdict is in `metadata["approved"]` (and
`metadata["confidence"]`), and the full report is in `final_output`.
Branch on the verdict, not the exit code.

## How do I run it?

- **CLI:** `attune workflow run release-gate` (canonical slug
  `release-prep`).
- **Python:** `await ReleasePrepTeamWorkflow().execute(path=".")`
  (importable from `attune.agents.release`).

There is no MCP tool for the gate — it is CLI / Python only.

## How do I customize the thresholds?

Pass a `quality_gates` dict to `ReleasePrepTeam` or
`ReleasePrepTeamWorkflow` using the keys `max_critical_issues`,
`min_coverage`, `min_quality_score`, and `min_doc_coverage`. Coverage
and doc-coverage are percentages (e.g. `90.0`), not fractions:

```python
import asyncio

from attune.agents.release import ReleasePrepTeam


async def main() -> None:
    team = ReleasePrepTeam(quality_gates={"min_coverage": 90.0})
    report = await team.assess_readiness(codebase_path=".")
    print(report.format_console_output())


asyncio.run(main())
```

## Which calls are async?

Both `ReleasePrepTeamWorkflow.execute` and
`ReleasePrepTeam.assess_readiness` are coroutines — `await` them or
drive them with `asyncio.run`.

**Tags:** `release`, `publishing`, `quality`
