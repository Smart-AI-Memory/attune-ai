---
description: CLI Minimal Refactor Plan: **Goal:** Reduce CLI from ~4,000 lines to ~500 lines by removing redundant commands covered by skills.
---

# CLI Minimal Refactor Plan

**Goal:** Reduce CLI from ~4,000 lines to ~500 lines by removing redundant commands covered by skills.

**Status:** Planning
**Created:** 2026-01-25

---

## Phase 1: Create New Minimal CLI (src/attune/cli_minimal.py)

### Commands to Keep

```python
# Core automation commands (~300 lines)
attune workflow list              # List available workflows
attune workflow run <name>        # Execute workflow (CI/CD)
attune workflow info <name>       # Show workflow details

# Telemetry commands (~100 lines)
attune telemetry show             # Display usage summary
attune telemetry savings          # Show cost savings
attune telemetry export           # Export to CSV/JSON

# Provider configuration (~50 lines)
attune provider show              # Current provider config
attune provider set <name>        # Set provider (anthropic, openai, hybrid)

# Utility commands (~50 lines)
attune validate                   # Validate configuration
attune version                    # Show version
```

### File Structure

```
src/attune/
├── cli_minimal.py          # NEW: ~500 lines
├── cli.py                  # DEPRECATED: Keep for backward compat, logs warning
├── cli_commands/
│   ├── __init__.py
│   ├── workflow.py         # workflow list/run/info
│   ├── telemetry.py        # telemetry show/savings/export
│   └── provider.py         # provider show/set
```

---

## Phase 2: Commands to Remove

### Replaced by `/dev` skill
- `cmd_review` - Code review
- `cmd_inspect` - Code inspection
- `cmd_explain` - Code explanation

### Replaced by `/testing` skill
- `cmd_tier_stats` - Test tier statistics
- `_cmd_test_status` - Test status
- `_cmd_file_test_status` - File test status
- `_cmd_file_test_dashboard` - Test dashboard

### Replaced by `/learning` skill
- `cmd_patterns_list` - Pattern listing
- `cmd_patterns_export` - Pattern export
- `cmd_patterns_resolve` - Pattern resolution

### Replaced by `/context` skill
- `cmd_status` - Project status
- `cmd_state_list` - State management

### Replaced by `/release` skill
- `cmd_orchestrate` - Orchestrated workflows

### Replaced by `/utilities` skill
- `cmd_init` - Project initialization
- `cmd_onboard` - Onboarding

### Replaced by `/help` skill
- `cmd_cheatsheet` - Command reference

### Remove entirely (unused/cruft)
- `cmd_achievements` - Gamification
- `cmd_tier_recommend` - Built into skills
- `cmd_frameworks` - Unused
- `cmd_sync_claude` - Internal tool
- `_cmd_agent_performance` - Unused

---

## Phase 3: Migration Path

### 3.1 Deprecation Warnings

```python
# In old cli.py commands
import warnings

def cmd_review(args):
    warnings.warn(
        "attune review is deprecated. Use '/dev' skill in Claude Code instead.",
        DeprecationWarning
    )
    # ... existing code for backward compat
```

### 3.2 Entry Points Update

```toml
# pyproject.toml
[project.scripts]
empathy = "attune.cli_minimal:main"
empathy-legacy = "attune.cli:main"  # Keep for migration
```

### 3.3 Documentation Updates

- Update README CLI section
- Update docs/cli-reference.md
- Add migration guide for CLI users

---

## Phase 4: Implementation Steps

### Step 1: Create cli_minimal.py skeleton
- [ ] Create file with argparse structure
- [ ] Implement `workflow` subcommand group
- [ ] Implement `telemetry` subcommand group
- [ ] Implement `provider` subcommand group
- [ ] Add `validate` and `version` commands

### Step 2: Extract reusable logic
- [ ] Move workflow execution logic to `cli_commands/workflow.py`
- [ ] Move telemetry logic to `cli_commands/telemetry.py`
- [ ] Move provider logic to `cli_commands/provider.py`

### Step 3: Add deprecation warnings to old CLI
- [ ] Add warnings to all deprecated commands
- [ ] Log usage of deprecated commands for analytics

### Step 4: Update entry points
- [ ] Change `empathy` to point to `cli_minimal`
- [ ] Add `empathy-legacy` for old CLI

### Step 5: Update tests
- [ ] Add tests for new minimal CLI
- [ ] Ensure old CLI tests still pass (deprecated but functional)

### Step 6: Update documentation
- [ ] README CLI section
- [ ] CLI reference docs
- [ ] Migration guide

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| CLI lines of code | ~4,000 | ~500 |
| Number of commands | ~40 | ~10 |
| Maintenance burden | High | Low |
| Feature parity | CLI + Skills overlap | Skills primary, CLI for automation |

---

## Timeline

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Create minimal CLI | 2-3 hours | High |
| Phase 2: Add deprecation warnings | 1 hour | High |
| Phase 3: Update entry points | 30 min | High |
| Phase 4: Documentation | 1 hour | Medium |
| Phase 5: Remove deprecated code | Future release | Low |

---

## Risks & Mitigation

### Risk: Breaking existing CI/CD pipelines
**Mitigation:**
- Keep `empathy-legacy` entry point
- Add clear deprecation warnings with migration path
- Document in CHANGELOG

### Risk: Users confused by reduced CLI
**Mitigation:**
- Clear error messages pointing to skills
- Migration guide in docs
- Announce in release notes

---

## Success Criteria

- [ ] `attune workflow run X` works for CI/CD
- [ ] `attune telemetry` works for reporting
- [ ] `attune provider` works for setup
- [ ] Old commands show deprecation warnings
- [ ] Documentation updated
- [ ] Tests pass
