---
type: tip
name: cli-tip
feature: cli
depth: tip
generated_at: 2026-06-24T04:24:53.876139+00:00
source_hash: bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4
status: generated
---

# The attune command-line interface and its natural-language router

## Notes & tips

- **`python -m attune.cli_minimal` is the fallback** when the `attune`
  script isn't on PATH.
- **`attune doctor` first.** It diagnoses most install/config issues.
- **`route_user_input` is async.** `is_slash_command` and
  `list_workflows` are sync.
- **`<group> --help`.** Every command group has its own help.
