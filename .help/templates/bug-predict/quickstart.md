---
type: quickstart
feature: bug-predict
depth: quickstart
generated_at: 2026-04-14T14:48:44.718028+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Quickstart: bug predict

Run bug prediction analysis on your codebase from the command line:

```bash
python -m attune.workflows.bug_predict /path/to/your/code
```

## Run the workflow

1. **Execute the CLI command** on any directory containing source code:

   ```bash
   python -m attune.workflows.bug_predict ./src
   ```

2. **Review the generated report** that appears in your terminal. The output includes:
   - Overall risk score (0-100)
   - Predicted bugs organized by severity (HIGH, MEDIUM, LOW)
   - Prevention strategies with specific refactoring advice

   Expected output format:
   ```
   ## Summary
   Risk Score: 72/100
   High-risk areas detected in authentication and data validation modules.

   ## Bugs
   ### HIGH
   - src/auth.py:42 - Potential null pointer dereference in login validation

   ### MEDIUM
   - src/utils.py:15 - Complex conditional may hide edge cases

   ## Suggestions
   1. Add input validation to auth.py login methods
   2. Refactor nested conditionals in utils.py
   ```

3. **Use the workflow programmatically** if you need to integrate predictions into other tools:

   ```python
   from attune.workflows.bug_predict import BugPredictionWorkflow

   workflow = BugPredictionWorkflow()
   result = workflow.execute(path="./src")
   print(result.content)
   ```

**Next:** Review the HIGH severity predictions and implement the top prevention strategy from the suggestions section.
