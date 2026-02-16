---
description: Attune AI CLI Guide API reference: The Attune AI includes a command-line tool for managing configurations, pattern libraries, m
---

# Attune AI CLI Guide

The Attune AI includes a command-line tool for managing configurations, pattern libraries, metrics, and state.

## Installation

```bash
pip install attune-ai
```

Or for development:

```bash
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd Empathy
pip install -e .
```

## Commands

### Version

Display version information:

```bash
attune-ai version
```

Output:
```
Attune AI v1.0.0
Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
```

---

### Init

Initialize a new project with an interactive configuration wizard:

```bash
# Interactive setup wizard (recommended)
attune init

# Non-interactive with defaults
attune init --non-interactive

# Overwrite existing config
attune init --force
```

The wizard guides you through:

- **Provider selection** - Anthropic, OpenAI, Google, Ollama, or Hybrid
- **API key configuration** - Environment variable or direct input
- **Model tier preferences** - Cheap, Capable, Premium model mapping
- **Compliance mode** - Standard or HIPAA

This creates `empathy.config.yml` with your settings.

---

### Validate

Validate a configuration file:

```bash
attune-ai validate empathy.config.yml
```

Output:
```
✓ Configuration valid: empathy.config.yml

  User ID: alice
  Target Level: 4
  Confidence Threshold: 0.8
  Persistence Backend: sqlite
  Metrics Enabled: True
```

---

### Info

Display framework information:

```bash
# With default config
attune-ai info

# With custom config
attune-ai info --config my-config.yml
```

Output:
```
=== Attune AI Info ===

Configuration:
  User ID: alice
  Target Level: 4
  Confidence Threshold: 0.8

Persistence:
  Backend: sqlite
  Path: ./empathy_data
  Enabled: True

Metrics:
  Enabled: True
  Path: ./metrics.db

Pattern Library:
  Enabled: True
  Pattern Sharing: True
  Confidence Threshold: 0.3
```

---

### Pattern Library Commands

#### List Patterns

List patterns in a pattern library:

```bash
# List patterns from JSON file
attune-ai patterns list patterns.json

# List patterns from SQLite database
attune-ai patterns list patterns.db --format sqlite
```

Output:
```
=== Pattern Library: patterns.json ===

Total patterns: 3
Total agents: 2

Patterns:

  [pat_001] Post-deployment documentation
    Agent: agent_1
    Type: sequential
    Confidence: 0.85
    Usage: 12
    Success Rate: 0.83

  [pat_002] Error recovery workflow
    Agent: agent_2
    Type: adaptive
    Confidence: 0.92
    Usage: 8
    Success Rate: 1.00
```

#### Export Patterns

Export patterns from one format to another:

```bash
# JSON to SQLite
attune-ai patterns export patterns.json patterns.db \
  --input-format json --output-format sqlite

# SQLite to JSON
attune-ai patterns export patterns.db patterns.json \
  --input-format sqlite --output-format json
```

Output:
```
✓ Loaded 3 patterns from patterns.json
✓ Saved 3 patterns to patterns.db
```

---

### Metrics Commands

#### Show Metrics

Display metrics for a specific user:

```bash
# Default metrics.db location
attune-ai metrics show alice

# Custom database location
attune-ai metrics show alice --db /path/to/metrics.db
```

Output:
```
=== Metrics for User: alice ===

Total Operations: 45
Success Rate: 88.9%
Average Response Time: 234 ms

First Use: 2025-10-01 14:23:45
Last Use: 2025-10-14 09:15:22

Empathy Level Usage:
  Level 1: 5 uses
  Level 2: 12 uses
  Level 3: 18 uses
  Level 4: 8 uses
  Level 5: 2 uses
```

---

### State Management Commands

#### List Saved States

List all saved user states:

```bash
# Default state directory
attune-ai state list

# Custom state directory
attune-ai state list --state-dir /path/to/states
```

Output:
```
=== Saved User States: ./empathy_state ===

Total users: 3

Users:
  - alice
  - bob
  - charlie
```

---

### Pattern Enhancement Commands (New in v2.1.4)

#### Resolve Investigating Patterns

Mark investigating bug patterns as resolved with root cause and fix:

```bash
# List all investigating bugs
attune patterns resolve

# Resolve a specific bug
attune patterns resolve bug_20251212_3c5b9951 \
  --root-cause "Missing null check on API response" \
  --fix "Added optional chaining operator" \
  --fix-code "data?.items ?? []" \
  --time 15 \
  --resolved-by "@developer"
```

