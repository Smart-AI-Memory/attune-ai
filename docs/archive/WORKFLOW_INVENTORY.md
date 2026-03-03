# Attune Workflow Inventory

Complete inventory of all workflows in the Attune framework.

**Total Registered:** 31 workflows
**Last Updated:** 2026-02-02

## Quick Reference

| Category | Count | Workflows |
|----------|-------|-----------|
| Code Analysis | 5 | code-review, bug-predict, security-audit, perf-audit, pro-review |
| Test Generation | 7 | test-gen, test-gen-behavioral, test-gen-parallel, test-coverage-boost, test-maintenance, autonomous-test-gen, progressive-test-gen |
| Documentation | 5 | doc-gen, doc-orchestrator, manage-docs, document-manager, seo-optimization |
| Release & Deploy | 5 | release-prep, release-prep-legacy, secure-release, orchestrated-release-prep, dependency-check |
| Research & Planning | 3 | research-synthesis, refactor-plan, keyboard-shortcuts |
| Meta/Orchestration | 3 | orchestrated-health-check, batch-processing, pr-review |
| Experimental/User | 3 | test5, orchestrated-*-experimental variants |

---

## Code Analysis Workflows

### code-review

Multi-tier code review with quality, security, and performance analysis.

```bash
uv run attune workflow run code-review --path src/
```

**Stages:** triage → analyze → synthesize
**Tiers:** cheap → capable → premium

---

### bug-predict

Predict bugs by correlating current code with historical patterns.

```bash
uv run attune workflow run bug-predict --path src/
```

**Features:**

- Pattern matching against known bug signatures
- Historical commit analysis
- Risk scoring by file

---

### security-audit

OWASP-focused security audit with vulnerability detection.

```bash
uv run attune workflow run security-audit --path src/
```

**Checks:**

- Injection vulnerabilities (SQL, command, path traversal)
- Authentication/authorization issues
- Sensitive data exposure
- Dependency vulnerabilities

---

### perf-audit

Identify performance bottlenecks and optimization opportunities.

```bash
uv run attune workflow run perf-audit --path src/
```

**Analyzes:**

- Algorithmic complexity
- Memory usage patterns
- I/O bottlenecks
- Caching opportunities

---

### pro-review

Composite workflow combining CodeReviewCrew with CodeReviewWorkflow.

```bash
uv run attune workflow run pro-review --path src/
```

**Combines:** Multi-agent crew review + tier-based analysis

---

## Test Generation Workflows

### test-gen

Generate tests targeting areas with historical bugs.

```bash
uv run attune workflow run test-gen --path src/module.py
```

**Features:**

- AST-based function analysis
- Priority based on bug history
- pytest-compatible output

---

### test-gen-behavioral

Generate BDD-style behavioral test templates.

```bash
uv run attune workflow run test-gen-behavioral --path src/
```

**Format:** Given-When-Then test structure

---

### test-gen-parallel

Generate tests in parallel using multi-tier LLMs.

```bash
uv run attune workflow run test-gen-parallel --path src/
```

**Advantage:** Faster generation for large codebases

---

### test-coverage-boost

Multi-agent crew for boosting test coverage.

```bash
uv run attune workflow run test-coverage-boost --path src/
```

**Agents:**

- Coverage Analyzer
- Test Generator
- Test Reviewer

---

### test-maintenance

Automatic test lifecycle management.

```bash
uv run attune workflow run test-maintenance --path src/
```

**Features:**

- Detect stale tests
- Track orphaned tests
- Generate test plans for new files

---

### autonomous-test-gen

Self-improving test generation with dashboard monitoring.

```bash
uv run attune workflow run autonomous-test-gen --path src/
```

**Features:**

- Continuous improvement loop
- Dashboard integration
- Anthropic best practices

---

### progressive-test-gen

Test generation with progressive tier escalation.

```bash
uv run attune workflow run progressive-test-gen --path src/
```

**Behavior:** Starts cheap, escalates on failure

---

## Documentation Workflows

### doc-gen

Multi-tier document generation workflow.

```bash
uv run attune workflow run doc-gen --path src/
```

**Outputs:** API docs, README sections, docstrings

---

### doc-orchestrator

End-to-end documentation management orchestrator.

```bash
uv run attune workflow run doc-orchestrator --path src/
```

**Features:**

- Full documentation lifecycle
- Cross-reference management
- Version tracking

---

### manage-docs

Alias for doc-orchestrator.

```bash
uv run attune workflow run manage-docs --path src/
```

---

### document-manager

Expert document creation using style guides and best practices.

