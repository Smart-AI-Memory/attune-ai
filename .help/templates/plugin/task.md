---
feature: plugin
depth: task
generated_at: 2026-04-04T02:25:50.650167+00:00
source_hash: 91035b6062c35b9c5a02a46b975ee4d920fbf79b8c3cad1575709d661c5d2cde
status: generated
---

# Working with Plugin

## Overview

Common tasks for modifying or extending plugin.

## Key Files

- `plugin/**`


## Common Modifications

Functions you may need to modify:

- `main()` in `plugin/hooks/format_on_save.py`

- `main()` in `plugin/hooks/help_freshness_check.py`

- `main()` in `plugin/hooks/help_on_error.py`

- `main()` in `plugin/hooks/help_post_commit.py`

- `validate_bash_command()` in `plugin/hooks/security_guard.py`

- `validate_file_path()` in `plugin/hooks/security_guard.py`

- `main()` in `plugin/hooks/security_guard.py`

- `main()` in `plugin/hooks/welcome.py`
