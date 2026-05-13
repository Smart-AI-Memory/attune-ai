# Design — Discovery Sweep

**Status:** approved with updates

Technical shape of the work. See `requirements.md` for what we're building, `tasks.md` for the phase plan, `decisions.md` for why.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ CLI: attune workflow run discovery-sweep --path X           │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ DiscoverySweepWorkflow (workflow.py)                        │
│                                                             │
│  execute(path, budget_usd):                                 │
│   1. sources = default_sources()                            │
│   2. allocate per-source budget                             │
│   3. fan out: run each source.discover() in parallel        │
│   4. collect findings (handle source failures)              │
│   5. apply verification rules → bucket each finding         │
│   6. return SweepResult{ queue, questions, rejected,        │
│                          metadata }                         │
└────────┬──────────────────────────────────┬─────────────────┘
         │                                  │
         ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────────────┐
│ FindingSource        │         │ Verification rules           │
│  Protocol            │         │  (deterministic, not LLM)    │
│                      │         │                              │
│  name: str           │         │  - dedup_by_location()       │
│  discover(path,      │         │  - severity_threshold()      │
│           budget) -> │         │  - resolve_conflicts() →     │
│       list[Finding]  │         │    routes to questions       │
└──────┬───────────────┘         │  - location_missing() →      │
       │                         │    routes to questions       │
       ▼                         └──────────────────────────────┘
┌──────────────────────────────────────────────────┐
│ Adapters                                         │
│                                                  │
│  PatternScanSource    (non-LLM, regex)           │
│  BugPredictSource     (wraps BugPredictionWflow) │
│  SecurityAuditSource  (wraps SecurityAuditWflow) │
│  DependencyCheckSource(wraps DependencyCheckWflw)│
│  PerfAuditSource      (wraps PerformanceAuditW.) │
│  DocAuditSource       (wraps DocAuditWorkflow)   │
└──────────────────────────────────────────────────┘
```

**Resolved (2026-05-13):** Parallel fan-out via `asyncio.gather(*coros, return_exceptions=True)`. Each adapter is an `async def discover(...)`. Source-level isolation: a crashed source becomes one `questions` entry, not a failed sweep. No engine-level throttle in v1 (sources self-throttle via the SDK).

---

## Data model

### Finding

```python
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["critical", "high", "medium", "low", "info"]

@dataclass(frozen=True)
class Finding:
    source: str                    # e.g. "bug-predict", "pattern-scan"
    severity: Severity
    title: str                     # one-line summary
    description: str               # 1–3 sentence detail
    file: str | None               # repo-relative path, None if N/A
    line: int | None               # 1-indexed, None if file-level finding
    evidence: str | None           # quote from source code or scanner output
    confidence: float              # 0.0–1.0, source-emitted
    tags: tuple[str, ...] = ()     # free-form for verification rules
    raw: dict | None = None        # source-emitted JSON for debugging
```

Findings are frozen because verification rules treat them as immutable inputs. Tags are a tuple (not list) so the dataclass is hashable, enabling set-based dedup.

### SweepResult

```python
@dataclass
class SweepResult:
    queue: list[Finding]
    questions: list[QuestionFinding]
    rejected: list[RejectedFinding]
    metadata: SweepMetadata

@dataclass
class QuestionFinding:
    finding: Finding
    reason: str          # human-readable why-can't-engine-decide
    next_step: str       # one-line hint from the rule that flagged it

@dataclass
class RejectedFinding:
    finding: Finding
    rule: str            # e.g. "SEVERITY_BELOW_THRESHOLD", "DUPLICATE_OF:..."

@dataclass
class SweepMetadata:
    spent_usd: float
    budget_usd: float
    sources: list[str]   # names of sources that ran (may be subset if some failed)
    failures: list[str]  # names of sources that failed + their error
    duration_ms: int
```

---

## FindingSource Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FindingSource(Protocol):
    name: str
    is_llm: bool
    budget_multiplier: float

    async def discover(
        self,
        paths: list[str],
        budget_usd: float,
    ) -> list[Finding]:
        """Discover findings under `paths`. Must respect budget_usd.

        `paths` is a list of concrete files or directories — the engine
        glob-expands the user's `--path` upstream so every source sees
        the same scope.

        Implementations should:
        - Return early (with partial findings) if budget is exhausted
        - Emit a Finding with severity="info", confidence=1.0,
          title="<source> reached budget mid-sweep" rather than raise,
          so the engine routes it to `questions` not failure path.
        - Never exceed `budget_usd`. The engine trusts the source on this.
        """
        ...
```

