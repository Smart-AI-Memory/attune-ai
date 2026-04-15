---
type: quickstart
feature: cli
depth: quickstart
generated_at: 2026-04-14T15:12:23.503665+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# Quickstart: cli

Run the Attune AI CLI to route commands to skills or natural language processing.

```bash
attune "show me today's costs"
```

## Prerequisites

- Attune AI installed locally
- Terminal or command prompt access

## Run your first command

1. **Check your installation** by viewing the CLI version:
   ```bash
   attune --version
   ```

2. **Try a natural language command** that gets routed automatically:
   ```bash
   attune "show me today's costs"
   ```

   You'll see output like:
   ```
   Today's costs: $2.45
   API calls: 23
   Tokens used: 1,247
   ```

3. **Use a direct skill command** with the slash syntax:
   ```bash
   attune /costs today
   ```

The CLI learns your preferences over time, so "costs" will route to the `/costs` skill automatically after a few uses.

## Next steps

Explore cost tracking commands with `attune help costs` to see detailed usage patterns and export options.