```bash
uv run attune workflow run document-manager --path src/
```

---

### seo-optimization

Multi-tier SEO optimization workflow.

```bash
uv run attune workflow run seo-optimization --path content/
```

**Analyzes:** Keywords, meta tags, content structure

---

## Release & Deploy Workflows

### release-prep

Multi-agent release readiness assessment (orchestrated version).

```bash
uv run attune workflow run release-prep
```

**Checks:**

- Version consistency
- Changelog completeness
- Test coverage
- Security scan

---

### release-prep-legacy

Legacy pre-release quality gate workflow.

```bash
uv run attune workflow run release-prep-legacy
```

---

### secure-release

Comprehensive security pipeline for release preparation.

```bash
uv run attune workflow run secure-release
```

**Pipeline:**

1. Dependency audit
2. Code security scan
3. Secret detection
4. Final approval

---

### orchestrated-release-prep

Release preparation using meta-orchestration.

```bash
uv run attune workflow run orchestrated-release-prep
```

---

### dependency-check

Audit dependencies for security and updates.

```bash
uv run attune workflow run dependency-check
```

**Reports:**

- Vulnerable dependencies
- Outdated packages
- License compliance

---

## Research & Planning Workflows

### research-synthesis

Multi-tier research synthesis for comparing multiple documents.

```bash
uv run attune workflow run research-synthesis --sources doc1.md,doc2.md
```

**Use Cases:**

- Compare competing approaches
- Synthesize research papers
- Aggregate documentation

---

### refactor-plan

Prioritize tech debt with trajectory analysis.

```bash
uv run attune workflow run refactor-plan --path src/
```

**Outputs:**

- Prioritized refactoring targets
- Effort estimates
- Dependency analysis

---

### keyboard-shortcuts

Generate optimized keyboard shortcuts for any project.

```bash
uv run attune workflow run keyboard-shortcuts
```

---

## Meta/Orchestration Workflows

### orchestrated-health-check

Health check workflow using meta-orchestration.

```bash
uv run attune workflow run orchestrated-health-check
```

**Checks:**

- Test suite health
- Coverage metrics
- Code quality scores

---

### batch-processing

Process multiple tasks via Anthropic Batch API.

```bash
uv run attune workflow run batch-processing --tasks tasks.json
```

**Benefit:** 50% cost savings on batch operations

---

### pr-review

Combined code review + security audit for comprehensive PR analysis.

```bash
uv run attune workflow run pr-review --path src/
```

---

## Experimental/User Workflows

### test5

User-generated workflow for code scanning and reporting.

```bash
uv run attune workflow run test5 --path src/
```

---

### orchestrated-health-check-experimental

Experimental variant of orchestrated health check.

---

### orchestrated-release-prep-experimental

Experimental variant of orchestrated release prep.

---

## Workflow Categories by Use Case

### "I want to improve code quality"

1. `code-review` - General quality review
2. `bug-predict` - Find potential bugs
3. `perf-audit` - Find performance issues
4. `refactor-plan` - Plan improvements

### "I want to add tests"

1. `test-gen` - Generate basic tests
2. `test-gen-behavioral` - Generate BDD tests
3. `test-coverage-boost` - Boost coverage with crew
4. `autonomous-test-gen` - Self-improving generation

### "I want to ship safely"

1. `security-audit` - Security review
2. `dependency-check` - Dependency audit
3. `release-prep` - Full release checklist
4. `secure-release` - Security pipeline

### "I want documentation"

1. `doc-gen` - Generate docs
2. `doc-orchestrator` - Full doc management
3. `research-synthesis` - Compare/synthesize sources

---

## CLI Quick Reference

```bash
# List all workflows
uv run attune workflow list

# Run a workflow
uv run attune workflow run <workflow-name> --path <target>

# Run with mock mode (no LLM calls)
uv run attune workflow run <workflow-name> --mock

# Run with JSON output
uv run attune workflow run <workflow-name> --json

# Get help for a workflow
uv run attune workflow run <workflow-name> --help
```

---

## Version History

| Version | Workflows Added |
|---------|-----------------|
| v2.0 | Core 12 workflows |
| v3.0 | secure-release |
| v3.1 | pro-review, pr-review |
| v3.5 | doc-orchestrator, manage-docs |
| v3.6 | keyboard-shortcuts |
| v4.0 | orchestrated-health-check, orchestrated-release-prep |
| v5.0 | research-synthesis, test-coverage-boost, test-maintenance |
| v5.1 | autonomous-test-gen, batch-processing, progressive-test-gen |
