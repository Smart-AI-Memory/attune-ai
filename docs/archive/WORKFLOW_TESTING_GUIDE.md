# Workflow Testing Guide

Complete guide to test all 31 Attune workflows.

## Quick Start (Automated)

Run the automated test script:

```bash
./scripts/test_all_workflows.sh
```

## Workflow Count Summary

| Category           | Count |
|--------------------|-------|
| Code Analysis      | 5     |
| Test Generation    | 7     |
| Documentation      | 5     |
| Release & Deploy   | 5     |
| Research & Planning| 3     |
| Meta/Orchestration | 3     |
| Experimental       | 3     |
| **Total**          | **31**|

---

## Manual Testing Checklist

### 1. Verify CLI Installation

```bash
# Should show help text
uv run attune --help

# Should list all 31 workflows
uv run attune workflow list
```

**Expected:** 31 workflows listed

---

## Code Analysis Workflows (5)

### code-review

```bash
uv run attune workflow run code-review --path src/attune/config.py
```

**Expected:** Code quality analysis with suggestions

### bug-predict

```bash
uv run attune workflow run bug-predict --path src/attune/
```

**Expected:** Bug risk scores based on patterns

### security-audit

```bash
uv run attune workflow run security-audit --path src/attune/config.py
```

**Expected:** Security analysis with vulnerability findings

### perf-audit

```bash
uv run attune workflow run perf-audit --path src/attune/workflows/
```

**Expected:** Performance bottleneck analysis

### pro-review

```bash
uv run attune workflow run pro-review --path src/attune/config.py
```

**Expected:** Combined crew + tier-based review

---

## Test Generation Workflows (7)

### test-gen

```bash
uv run attune workflow run test-gen --path src/attune/config.py
```

**Expected:** Generated test suggestions

### test-gen-behavioral

```bash
uv run attune workflow run test-gen-behavioral --path src/attune/config.py
```

**Expected:** BDD-style test templates

### test-gen-parallel

```bash
uv run attune workflow run test-gen-parallel --path src/attune/config.py
```

**Expected:** Parallel test generation output

### test-coverage-boost

```bash
uv run attune workflow run test-coverage-boost --path src/attune/
```

**Expected:** Multi-agent coverage boost results

### test-maintenance

```bash
uv run attune workflow run test-maintenance --path src/attune/
```

**Expected:** Test lifecycle management report

### autonomous-test-gen

```bash
uv run attune workflow run autonomous-test-gen --path src/attune/config.py
```

**Expected:** Self-improving test generation output

### progressive-test-gen

```bash
uv run attune workflow run progressive-test-gen --path src/attune/config.py
```

**Expected:** Progressive tier escalation output

---

## Documentation Workflows (5)

### doc-gen

```bash
uv run attune workflow run doc-gen --path src/attune/config.py
```

**Expected:** Generated documentation content

### doc-orchestrator

```bash
uv run attune workflow run doc-orchestrator --path src/attune/
```

**Expected:** Full documentation management output

### manage-docs

```bash
uv run attune workflow run manage-docs --path src/attune/
```

**Expected:** Same as doc-orchestrator (alias)

### document-manager

```bash
uv run attune workflow run document-manager --path src/attune/
```

**Expected:** Expert document creation output

### seo-optimization

```bash
uv run attune workflow run seo-optimization --path docs/
```

**Expected:** SEO analysis and recommendations

---

## Release & Deploy Workflows (5)

### release-prep

```bash
uv run attune workflow run release-prep
```

**Expected:** Release readiness checklist

### release-prep-legacy

```bash
uv run attune workflow run release-prep-legacy
```

**Expected:** Legacy pre-release quality gate

### secure-release

```bash
uv run attune workflow run secure-release
```

**Expected:** Security pipeline results

### orchestrated-release-prep

```bash
uv run attune workflow run orchestrated-release-prep
```

**Expected:** Meta-orchestrated release prep

### dependency-check

```bash
uv run attune workflow run dependency-check
```

**Expected:** Dependency audit results

---

## Research & Planning Workflows (3)

### research-synthesis

```bash
uv run attune workflow run research-synthesis --path docs/
```

**Expected:** Synthesized research output

### refactor-plan

```bash
uv run attune workflow run refactor-plan --path src/attune/
```

**Expected:** Prioritized refactoring targets

### keyboard-shortcuts

```bash
uv run attune workflow run keyboard-shortcuts
```

**Expected:** Generated keyboard shortcuts

---

## Meta/Orchestration Workflows (3)

### orchestrated-health-check

```bash
uv run attune workflow run orchestrated-health-check
```

**Expected:** Health check metrics

### batch-processing

```bash
uv run attune workflow run batch-processing
```

**Expected:** Batch processing configuration/status

### pr-review

```bash
uv run attune workflow run pr-review --path src/attune/config.py
```

**Expected:** Combined code + security review

---

## Experimental Workflows (3)

### test5

```bash
uv run attune workflow run test5 --path src/attune/
```

**Expected:** Code scan report

### orchestrated-health-check-experimental

```bash
uv run attune workflow run orchestrated-health-check-experimental
```

### orchestrated-release-prep-experimental

```bash
uv run attune workflow run orchestrated-release-prep-experimental
```

---

## Test Suite Integration

```bash
# Run all workflow-related tests
uv run pytest tests/ -k "workflow" -v

# Run with coverage
uv run pytest tests/ -k "workflow" --cov=src/attune/workflows --cov-report=term-missing

# Quick smoke test
uv run pytest tests/behavioral/test_workflow_base_behavioral.py -v
```

---

## Telemetry Verification

```bash
# Show recent workflow runs
uv run attune telemetry show

# View cost tracking
uv run attune telemetry costs
```

**Expected:** Telemetry data displays (may be empty on first run)

---

## Mock Mode Testing

Most workflows support `--mock` for testing without LLM API calls:

```bash
# Test without API calls
uv run attune workflow run security-audit --path src/ --mock
uv run attune workflow run code-review --path src/ --mock
uv run attune workflow run test-gen --path src/ --mock
```

---

## Troubleshooting

| Issue              | Solution                                        |
|--------------------|-------------------------------------------------|
| "Command not found"| Run `uv sync` to install dependencies           |
| Workflow hangs     | Add `--mock` flag for testing without LLM calls |
| "No API key"       | Set `ANTHROPIC_API_KEY` environment variable    |
| Import errors      | Check `uv run python -c "import attune"`        |
| Workflow not found | Run `uv run attune workflow list` to verify     |

---

## Success Criteria

All 31 workflows should:

- [ ] Start without import errors
- [ ] Accept `--path` parameter (where applicable)
- [ ] Produce output (not empty)
- [ ] Exit with code 0 on success
- [ ] Handle missing files gracefully