`budget_multiplier` is the source's proportional claim on the total budget pool. The engine sums multipliers across active sources and allocates `budget_usd * (mult / total)` to each. Non-LLM sources set `0.0`. See `decisions.md` § Cost discipline for defaults.

Adapters are constructed by `default_sources()` (or a test-only `make_sources(...)` helper). The engine never instantiates them directly — keeps source-list management out of `DiscoverySweepWorkflow`.

---

## Structured emit (LLM adapters)

Each LLM adapter augments its wrapped workflow's system prompt with a footer:

```text
In addition to your normal prose output, emit a JSON block at the END
of your response in the following format. The prose above is for the
human; the JSON is for downstream tooling.

```json
{
  "findings": [
    {
      "severity": "high" | "medium" | "low" | "info",
      "title": "one-line summary",
      "description": "1–3 sentence detail",
      "file": "repo-relative path or null",
      "line": <1-indexed int or null>,
      "evidence": "exact quote from source or null",
      "confidence": <float 0.0–1.0>,
      "tags": ["optional", "freeform"]
    }
  ]
}
```
```

Adapter parses the JSON block with a tolerant regex (`r"```json\s*(\{.*?\})\s*```"` with DOTALL). On parse failure or missing block:

```python
return [Finding(
    source=self.name,
    severity="info",
    title=f"{self.name} returned no structured findings",
    description=f"Workflow completed but emitted no parseable JSON block. "
                f"Raw output length: {len(text)} chars. Re-run with --verbose "
                f"to inspect.",
    file=None, line=None,
    evidence=text[:200] + "..." if len(text) > 200 else text,
    confidence=0.1,  # low — text-only fallback
    tags=("text-only-fallback",),
)]
```

This is what guarantees engine progress even when the LLM ignores the JSON instruction: one low-confidence finding ends up in `questions`, the user sees that the adapter degraded, and the sweep moves on.

> **DECIDE:** Exact JSON schema. Sketch above is a starting point — finalize during P2.1.

### Prompt augmentation lives at the workflow-instance level, NEVER class

Adapters must build a per-call workflow instance and append `STRUCTURED_EMIT_FOOTER` to the instance's prompt before invoking `execute()`. Mutating the workflow class's prompt template would leak into every other caller (standalone `attune workflow run bug-predict`, MCP `mcp__attune-ai__bug_predict`, the ops dashboard, etc.) and force them to parse the JSON footer they didn't ask for. The augmentation is a discovery-sweep concern; everyone else sees the unmodified workflow.

Concretely: each adapter's `discover()` constructs the wrapped workflow with the augmented system prompt as an instance attribute (or kwargs to `__init__` if the workflow supports it), runs it, and discards the instance. No global state, no monkey-patching of the workflow class.

---

## Verification rules (engine internals)

Rules run in order; each can route a finding to a bucket OR pass it to the next rule. A finding that survives all rules lands in `queue`.

```python
def route(finding: Finding, all_findings: list[Finding]) -> Bucket:
    # Rule 1: location required for queue
    if finding.file is None and "file-level" not in finding.tags:
        return Questions(reason="LOCATION_MISSING",
                         next_step="Re-run source with --explain to surface location")

    # Rule 2: severity threshold
    if SEVERITY_RANK[finding.severity] < SEVERITY_RANK["medium"]:
        return Rejected(rule="SEVERITY_BELOW_THRESHOLD")

    # Rule 3: confidence threshold
    if finding.confidence < 0.5:
        return Questions(reason="LOW_CONFIDENCE",
                         next_step="Manually verify; source rated < 50% confident")

    # Rule 4: dedup by (file, line) — keep highest severity, route others to rejected
    same_loc = [f for f in all_findings
                if f.file == finding.file and f.line == finding.line and f is not finding]
    if same_loc and not _is_highest_severity_at_location(finding, same_loc):
        return Rejected(rule=f"DUPLICATE_OF:{_highest(same_loc).source}")

    # Rule 5: conflicting severity from same location → question, not queue
    if same_loc and _severity_conflict(finding, same_loc):
        return Questions(reason="SEVERITY_CONFLICT",
                         next_step=f"Sources disagree on severity at {finding.file}:{finding.line}. "
                                   f"Read both findings and decide.")

    # Survived → queue
    return Queue()
```

**Resolved (2026-05-13):** Severity rank order `critical > high > medium > low > info`. Queue threshold = `medium`. Confidence threshold = `0.5` (findings below route to `questions` with reason `LOW_CONFIDENCE`). Tune after dogfood.

---

## Default sources list