Output:
```
✓ Resolved: bug_20251212_3c5b9951
✓ Regenerated patterns_summary.md
```

---

#### Pattern-Based Code Review

Review code against historical bug patterns:

```bash
# Review recent changes
attune review

# Review staged changes only
attune review --staged

# Review specific files
attune review src/api.py src/utils.py

# Set minimum severity threshold
attune review --severity warning

# Output as JSON
attune review --json
```

Output:
```
Code Review Results
========================================

⚠️  src/api.py:47
    Pattern: null_reference (bug_20250915_abc123)
    Risk: API response accessed without null check
    Historical: "API returned null instead of empty array"
    Suggestion: Add fallback - data?.items ?? []
    Confidence: 85%

Summary: 1 findings in 1 file(s)

Recommendations:
  • Fix 1 null_reference issue(s): Add null check
```

---

### Session Status Assistant (New in v2.1.5)

#### Check Project Status

Get a prioritized status report of your project when you return after a break:

```bash
# Show status (only if enough time has passed since last interaction)
attune status

# Force show status regardless of inactivity
attune status --force

# Show all items (no limit)
attune status --full

# Output as JSON
attune status --json

# Select an item to get its action prompt
attune status --select 1
```

Output:
```
📊 Project Status (6 items need attention)

🎉 Wins since last session:
   • 3 bugs resolved since last session

🔴 Security: 2 decisions pending review
   → Review XSS finding in auth.ts

🟡 Bugs: 3 investigating, 1 high-severity
   → Resolve null_reference in OrderList.tsx

🟢 Tech Debt: Stable (343 items, +0 this week)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] Fix high-severity bug  [2] Review security  [3] See full status
```

#### Priority System

Items are prioritized by severity:

| Priority | Category | Weight | Icon |
|----------|----------|--------|------|
| P0 | Security pending | 100 | 🔴 |
| P1 | Bugs high-severity | 80 | 🔴 |
| P2 | Bugs investigating | 60 | 🟡 |
| P3 | Tech debt increasing | 40 | 🟡 |
| P4 | Roadmap unchecked | 30 | 🔵 |
| P5 | Commits WIP/TODO | 20 | ⚪ |

#### Interactive Selection

Select an item number to get its full action prompt:

```bash
attune status --force --select 1
```

Output:
```
Action prompt for selection 1:

Continue investigating bug bug_20251212_97c0f72f:
TypeError: Cannot read property 'map' of undefined.
Use: attune patterns resolve bug_20251212_97c0f72f --root-cause '<cause>' --fix '<fix>'
```

#### Configuration

Set inactivity threshold (default: 60 minutes):

```bash
attune status --inactivity 30  # Show after 30 min of inactivity
```

---

### Code Health Assistant (New in v2.2.0)

#### Quick Health Check

Run fast health checks (lint, format, types):

```bash
attune health
```

Output:
```
📊 Code Health: Good (87/100)

🟢 Tests: 142 passed, 0 failed
🟡 Lint: 3 warnings
🟢 Types: No errors

[1] Fix 3 auto-fixable issues  [2] See details  [3] Full report
```

#### Comprehensive Health Check

Run all health checks including tests, security, and dependencies:

```bash
attune health --deep
```

#### Specific Check

Run only a specific category of health checks:

```bash
attune health --check lint
attune health --check format
attune health --check types
attune health --check tests
attune health --check security
attune health --check deps
```

#### Auto-Fix Issues

Preview what would be fixed:

```bash
attune health --fix --dry-run
```

Apply safe fixes automatically:

```bash
attune health --fix
```

Fix specific category:

```bash
attune health --fix --check lint
```

Interactive mode (prompt for non-safe fixes):

```bash
attune health --fix --interactive
```

#### Detail Levels

Summary view (default):
```bash
attune health
```

Details view (shows individual issues):
```bash
attune health --details
```

Full report:
```bash
attune health --full
```

#### Health Trends

View health trends over time:

```bash
attune health --trends 30  # Last 30 days
```

Output:
```
📈 Health Trends (30 days)

Average Score: 85/100
Trend: improving (+5)

Recent scores:
  2025-12-15: 87/100
  2025-12-14: 85/100
  2025-12-13: 82/100

🔥 Hotspots (files with recurring issues):
  src/api/client.py: 12 issues
  src/utils/helpers.py: 8 issues
```

#### JSON Output

Get machine-readable output:

```bash
attune health --json
```

---

## Usage Examples

