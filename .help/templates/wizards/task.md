---
feature: wizards
depth: task
generated_at: 2026-04-06T04:36:11.991531+00:00
source_hash: fad88261e0dbe9f9ea2e6e67da0819f247e4b1e816131c4c3128024aadbdd904
status: generated
---

# Work with wizards

Use wizards when you need to create or customize XML-enhanced interactive workflows that guide users through multi-step processes like debugging, refactoring, release preparation, security audits, or test generation.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/wizards/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what wizards
   does today before making changes.
   The primary functions are:
   - `register_wizard()` in `src/attune/wizards/registry.py` — Register a wizard class.
   - `get_wizard()` in `src/attune/wizards/registry.py` — Get a wizard class by ID.
   - `list_wizards()` in `src/attune/wizards/registry.py` — List all registered wizard configs.
   - `save_custom_wizard()` in `src/attune/wizards/registry.py` — Save a custom wizard definition to YAML.
   - `delete_custom_wizard()` in `src/attune/wizards/registry.py` — Delete a custom wizard definition.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "wizards"`.

## Key files

- `src/attune/wizards/**`

## Common modifications

Functions you are most likely to modify:

- `register_wizard()` in `src/attune/wizards/registry.py`
- `get_wizard()` in `src/attune/wizards/registry.py`
- `list_wizards()` in `src/attune/wizards/registry.py`
- `save_custom_wizard()` in `src/attune/wizards/registry.py`
- `delete_custom_wizard()` in `src/attune/wizards/registry.py`
