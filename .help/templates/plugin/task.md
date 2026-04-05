---
feature: plugin
depth: task
generated_at: 2026-04-04T13:00:34.172237+00:00
source_hash: d77f635d1744204539648a98bb499be7b81f018d08c49a5f270bbf69bc0595a1
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
