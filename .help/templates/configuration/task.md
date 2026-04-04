---
feature: configuration
depth: task
generated_at: 2026-04-04T02:25:50.678421+00:00
source_hash: 6be742830b8d72209e378e70916c649d55dd40a3afdfa434cf328395a1bc4ee3
status: generated
---

# Working with Configuration

## Overview

Common tasks for modifying or extending configuration.

## Key Files

- `src/attune/config/**`


## Common Modifications

Functions you may need to modify:

- `get_attune_env()` in `src/attune/config/env_compat.py`

- `iter_attune_env_prefix()` in `src/attune/config/env_compat.py`

- `get_loader()` in `src/attune/config/loader.py`

- `load_unified_config()` in `src/attune/config/loader.py`

- `save_unified_config()` in `src/attune/config/loader.py`

- `validate_config()` in `src/attune/config/validation.py`

- `get_config()` in `src/attune/config/xml_config.py`

- `set_config()` in `src/attune/config/xml_config.py`