### Development Workflow

```bash
# 1. Initialize project
attune-ai init --format yaml --output dev-config.yml

# 2. Edit dev-config.yml to customize settings
nano dev-config.yml

# 3. Validate configuration
attune-ai validate dev-config.yml

# 4. Check framework info
attune-ai info --config dev-config.yml

# 5. Run your application
python my_app.py

# 6. View metrics
attune-ai metrics show my_user

# 7. List saved states
attune-ai state list
```

### Production Deployment

```bash
# 1. Create production config
attune-ai init --format yaml --output prod-config.yml

# 2. Set production values via environment variables
export ATTUNE_USER_ID=prod_system
export ATTUNE_TARGET_LEVEL=5
export ATTUNE_PERSISTENCE_BACKEND=sqlite
export ATTUNE_METRICS_ENABLED=true

# 3. Validate combined config (file + env)
attune-ai validate prod-config.yml

# 4. Deploy application with config
python -m my_app --config prod-config.yml
```

### Pattern Library Management

```bash
# 1. Export patterns from development to JSON (for version control)
attune-ai patterns export dev_patterns.db dev_patterns.json \
  --input-format sqlite --output-format json

# 2. Commit to git
git add dev_patterns.json
git commit -m "Update pattern library"

# 3. On production, import patterns to SQLite
attune-ai patterns export dev_patterns.json prod_patterns.db \
  --input-format json --output-format sqlite

# 4. List patterns to verify
attune-ai patterns list prod_patterns.db --format sqlite
```

---

## Configuration File Reference

### YAML Example

```yaml
# Core settings
user_id: "alice"
target_level: 4
confidence_threshold: 0.8

# Trust settings
trust_building_rate: 0.05
trust_erosion_rate: 0.10

# Persistence
persistence_enabled: true
persistence_backend: "sqlite"
persistence_path: "./empathy_data"

# State management
state_persistence: true
state_path: "./empathy_state"

# Metrics
metrics_enabled: true
metrics_path: "./metrics.db"

# Logging
log_level: "INFO"
log_file: null
structured_logging: true

# Pattern library
pattern_library_enabled: true
pattern_sharing: true
pattern_confidence_threshold: 0.3

# Advanced
async_enabled: true
feedback_loop_monitoring: true
leverage_point_analysis: true
```

### JSON Example

```json
{
  "user_id": "alice",
  "target_level": 4,
  "confidence_threshold": 0.8,
  "persistence_enabled": true,
  "persistence_backend": "sqlite",
  "metrics_enabled": true,
  "pattern_library_enabled": true
}
```

### Environment Variables

All configuration fields can be set via environment variables with the `ATTUNE_` prefix (`EMPATHY_` prefix is also accepted for backward compatibility):

```bash
export ATTUNE_USER_ID=alice
export ATTUNE_TARGET_LEVEL=4
export ATTUNE_CONFIDENCE_THRESHOLD=0.8
export ATTUNE_PERSISTENCE_ENABLED=true
export ATTUNE_PERSISTENCE_BACKEND=sqlite
export ATTUNE_METRICS_ENABLED=true
```

Boolean values can be: `true`, `false`, `1`, `0`, `yes`, `no`

---

### Code Inspection Pipeline (New in v2.2.9)

The `attune-inspect` command provides a unified code inspection pipeline that combines multiple static analysis tools with cross-tool intelligence and pattern learning.

#### Basic Usage

```bash
# Inspect current directory
attune-inspect .

# Inspect specific path
attune-inspect ./src

# Quick mode (skip slow checks)
attune-inspect . --quick

# Verbose output
attune-inspect . --verbose
```

#### Output Formats

```bash
# Terminal output (default)
attune-inspect .

# JSON output
attune-inspect . --format json

# Markdown report
attune-inspect . --format markdown

# SARIF for GitHub Actions
attune-inspect . --format sarif

# HTML dashboard
attune-inspect . --format html

# Save report to file
attune-inspect . --format html --output report.html
```

**SARIF Integration (GitHub Actions example):**

SARIF is an industry standard supported by GitHub, GitLab, Azure DevOps, Bitbucket, and other CI/CD platforms. While optimized for GitHub, the same output works with any SARIF-compliant system.

```yaml
# .github/workflows/code-quality.yml
- name: Run Empathy Inspect
  run: attune-inspect . --format sarif --output results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

#### Target Modes

```bash
# Inspect all files (default)
attune-inspect .

# Only staged git changes
attune-inspect . --staged

