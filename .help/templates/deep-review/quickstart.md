---
type: quickstart
name: deep-review-quickstart
feature: deep-review
depth: quickstart
generated_at: 2026-06-02T10:54:11.460701+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Quickstart: Deep review

Run a multi-pass code review that covers security, quality, and test gaps in one consolidated report.

```python
from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow

result = DeepReviewAgentSDKWorkflow().execute(path="src/")
print(result)
```

**Result:** A consolidated report with an overall health score (0–100), security findings, quality findings, test gap findings, and up to ten prioritized suggestions — each tied to a specific finding.

## Steps

**1. Import and instantiate**

```python
from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow

workflow = DeepReviewAgentSDKWorkflow()
```

**2. Run the review against your codebase**

Pass the path you want reviewed:

```python
result = workflow.execute(path="src/")
```

The workflow coordinates three specialized subagents — `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` — then synthesizes their findings.

**3. Read the report**

```python
print(result)
```

Your output will be structured as:

```
## Summary
Overall code health score (0-100) ...

## Security
...

## Quality
...

## Test Gaps
...

## Suggestions
...
```

If you see all five sections, the review completed successfully.

---

**Next:** Run `attune workflow run code-review --path "src/"` for a faster, single-pass quality check you can use on every commit.
