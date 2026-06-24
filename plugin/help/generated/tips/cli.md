---
name: cli
source: content/features/cli.md
tags:
- cli
- commands
type: tip
---

# The attune command-line interface and its natural-language router

## Notes & tips

- **`python -m attune.cli_minimal` is the fallback** when the `attune`
  script isn't on PATH.
- **`attune doctor` first.** It diagnoses most install/config issues.
- **`route_user_input` is async.** `is_slash_command` and
  `list_workflows` are sync.
- **`<group> --help`.** Every command group has its own help.
