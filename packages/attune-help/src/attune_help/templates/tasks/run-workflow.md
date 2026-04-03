---
type: task
name: run-workflow
tags: [cli, workflow]
source: src/attune/cli_minimal.py
---

# Task: Run a workflow

Execute an AI-powered analysis workflow on your codebase. Workflows include security audits, code reviews, test generation, and more.

## Prerequisites

- ANTHROPIC_API_KEY set in environment

## Steps

1. **List available workflows**

   ```
   attune workflow list
   ```

2. **Run a workflow by name**
   Specify the workflow name and optional target path.

   ```
   attune workflow run security-audit --path "src/"
   ```

3. **View results**
   Results are displayed in the terminal with severity grouping.


## Related Topics

_No related topics yet._
