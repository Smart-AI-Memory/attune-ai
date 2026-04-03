---
type: task
name: browse-help-docs
tags: [cli, help]
source: src/attune/cli_commands/help_commands.py
---

# Task: Browse documentation templates

Use the built-in help system to browse error resolutions, tips, tool references, and warnings. Supports tag filtering and feedback.

## Steps

1. **List categories**

   ```
   attune help-docs
   ```

2. **Browse a category**

   ```
   attune help-docs errors
   ```

3. **Show a specific template**

   ```
   attune help-docs err-shadow-directories-at-repo-root-break-imports --deep
   ```

4. **Filter by tag**

   ```
   attune help-docs --tag security
   ```


## Related Topics

_No related topics yet._
