---
description: CLI Reference API reference: Complete reference for the `attune` command-line interface.
---

# CLI Reference

Complete reference for the `attune` command-line interface.

---

## Quick Reference

```bash
# Workflows
attune workflow list                    # List available workflows
attune workflow info <name>             # Show workflow details
attune workflow run <name> [options]    # Execute a workflow

# Telemetry
attune telemetry show                   # Display usage summary
attune telemetry savings                # Show cost savings
attune telemetry export -o <file>       # Export to CSV/JSON

# Provider
attune provider show                    # Show current provider
attune provider set <name>              # Set provider (anthropic)

# Memory (Lessons Learned)
attune remember "lesson text"           # Save a lesson
attune forget <number-or-keyword>       # Remove a lesson
attune lessons                          # List all lessons

# Utilities
attune validate                         # Validate configuration
attune version                          # Show version
```

---

## Workflow Commands

### `attune workflow list`

List all available workflows registered in the framework.

```bash
attune workflow list
```

**Output:**
```
📋 Available Workflows

------------------------------------------------------------
  security-audit           Audit code for security vulnerabilities
  bug-predict              Predict potential bugs using patterns
  release-prep             Prepare release with changelog
  test-coverage            Generate tests for coverage gaps
------------------------------------------------------------

Total: 4 workflows

Run a workflow: attune workflow run <name>
```

---

### `attune workflow info <name>`

Show detailed information about a specific workflow.

```bash
attune workflow info security-audit
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Workflow name |

---

### `attune workflow run <name>`

Execute a workflow with optional parameters.

```bash
# Basic usage
attune workflow run security-audit

# With target path
attune workflow run security-audit --path ./src

# With JSON input
attune workflow run bug-predict --input '{"threshold": 0.8}'

# Output as JSON (for CI/CD)
attune workflow run security-audit --path ./src --json
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Workflow name |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--path` | `-p` | Target path for analysis |
| `--input` | `-i` | JSON input data |
| `--target` | `-t` | Target value (e.g., coverage percentage) |
| `--depth` | | Analysis depth: `quick`, `standard`, `deep` |
| `--json` | `-j` | Output result as JSON |
| `--cheap` | | Force every inherit-default subagent onto Haiku for this run (opus/sonnet-pinned subagents unaffected) |

**Examples:**

```bash
# Security audit on src directory
attune workflow run security-audit --path ./src

# Bug prediction with custom threshold
attune workflow run bug-predict --input '{"path":"./src","threshold":0.7}'

# Test coverage targeting 80%
attune workflow run test-coverage --path ./src --target 80

# CI/CD friendly output
attune workflow run security-audit --path ./src --json > results.json

# Cheap-mode: route inherit-default subagents to Haiku
attune workflow run bug-predict --cheap
```

### Cost knobs

`--cheap` is a single-flag shortcut for
`ATTUNE_AGENT_MODEL_DEFAULT=haiku`. For finer-grained control,
set per-keyword env vars listed in
[PROJECT_OVERVIEW.md → Per-Agent Model Override](../PROJECT_OVERVIEW.md#per-agent-model-override).
Subagent names are matched against keywords (first match wins):
security/vuln/architect → opus; quality/plan/research → sonnet;
complexity/lint/coverage/dep/scanner/finder/detector → haiku;
reviewer → inherit (override hook).

### Spend gate

The first billable `attune workflow run` of a session surfaces an
estimate and asks for an explicit go before any paid call. Once you
confirm, a session **spend window** (~5h, aligned to Anthropic's
rolling usage window) is established and later runs proceed silently
until the window expires or a run would exceed it. A `--no-llm` run
never reaches the gate.

The framing matches your billing meter: API users see a dollar band
(`≈ up to $X`), subscription users see usage-headroom framing (no
dollar figure).

| Env var | Effect |
|---------|--------|
| `ATTUNE_SPEND_GATE=off` | Disable the gate entirely (always proceed). |
| `ATTUNE_MAX_BUDGET_USD=0` | Also disables the gate (the existing cap-disable; `0` = no cap). |
| `ATTUNE_MAX_BUDGET_USD=<n>` | Sets the per-run estimate band / cap (positive float). |
| `ATTUNE_SPEND_GATE_AUTHORIZED=1` | Pre-authorize a **non-interactive** run (CI, the ops daemon) — required because a context that can't prompt blocks by default rather than spending silently. |

In a non-interactive run (no TTY) with no pre-authorization, the gate
**blocks** rather than spend silently, and prints the
`ATTUNE_SPEND_GATE_AUTHORIZED=1` hint. The ops dashboard and the
`security-scan` CI workflow set this opt-in automatically.

---

## Telemetry Commands

### `attune telemetry show`

Display usage summary including API calls, tokens, and costs.

```bash
attune telemetry show
attune telemetry show --days 7
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--days` | `-d` | 30 | Number of days to summarize |

**Output:**
```
📊 Telemetry Summary

