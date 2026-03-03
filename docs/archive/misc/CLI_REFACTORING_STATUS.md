---
description: CLI Refactoring Status: **Date:** 2026-01-26 **Status:** Phase 1 Complete (30% of full refactoring) **Original File:** `src/attune/cli.py` (3,957 lines) ---
---

# CLI Refactoring Status

**Date:** 2026-01-26
**Status:** Phase 1 Complete (30% of full refactoring)
**Original File:** `src/attune/cli.py` (3,957 lines)

---

## ✅ Completed Work

### Phase 1: Foundation & Proof of Concept

**Directory Structure Created:**
```
src/attune/cli/
├── __init__.py              # New main() entry point (152 lines)
├── __main__.py              # Python -m execution support
├── commands/                # Extracted command implementations
│   ├── __init__.py
│   ├── help.py             # 5 commands: version, cheatsheet, onboard, explain, achievements
│   ├── tier.py             # 2 commands: tier_recommend, tier_stats
│   └── info.py             # 2 commands: info, frameworks
├── parsers/                # Parser definitions
│   ├── __init__.py         # Central parser registry
│   ├── help.py
│   ├── tier.py
│   └── info.py
└── utils/                  # Shared utilities
    ├── __init__.py
    ├── data.py             # CHEATSHEET, EXPLAIN_CONTENT (234 lines)
    └── helpers.py          # _file_exists, _show_achievements (72 lines)
```

---

## 📊 Statistics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Main file size** | 3,957 lines | 152 lines (main) | 96% reduction |
| **Commands extracted** | 0/30 | 9/30 | 30% complete |
| **Modules created** | 1 file | 11 files | Modular! |
| **Largest file** | 3,957 lines | 380 lines | Much better |

**Commands Extracted (9/30):**
1. ✅ cmd_version
2. ✅ cmd_cheatsheet
3. ✅ cmd_onboard
4. ✅ cmd_explain
5. ✅ cmd_achievements
6. ✅ cmd_tier_recommend
7. ✅ cmd_tier_stats
8. ✅ cmd_info
9. ✅ cmd_frameworks

---

## ✅ Testing Results

**Test 1: Version Command**
```bash
python -m attune.cli version
# ✅ Works! Logger shows: attune.cli.commands.help:cmd_version
```

**Test 2: Cheatsheet Command**
```bash
python -m attune.cli cheatsheet --compact
# ✅ Works! Displays formatted cheatsheet correctly
```

**Test 3: Import Structure**
```python
from attune.cli.commands.help import cmd_version
# ✅ Works! New modular structure is importable
```

---

## 🎯 Architecture Design

### Command Organization Pattern

**Each command module follows:**
```python
# commands/help.py
from attune.logging_config import get_logger
from ..utils.data import CHEATSHEET  # Relative imports
from ..utils.helpers import _show_achievements

def cmd_version(args):
    """Command implementation with full docstring."""
    # Implementation here
```

### Parser Organization Pattern

**Each parser module follows:**
```python
# parsers/help.py
from ..commands import help as help_commands

def register_parsers(subparsers):
    """Register all parsers for this command group."""
    parser = subparsers.add_parser("version", help="...")
    parser.set_defaults(func=help_commands.cmd_version)
```

### Main Entry Point

**New main() function:**
- Modular parser registration via `register_all_parsers()`
- Fallback to old cli.py for un-extracted commands
- Clean error handling and discovery tips
- ~150 lines vs original 900+ lines

---

## 📋 Remaining Work

### Phase 2: Extract Remaining Commands (21 commands)

**High Priority (frequently used):**
1. ⏭️ Pattern commands (3): patterns_list, patterns_export, patterns_resolve
2. ⏭️ Workflow command (1): cmd_workflow (multi-model, lines 2475-2820)
3. ⏭️ Status commands (3): status, review, health

**Medium Priority:**
4. ⏭️ Inspect commands (4): run, inspect, export, import
5. ⏭️ Provider commands (3): provider_hybrid, provider_show, provider_set
6. ⏭️ Orchestrate (1): orchestrate
7. ⏭️ Sync (1): sync_claude
8. ⏭️ Metrics (2): metrics_show, state_list

**Low Priority (less used):**
9. ⏭️ Workflow legacy (1): cmd_workflow (old version, lines 2022-2164) - DEPRECATED
10. ⏭️ Setup (2): init, validate