# Only changed files vs HEAD
attune-inspect . --changed

# Exclude patterns
attune-inspect . --exclude "**/*.test.py" --exclude "**/migrations/*"
```

#### Auto-Fix

```bash
# Auto-fix safe issues (formatting, imports)
attune-inspect . --fix
```

#### Baseline & Suppression System

Manage false positives and known issues without cluttering your codebase:

```bash
# Initialize baseline file
attune-inspect . --baseline-init

# Run inspection (baseline filtering enabled by default)
attune-inspect .

# Show all findings including suppressed
attune-inspect . --no-baseline

# Clean up expired suppressions
attune-inspect . --baseline-cleanup
```

**Inline Suppressions:**

```python
# Suppress a specific rule on this line
eval(user_input)  # empathy:disable S307 reason="Input is validated"

# Suppress a rule on the next line
# empathy:disable-next-line W291 reason="Intentional whitespace"
result = calculate()

# Suppress a rule for entire file (must be in first 10 lines)
# empathy:disable-file B001 reason="Legacy code, refactoring planned"
```

**Baseline File (`.empathy-baseline.json`):**

```json
{
  "version": "1.0",
  "suppressions": {
    "project": [
      {
        "rule_code": "W291",
        "reason": "Formatting handled by pre-commit",
        "expires_at": "2025-03-01T00:00:00"
      }
    ],
    "files": {
      "src/legacy/old_module.py": [
        {
          "rule_code": "B001",
          "reason": "Legacy code, will refactor in Q2"
        }
      ]
    },
    "rules": {
      "E501": {
        "reason": "Line length handled by formatter"
      }
    }
  }
}
```

#### Parallel Execution

```bash
# Run Phase 1 tools in parallel (default)
attune-inspect .

# Disable parallel execution
attune-inspect . --no-parallel
```

#### Pattern Learning

```bash
# Enable pattern learning (default)
attune-inspect .

# Disable pattern learning
attune-inspect . --no-learning
```

#### Example Output

```
============================================================
  CODE INSPECTION REPORT
============================================================

  Health Score: 87/100 (B) - PASS

  CATEGORY SCORES:
    Lint               92/100  [PASS]
    Security           85/100  [PASS]
    Tests              88/100  [PASS]
    Debt               82/100  [WARN]
    Review             90/100  [PASS]

  FINDINGS: 12 total (3 suppressed)
    HIGH       1
    MEDIUM     8
    LOW        3

  BLOCKING ISSUES (1):
    [HIGH] src/api/client.py
      Potential SQL injection in query parameter...

  RECOMMENDATIONS:
    1. [HIGH] Address 1 high-severity findings
    2. [LOW] Auto-fix 5 issues with `attune-inspect --fix`

============================================================
  Duration: 2341ms
  Execution ID: insp_20251218_143022_a1b2c3d4
============================================================
```

#### Pipeline Phases

The inspection pipeline runs in 5 phases:

| Phase | Tools | Mode |
|-------|-------|------|
| 1. Static Analysis | Lint, Security, Tech Debt, Test Quality | Parallel |
| 2. Dynamic Analysis | Code Review, Advanced Debugging | Conditional |
| 3. Cross-Analysis | Correlate findings across tools | Sequential |
| 4. Learning | Extract patterns for future use | Optional |
| 5. Reporting | Generate unified report | Always |

#### Language-Aware Analysis

The code review automatically detects file languages and applies appropriate patterns:

| Extension | Language |
|-----------|----------|
| `.py` | Python |
| `.js`, `.jsx` | JavaScript |
| `.ts`, `.tsx` | TypeScript |
| `.rs` | Rust |
| `.go` | Go |
| `.java` | Java |
| `.rb` | Ruby |
| `.c`, `.h` | C |
| `.cpp`, `.hpp` | C++ |
| `.cs` | C# |
| `.swift` | Swift |
| `.php` | PHP |
| `.kt` | Kotlin |

---

### Bug Prediction Workflow (New in v3.5.5)

Predict bugs by analyzing code against learned patterns:

```bash
# Scan current directory
attune workflow run bug-predict

# Scan specific path
attune workflow run bug-predict --input '{"path":"./src"}'