------------------------------------------------------------
  Period:         Last 30 days
  Workflow runs:  45
  Total tokens:   1,234,567
  Total cost:     $12.34
------------------------------------------------------------
```

---

### `attune telemetry savings`

Show cost savings from intelligent tier routing.

```bash
attune telemetry savings
attune telemetry savings --days 90
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--days` | `-d` | 30 | Number of days to analyze |

**Output:**
```
💰 Cost Savings Report

------------------------------------------------------------
  Period:              Last 30 days
  Actual cost:         $12.34
  Premium-only cost:   $45.00 (estimated)
  Savings:             $32.66
  Savings percentage:  72.6%

  * Premium baseline assumes Claude Opus pricing (~$45/1M tokens)
------------------------------------------------------------
```

---

### `attune telemetry export`

Export telemetry data to a file.

```bash
attune telemetry export -o telemetry.json
attune telemetry export -o telemetry.csv --format csv
```

**Options:**

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--output` | `-o` | Yes | - | Output file path |
| `--format` | `-f` | No | json | Output format (json/csv) |
| `--days` | `-d` | No | 30 | Number of days |

---

### `attune telemetry routing-stats`

Show adaptive routing statistics — how the tier router chose between cheap,
capable, and premium models across your workflows.

```bash
attune telemetry routing-stats
attune telemetry routing-stats --workflow security-audit
attune telemetry routing-stats --workflow code-review --stage scan --days 14
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--workflow` | `-w` | all | Filter by workflow name |
| `--stage` | `-s` | all | Filter by stage name within a workflow |
| `--days` | `-d` | 7 | Number of days to include |

**Output (per workflow):**
```
📊 Adaptive Routing Statistics

  Workflow:      security-audit
  Period:        Last 7 days
  Total calls:   28
  Avg cost:      $0.0034
  Success rate:  96.4%

  Models used:   claude-haiku-4-5, claude-sonnet-4-5

  Per-Model Performance:
    claude-sonnet-4-5:
      Calls:         20   Success rate: 100.0%
      Avg cost:      $0.0045  Avg latency: 1420ms
    claude-haiku-4-5:
      Calls:         8    Success rate: 87.5%
      Avg cost:      $0.0008  Avg latency: 680ms
```

---

### `attune telemetry routing-check`

Get tier upgrade recommendations based on recent routing performance. Tells
you if a stage is consistently failing at a lower tier and should be promoted.

```bash
attune telemetry routing-check
attune telemetry routing-check --workflow code-review --days 30
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--workflow` | `-w` | all | Limit analysis to one workflow |
| `--days` | `-d` | 7 | Number of days to analyze |

---

### `attune telemetry models`

Show model performance broken down by provider.

```bash
attune telemetry models
attune telemetry models --days 14
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--days` | `-d` | 7 | Number of days |
| `--min-calls` | - | 5 | Minimum call count to include in report |

---

### `attune telemetry agents`

Show active agents and their current coordination status.

```bash
attune telemetry agents
```

Displays agent IDs, session type, access tier, capabilities, and last
heartbeat time for all agents currently registered in the coordination layer.

---

### `attune telemetry signals`

Show coordination signals for a specific agent — messages sent and received
across the multi-agent coordination bus.

```bash
attune telemetry signals --agent <agent-id>
```

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--agent` | `-a` | Yes | Agent ID to inspect |

---

## Costs Commands

Track API spend and savings from intelligent tier routing.

### `attune costs`

Show a cost report for the recent period.

```bash
attune costs
attune costs --days 30
attune costs --workflow security-audit
attune costs --json
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--days` | `-d` | 7 | Number of days |
| `--workflow` | `-w` | all | Filter by workflow name |
| `--json` | - | false | Output raw JSON |

**Output:**
```
Cost Report — Last 7 days
--------------------------------------------------
  Requests:        142
  Actual cost:     $0.4821
  Baseline (Opus): $6.3900
  Saved:           $5.9079  (92.5%)
```

---

### `attune costs today`

Show costs incurred today only.

```bash
attune costs today
```

---

### `attune costs export`

Export cost data to a file.

```bash
attune costs export -o costs.json
attune costs export -o costs.csv --format csv --days 30
```

**Options:**

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--output` | `-o` | Yes | - | Output file path |
| `--format` | `-f` | No | json | Output format (`json` or `csv`) |
| `--days` | `-d` | No | 30 | Days of history to include |

---

### `attune costs reset`

Clear all stored cost data. Requires explicit confirmation.

```bash
attune costs reset --confirm
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--confirm` | Yes | Safety flag — must be passed to proceed |

---

## Provider Commands

### `attune provider show`

Display current LLM provider configuration.

```bash
attune provider show
```