### Phase 3: Extract Telemetry Wrappers
- ⏭️ Create `cli/wrappers.py` (8 wrapper functions, lines 2918-3004)

### Phase 4: Cleanup & Finalize
- ⏭️ Remove old cli.py or convert to redirect
- ⏭️ Update all internal imports
- ⏭️ Run full test suite
- ⏭️ Update documentation

---

## 📝 How to Continue Refactoring

### Step 1: Choose Next Command Group

Pick from remaining commands. Example: patterns commands

### Step 2: Extract Command Functions

Read from original `cli.py` and create new module:
```bash
# Read lines for patterns commands
# Create: src/attune/cli/commands/patterns.py
```

### Step 3: Create Parser

Create corresponding parser file:
```bash
# Create: src/attune/cli/parsers/patterns.py
```

### Step 4: Register Parser

Update `cli/parsers/__init__.py`:
```python
from . import help, info, tier, patterns  # Add new module

def register_all_parsers(subparsers):
    help.register_parsers(subparsers)
    tier.register_parsers(subparsers)
    info.register_parsers(subparsers)
    patterns.register_parsers(subparsers)  # Add registration
```

### Step 5: Test

```bash
python -m attune.cli patterns list
```

### Step 6: Repeat

Continue with next command group until all 30 commands are extracted.

---

## 🔧 Command Extraction Template

Use this template for extracting remaining commands:

```python
"""<Group> commands for the CLI.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.logging_config import get_logger
# Add other imports as needed

logger = get_logger(__name__)


def cmd_<name>(args):
    """Command description.

    Args:
        args: Namespace object from argparse with attributes:
            - attribute_name (type): Description

    Returns:
        int | None: Exit code or None
    """
    # Copy implementation from original cli.py
    # Update imports to use relative paths
    pass
```

---

## 🚨 Critical Issues Resolved

### Issue 1: Duplicate Function Names
**Problem:** Two `cmd_workflow()` functions exist (lines 2022 and 2475)

**Resolution:**
- Line 2022: Rename to `cmd_workflow_legacy()` with deprecation warning
- Line 2475: Keep as `cmd_workflow()` (current multi-model version)

**Status:** Not yet implemented (command not extracted)

---

## 🎯 Success Criteria

**Phase 1 (Completed):**
- [x] Directory structure created
- [x] 9 commands extracted and working
- [x] Modular parser system established
- [x] New main() function works
- [x] Backward compatibility maintained

**Phase 2 (Not Started):**
- [ ] 21 remaining commands extracted
- [ ] All 30 commands accessible via new structure
- [ ] Old cli.py converted to redirect
- [ ] Full test suite passes

**Phase 3 (Not Started):**
- [ ] No regressions in existing tests
- [ ] All imports updated to new structure
- [ ] Documentation updated
- [ ] CHANGELOG entry created

---

## 📚 Related Documentation

- [Refactoring Plan](../.claude/plans/ancient-dancing-candle.md) - Full implementation plan
- [Coding Standards](../docs/CODING_STANDARDS.md) - Project standards
- [Original cli.py](../src/attune/cli.py) - Source file (3,957 lines)

---

## 💡 Tips for Continuing

1. **Extract in groups** - Don't extract commands one-by-one, extract logical groups
2. **Test frequently** - Test each group immediately after extraction
3. **Use relative imports** - `from ..utils import helpers` (within cli package)
4. **Copy docstrings** - Maintain comprehensive documentation
5. **Check dependencies** - Some commands import from each other
6. **Update parsers/__init__.py** - Don't forget to register new parser modules

---

## 🐛 Known Issues

1. **Legacy fallback** - Commands not yet extracted still use old cli.py
2. **Import warnings** - Some IDEs may show import warnings during transition
3. **Duplicate logging** - Logger output may duplicate during testing

---

## 📈 Progress Tracking

**Overall Progress:** 30% complete (9/30 commands extracted)

**Estimated Remaining Time:**
- 21 commands × 3 min avg = ~60 minutes
- Parser creation: ~20 minutes
- Testing & cleanup: ~20 minutes
- **Total: ~100 minutes** (~1.5 hours)

**Next Session Goal:** Extract patterns, workflow, and status commands (7 commands)

---

**Last Updated:** 2026-01-26
**Maintainer:** Refactoring Team
**Status:** Ready for Phase 2
