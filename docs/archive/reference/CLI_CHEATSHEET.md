---
description: Attune AI CLI Cheatsheet API reference: Quick reference for Attune AI commands. Full docs at [smartaimemory.com/framework-docs](http
---

# Attune AI CLI Cheatsheet

Quick reference for Attune AI commands. Full docs at [smartaimemory.com/framework-docs](https://www.smartaimemory.com/framework-docs/).

---

## Installation

```bash
pip install attune-ai
```

---

## Workflows

### Code Analysis (8 commands)

```bash
attune code-review .          # Multi-tier code analysis
attune security-audit .       # OWASP vulnerability scanning
attune test-gen .             # Generate tests for coverage gaps
attune bug-predict .          # Predict bugs from patterns
attune doc-gen .              # Generate documentation
attune perf-audit .           # Performance analysis
attune refactor-plan .        # Tech debt prioritization
attune dependency-check .     # Dependency audit
```

### Release (3 commands)

```bash
attune release-prep .         # Release readiness check
attune health-check .         # Project health check
attune test-coverage-boost .  # Boost test coverage
```

### Review (3 commands)

```bash
attune pr-review .            # Pull request review
attune pro-review .           # Professional code review
attune secure-release .       # Security-focused release
```

### Workflow Options

All workflows support:

```bash
attune <workflow> .           # Analyze current directory
attune <workflow> ./src       # Analyze specific path
attune <workflow> . --json    # JSON output for automation
```

---

## Reports

```bash
attune report                 # List available reports
attune report costs           # API cost tracking
attune report health          # Project health summary
attune report coverage        # Test coverage
attune report patterns        # Learned patterns
attune report metrics         # Project metrics
attune report telemetry       # LLM usage telemetry
```

---

## Code Inspection

```bash
attune scan .                 # Quick scan for issues
attune scan . --fix           # Auto-fix issues
attune scan . --staged        # Staged files only

attune inspect .              # Deep inspection
attune inspect . --format sarif   # SARIF for CI/CD

attune fix                    # Auto-fix lint/format
```

---

## Memory & Patterns

```bash
attune memory                 # Show status (default)
attune memory status          # Check Redis & patterns
attune memory start           # Start Redis server
attune memory stop            # Stop Redis
attune memory patterns        # List stored patterns
```

---

## Pattern Learning

```bash
attune learn                  # Learn from last 20 commits
attune learn --analyze 50     # Learn from last 50 commits
attune sync-claude            # Sync to Claude Code memory
```

---

## Tier Optimization

```bash
attune tier setup --show              # Show current config
attune tier setup --default CAPABLE   # Set default tier
attune tier setup --max-cost 0.50     # Set cost limit
attune tier setup --auto-escalate     # Enable auto-escalation

attune tier recommend "fix login bug"     # Get tier recommendation
attune tier recommend "refactor auth" --files auth.py,login.py
```

---

## Project Setup

```bash
attune init                   # Initialize new project
attune new --list             # List project templates
attune new minimal my-proj    # Create from template
attune onboard                # Interactive tutorial
attune explain <command>      # Explain a command
attune --version              # Show version
attune cheatsheet             # Show this reference
```

---

## CI/CD Integration

### GitHub Actions (SARIF)

```yaml
- name: Run Empathy Inspect
  run: attune inspect . --format sarif -o results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: attune-security
        name: Security audit
        entry: attune security-audit . --json
        language: system
        pass_filenames: false
```

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-...          # Claude API key (required)
OPENAI_API_KEY=sk-...             # OpenAI key (optional)
ATTUNE_CONFIG=./config.yaml       # Custom config path
REDIS_URL=redis://localhost:6379  # Redis connection
```

---

## Getting Help

```bash
attune --help                 # Main help
attune <command> --help       # Command-specific help
attune cheatsheet             # Quick reference
```

---

*Attune AI v4.6.6 | [GitHub](https://github.com/Smart-AI-Memory/attune-ai) | [Docs](https://www.smartaimemory.com/framework-docs/)*