**Output:**
```
🔧 Provider Configuration

------------------------------------------------------------
  Mode:            SINGLE
  Primary provider: anthropic
  Cost optimization: ✅ Enabled

  Available providers:
    [✓] anthropic
------------------------------------------------------------
```

---

### `attune provider set <name>`

Set the active LLM provider.

```bash
attune provider set anthropic
```

**Arguments:**

| Argument | Required | Choices | Description |
|----------|----------|---------|-------------|
| `name` | Yes | `anthropic` | Provider to use |

> **Note:** As of v5.0.0, Attune AI is Anthropic-only. Multi-provider support may return in future versions.

---

## Memory Commands

### `attune remember <text>`

Save a lesson learned for future workflow prompts.

```bash
# Save a project-local lesson
attune remember "Always run ruff before committing"

# Save a global lesson (applies to all projects)
attune remember --global "Prefer heapq.nlargest over sorted()[:N]"
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `text` | Yes | Lesson text to save |

**Options:**

| Option | Description |
|--------|-------------|
| `--global` | Save to global lessons (`~/.attune/lessons.md`) |

Lessons are stored as markdown in `.attune/lessons.md` (project)
or `~/.attune/lessons.md` (global) and automatically injected
into all workflow prompts. Token budget: 3,000 tokens max
(oldest lessons dropped first when over budget).

---

### `attune forget <identifier>`

Remove a lesson by line number or keyword.

```bash
# Remove by line number (from `attune lessons` output)
attune forget 3

# Remove by keyword match (first match removed)
attune forget "heapq"
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `identifier` | Yes | Line number or keyword |

---

### `attune lessons`

List all current lessons with line numbers.

```bash
# Show all lessons (project + global)
attune lessons

# Show only global lessons
attune lessons --global
```

**Options:**

| Option | Description |
|--------|-------------|
| `--global` | Show only global lessons |

**Output:**

```
Attune Lessons
==================================================
    1. [2026-02-23] Always run ruff before committing [project]
    2. [2026-02-20] Use _validate_file_path for writes [global]

2 lesson(s) total.
Remove with: attune forget <number> or attune forget <keyword>
```

---

### `attune memory capture <topic> <content>`

Save a topic to personal cross-session memory. The content is polished by
Claude before saving so it's clear and retrievable in future sessions.

```bash
attune memory capture "auth-pattern" "Always use _validate_file_path before writes"
attune memory capture "deploy-note" "Blue/green deploy requires 10-min warm-up" --project
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `topic` | Yes | Slug identifier — letters, digits, hyphens, max 50 chars |
| `content` | Yes | Raw content to capture and polish |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | - | Save to `.attune/memory/` (project-local) instead of global |
| `--no-polish` | - | Skip LLM polish step; save content verbatim |

---

### `attune memory recall <topic>`

Retrieve a saved memory topic.

```bash
attune memory recall auth-pattern
attune memory recall deploy-note --deep
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `topic` | Yes | Topic slug to retrieve |

**Options:**

| Option | Description |
|--------|-------------|
| `--deep` | Show full detail including related topics |

---

### `attune memory topics`

List all saved personal memory topics.

```bash
attune memory topics
```

---

### `attune memory forget-topic <topic>`

Delete a saved memory topic.

```bash
attune memory forget-topic old-pattern
```

---

## Utility Commands

### `attune doctor`

Run a comprehensive environment health check — verifies Python version, API
key, Redis connectivity, installed extras, and MCP server reachability.

```bash
attune doctor
```

**Output:**
```
🩺 Attune AI Environment Check

  ✅ Python 3.11.5 (≥ 3.10 required)
  ✅ ANTHROPIC_API_KEY set
  ✅ attune-ai 6.3.0 installed
  ✅ Redis reachable (localhost:6379)
  ⚠️  attune-rag not installed (pip install attune-ai[rag])
  ✅ MCP server importable

2 warnings. Run `attune features` to see optional extras.
```

---

### `attune features`

Show which optional feature groups are installed and which are available to
install, with the pip command for each.

```bash
attune features
```

**Output:**
```
📦 Attune AI Features

  ✅ core          Always available
  ✅ redis         attune-ai[redis] — Redis short-term memory
  ✅ developer     attune-ai[developer] — Development tools
  ❌ rag           attune-ai[rag] — RAG grounding (attune-rag)
  ❌ author        attune-ai[author] — Template authoring (attune-author)

Install missing extras: pip install attune-ai[rag]
```

---

### `attune setup`

Install the Attune slash commands to `~/.claude/commands/` so they are
available in every Claude Code session without a project-level plugin.

```bash
attune setup
```

Copies all commands from the installed `attune-ai` package into
`~/.claude/commands/`. Safe to re-run — existing commands are overwritten
with the latest version.

---

### `attune validate`

Validate your configuration and environment.

```bash
attune validate
```

**Checks:**