```python
# src/attune/workflows/discovery_sweep/cli_workflow.py

def default_sources() -> list[FindingSource]:
    """Return the default source list for `attune workflow run discovery-sweep`."""
    return [
        PatternScanSource(),
        BugPredictSource(),
        SecurityAuditSource(),
        DependencyCheckSource(),
        PerfAuditSource(),
        DocAuditSource(),
        TestAuditSource(),
    ]
```

All six audit-family workflows get an adapter (see `decisions.md` § "Why this isn't `code-review` or `deep-review`"). The `--no-llm` flag filters to `[s for s in default_sources() if not s.is_llm]`.

> **DECIDE:** `--source <name>` filter. Cheap addition; defer if not needed.

---

## CLI integration

```python
# src/attune/workflows/__init__.py — register

_DEFAULT_WORKFLOW_NAMES = {
    ...existing...,
    "discovery-sweep": "DiscoverySweepWorkflow",
}

# Lazy import block
def __getattr__(name):
    if name == "DiscoverySweepWorkflow":
        from .discovery_sweep import DiscoverySweepWorkflow
        return DiscoverySweepWorkflow
```

CLI surface (`attune workflow run discovery-sweep ...`) is already uniform per the recent path-arg unification work — no `cli_minimal.py` changes needed beyond ensuring `discovery-sweep` accepts the `--path`, `--budget`, `--verbose`, `--json`, `--no-llm` kwargs.

**Resolved (2026-05-13):** `discovery-sweep` joins `PATH_ARG_REGISTRY` as **Category A** (`kwarg="path"`, `required=False`). Required for the ops-dashboard scope picker. Wired in P1.7.

---

## File layout

```
src/attune/workflows/discovery_sweep/
├── __init__.py                  # exports DiscoverySweepWorkflow
├── workflow.py                  # engine + FindingSource Protocol + Finding dataclass
├── cli_workflow.py              # default_sources(), CLI glue
├── verification.py              # routing rules
├── sources/
│   ├── __init__.py
│   ├── pattern_scan.py          # PatternScanSource (non-LLM)
│   ├── bug_predict.py           # BugPredictSource
│   ├── security_audit.py        # SecurityAuditSource
│   ├── dependency_check.py      # DependencyCheckSource
│   ├── perf_audit.py            # PerfAuditSource
│   ├── doc_audit.py             # DocAuditSource
│   └── test_audit.py            # TestAuditSource
└── llm_source_base.py           # shared parser + structured-emit prompt helper
```

`llm_source_base.py` provides:

- `STRUCTURED_EMIT_FOOTER` — the prompt-augmentation string described above
- `parse_findings_json(text: str, source_name: str) -> list[Finding]` — tolerant parser with text-only fallback
- `LLMSource` — optional marker base class (just sets `is_llm = True`); adapters can inherit or set the attribute directly

---

## Tests

| Test file | What it covers |
|---|---|
| `tests/unit/workflows/discovery_sweep/test_engine.py` | DiscoverySweepWorkflow.execute happy path with fake sources, budget allocation, source failure isolation |
| `tests/unit/workflows/discovery_sweep/test_verification.py` | Each rule individually + interaction (severity then dedup then conflict) |
| `tests/unit/workflows/discovery_sweep/test_pattern_scan_source.py` | PatternScanSource on real files in `tests/fixtures/` |
| `tests/unit/workflows/discovery_sweep/test_bug_predict_source.py` | Mocks `BugPredictionWorkflow.execute`, asserts Finding parsing |
| `tests/unit/workflows/discovery_sweep/test_llm_source_base.py` | `parse_findings_json` happy path + malformed JSON + missing block |
| `tests/integration/workflows/test_discovery_sweep_integration.py` | `@pytest.mark.integration` — real sweep on a tiny fixture path (see `tasks.md` P2.1 for the rationale: integration mark is the project-standard gate, replacing the older `HAS_API_KEY` skipif pattern that masked code regressions as Anthropic network flakes) |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Structured-emit prompt fails on some Claude versions (model decides "the prose was enough") | medium | Text-only fallback path + a contract test per adapter that asserts the JSON block was found |
| Budget allocation under-spends because some sources finish early | low | Acceptable in v1; redistribution is a v2 concern |
| Verification rules over-reject and `queue` is too small | medium | `--verbose` exposes rejected with rules; tune thresholds based on real runs |
| Verification rules under-reject and `queue` is noisy | medium | Same — dogfood + threshold tuning |
| Sources crash silently (network, SDK errors) | low | `return_exceptions=True` in `asyncio.gather` + per-source failure → questions entry |
| Concurrent sources flood the API at the same time | low | Sources internally throttle via SDK; engine doesn't add its own throttle in v1 |
