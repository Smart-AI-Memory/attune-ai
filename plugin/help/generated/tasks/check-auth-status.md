---
type: task
name: check-auth-status
tags: [cli, auth]
source: src/attune/cli_minimal.py
---

# Task: Check authentication status

Verify your subscription and authentication strategy. Shows which provider is active and whether your API key is configured correctly.

## Steps

1. **Check status**

   ```
   attune auth status
   ```

2. **View as JSON**
   For programmatic use.

   ```
   attune auth status --json
   ```

3. **Reconfigure if needed**

   ```
   attune auth setup
   ```


## Related Topics

_No related topics yet._