- Configuration file (attune.config.json/yml)
- API keys (ANTHROPIC_API_KEY)
- Workflow registration

**Output:**
```
🔍 Validating configuration...

  ✅ Config file: attune.config.yml
  ✅ Anthropic (Claude) API key set
  ✅ 12 workflows registered

------------------------------------------------------------

✅ Configuration is valid
```

---

### `attune version`

Show version information.

```bash
attune version
attune version --verbose
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Show Python version and platform |

---

## Global Options

These options work with any command:

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Enable debug logging |
| `--help` | `-h` | Show help for command |

---

## Verification Configuration

Workflows support optional post-execution verification that
runs real tools (pytest, ruff, mypy, etc.) to verify output.
Configure via the `verification:` section in your workflow
config.

### Example Configuration

```yaml
# In your workflow config (e.g. empathy.config.yml)
verification:
  enabled: true
  strategy: auto          # auto, run-tests, lint-check,
                          # type-check, build, custom-command,
                          # or none
  max_retries: 2          # Retry failed verification (default: 2)
  timeout_seconds: 300    # Per-attempt timeout (default: 300)
  fail_open: false        # If true, failed verification does
                          # not fail the workflow

  # Per-workflow overrides
  workflows:
    code-review:
      strategy: lint-check
    test-gen:
      strategy: run-tests
      max_retries: 3
    release-prep:
      strategy: build
      fail_open: true
    security-audit:
      strategy: custom-command
      command: "bandit -r src/ --severity-level medium"
```

### Built-in Strategies

| Strategy | Command | Default for |
|----------|---------|-------------|
| `run-tests` | `pytest tests/ -x --tb=short -q` | test-gen, refactor-plan |
| `lint-check` | `ruff check src/ --no-fix` | code-review, bug-predict, perf-audit, security-audit |
| `type-check` | `mypy src/ --ignore-missing-imports` | (manual) |
| `build` | `python -m build --no-isolation` | release-prep, secure-release |
| `custom-command` | (user-provided) | (manual) |
| `none` | (skipped) | doc-gen, research-synthesis |

### Auto Strategy

When `strategy: auto` is set (the default), the verification
module looks up the workflow name in the defaults table above.
If no default is mapped, verification is skipped.

### Verification Result

After verification runs, results are attached to
`workflow_result.metadata["verification"]`:

```json
{
  "passed": true,
  "strategy": "run-tests",
  "command": "pytest tests/ -x --tb=short -q",
  "attempts": 1,
  "duration_ms": 4230,
  "exit_code": 0
}
```

If verification fails and `fail_open` is `false` (the default),
the workflow is marked as failed with `error_type: "verification"`.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required) |
| `ATTUNE_CONFIG` | Custom config file path |
| `ATTUNE_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) |

---

## Exit Codes

`attune workflow run` follows a four-code contract:

| Code | Meaning |
|------|---------|
| 0 | Workflow ran and succeeded (also: interactive spend prompt declined) |
| 1 | Workflow ran and reported failure (`WorkflowResult.success` false) |
| 2 | Workflow raised an uncaught exception (traceback on stderr) |
| 3 | CLI-level stop — workflow not found, bad input JSON, bad path, no auth, or spend-gate block (the workflow never executed) |

Other subcommands use `0` for success and `1` for error.

---

## Related Tools

The framework includes additional CLI tools:

See [All CLI Entry Points](#all-cli-entry-points) below for the full list of available CLIs.

---

## Claude Code Integration

For interactive features, use Claude Code slash commands instead of CLI:

| Command | Purpose |
|---------|---------|
| `/dev` | Developer tools (debug, commit, PR) |
| `/testing` | Run tests, coverage, benchmarks |
| `/docs` | Documentation generation |
| `/release` | Release preparation |
| `/help` | Navigation hub overview |

These provide guided, conversational experiences built on top of the same framework.

---

## All CLI Entry Points

### Primary (Canonical)

| Command | Module | Description |
| --- | --- | --- |
| `attune <command>` | `attune.cli_minimal` | Automation-focused CLI (workflows, telemetry, provider, validate) |
| `python -m attune.cli` | `attune.cli` | Full-featured modular CLI (30+ commands) |

### Specialty CLIs

Invoked via `python -m <module>`:

| Command | Description |
| --- | --- |
| `python -m attune.models` | Model registry, auth setup, cost estimation |
| `python -m attune.test_generator` | AI-powered test generation and risk analysis |
| `python -m attune.socratic` | Socratic question-driven workflow selection |
| `python -m attune.telemetry` | Detailed telemetry and cost analysis |
| `python -m attune.project_index` | Project indexing and code scanning |

### Deprecated

| Entry Point | Replacement | Removal Target |
| --- | --- | --- |
| `attune.cli_unified` | `attune` (cli_minimal) | v5.0.0 |