# JSON output for CI/CD
attune workflow run bug-predict --json
```

#### Understanding Scanner Results

The bug prediction scanner detects patterns that historically correlate with bugs:

| Pattern | Severity | Description |
|---------|----------|-------------|
| `dangerous_eval` | High | Use of `eval()` or `exec()` on untrusted input |
| `broad_exception` | Medium | Bare `except:` or `except Exception:` that may mask errors |
| `incomplete_code` | Low | TODO/FIXME comments indicating unfinished work |

#### Smart False Positive Filtering

The scanner automatically filters acceptable patterns:

**Acceptable `broad_exception` uses (not flagged):**
- Version detection with fallback: `except: return "dev"`
- Config loading with defaults: `except: pass  # Fall back to default`
- Optional feature detection: `try: import optional_lib`
- Cleanup/teardown code: `__del__`, `__exit__`, `close()`
- Logging with re-raise: `except: log.error(...); raise`

**Acceptable `dangerous_eval` uses (not flagged):**
- Test fixtures: Code inside `write_text()` for testing
- Scanner test files: `test_bug_predict*`, `test_scanner*`
- Detection code: `if "eval(" in content`

#### Risk Scores

Files are scored 0-100% based on pattern severity and historical correlation:

| Score | Risk Level | Action |
|-------|------------|--------|
| 80-100% | 🔴 HIGH | Immediate attention required |
| 50-79% | 🟠 MODERATE | Review before release |
| 30-49% | 🟡 LOW | Address when convenient |
| 0-29% | 🟢 MINIMAL | No action needed |

#### Customizing Scanner Behavior

See `empathy.config.yml` for customizable exclusions:

```yaml
bug_predict:
  exclude_files:
    - "**/test_*.py"
    - "**/fixtures/**"
  acceptable_exception_contexts:
    - version
    - config
    - cleanup
```

---

### Claude Code Integration (New in v2.3.0)

Sync learned patterns to Claude Code's native rules directory:

```bash
# One-time sync
attune-sync-claude

# Watch for changes and auto-sync
attune-sync-claude --watch

# Preview without writing
attune-sync-claude --dry-run

# Verbose output
attune-sync-claude --verbose
```

**Output structure:**

```
.claude/rules/attune/
├── bug-patterns.md          # From patterns/debugging/
├── security-decisions.md    # From patterns/security/
├── tech-debt-hotspots.md    # From patterns/tech_debt/
└── coding-patterns.md       # From patterns/inspection/
```

Claude Code automatically loads these rules at session start, giving it access to your team's bug history, security decisions, and coding patterns.

---

## Quick Reference (Cheatsheet)

### Core Commands

```bash
# Code Health
attune health                    # Quick health check
attune health --deep             # Comprehensive analysis
attune health --fix              # Auto-fix safe issues
attune health --check lint       # Run specific check

# Code Review
attune review                    # Review recent changes
attune review --staged           # Staged changes only

# Code Inspection
attune-inspect .                 # Inspect current directory
attune-inspect . --fix           # Auto-fix formatting/imports
attune-inspect . --format sarif  # SARIF for GitHub Actions
attune-inspect . --format html   # HTML dashboard
```

### Memory & Patterns

```bash
# Memory Control Panel
attune-memory serve              # Start Redis + API (recommended)
attune-memory status             # Show memory status
attune-memory patterns           # List stored patterns

# Pattern Management
attune patterns list             # List patterns
attune patterns resolve <id>     # Mark bug as resolved

# Claude Code Sync
attune-sync-claude               # Sync to .claude/rules/attune/
attune-sync-claude --watch       # Auto-sync on changes
```

### Quick Workflows

```bash
# Morning check
attune health --deep && attune status

# Before commit
attune review --staged && attune-inspect . --staged --quick

# Fix everything
attune health --fix && attune-inspect . --fix

# Sync to Claude Code
attune-sync-claude --verbose
```

### CI/CD Integration

**GitHub Actions (SARIF):**
```yaml
- name: Run Empathy Inspect
  run: attune-inspect . --format sarif -o results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

**Pre-commit Hook:**
```yaml
repos:
  - repo: local
    hooks:
      - id: empathy-review
        name: Pattern-based review
        entry: attune review --staged --severity error
        language: system
        pass_filenames: false
```

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-...          # Claude API key
ATTUNE_CONFIG=./config.yaml       # Custom config path
ATTUNE_LOG_LEVEL=DEBUG            # Logging level
REDIS_URL=redis://localhost:6379  # Redis connection
```

---

## Getting Help

For more information on any command:

```bash
attune --help
attune <command> --help
attune-inspect --help
attune-memory --help
attune-sync-claude --help
```

For bugs and feature requests, visit:
https://github.com/Smart-AI-Memory/attune-ai/issues
