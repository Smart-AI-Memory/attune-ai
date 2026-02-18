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

# Batch API (50% cost savings)
attune batch submit <file>             # Submit batch from JSON file
attune batch status <batch_id>        # Check batch status
attune batch results <id> <file>      # Download results
attune batch wait <id> <file>         # Wait until done, then download

# Telemetry
attune telemetry show                   # Display usage summary
attune telemetry savings                # Show cost savings
attune telemetry export -o <file>       # Export to CSV/JSON

# Provider
attune provider show                    # Show current provider
attune provider set <name>              # Set provider (anthropic)

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
| `--json` | `-j` | Output result as JSON |

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
```

---

## Batch Commands

Process up to 10,000 requests within 24 hours at **50% of standard
API pricing** via the Anthropic Message Batches API.

### `attune batch submit <file>`

Submit a batch of requests from a JSON file.

```bash
attune batch submit requests.json
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Path to JSON file with batch requests |

**Output:**

```
📤 Submitting batch from requests.json...
  Found 42 requests

✅ Batch submitted successfully!
   Batch ID: msgbatch_abc123

Monitor status with: attune batch status msgbatch_abc123
```

---

### `attune batch status <batch_id>`

Check the processing status of a submitted batch.

```bash
attune batch status msgbatch_abc123
attune batch status msgbatch_abc123 --json
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `batch_id` | Yes | Batch identifier (e.g., `msgbatch_abc123`) |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--json` | `-j` | Output raw JSON status |

---

### `attune batch results <batch_id> <output_file>`

Download results from a completed batch.

```bash
attune batch results msgbatch_abc123 output.json
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `batch_id` | Yes | Batch identifier |
| `output_file` | Yes | Path to save results JSON |

---

### `attune batch wait <batch_id> <output_file>`

Poll until the batch completes, then download results.

```bash
attune batch wait msgbatch_abc123 output.json
attune batch wait msgbatch_abc123 output.json --poll-interval 600
attune batch wait msgbatch_abc123 output.json --timeout 43200
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `batch_id` | Yes | Batch identifier |
| `output_file` | Yes | Path to save results JSON |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--poll-interval` | 300 | Seconds between status checks |
| `--timeout` | 86400 | Maximum wait time in seconds (24 hours) |

**Example workflow:**

```bash
# 1. Submit a batch
attune batch submit requests.json
#    Batch ID: msgbatch_abc123

# 2. Check status (or let wait handle it)
attune batch status msgbatch_abc123

# 3. Download when complete
attune batch results msgbatch_abc123 output.json

# — or — submit and wait in one step
attune batch wait msgbatch_abc123 output.json --poll-interval 300
```

> **Batch API limits:** up to 10,000 requests per batch, results
> within 24 hours, requires `ANTHROPIC_API_KEY`.

See [Batch API Guide](../BATCH_API_GUIDE.md) for request format and
best practices.

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

## Utility Commands

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

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required) |
| `ATTUNE_CONFIG` | Custom config file path |
| `ATTUNE_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, workflow failed, etc.) |

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
| `python -m attune.scaffolding` | Project scaffolding and boilerplate generation |
| `python -m attune.socratic` | Socratic question-driven workflow selection |
| `python -m attune.telemetry` | Detailed telemetry and cost analysis |
| `python -m attune.project_index` | Project indexing and code scanning |

### Deprecated

| Entry Point | Replacement | Removal Target |
| --- | --- | --- |
| `attune.cli_unified` | `attune` (cli_minimal) | v5.0.0 |
