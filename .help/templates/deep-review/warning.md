---
type: warning
feature: deep-review
depth: warning
generated_at: 2026-04-14T14:54:28.135714+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review cautions

## What to watch for

The deep-review feature coordinates three specialized subagents (security, quality, and test gap reviewers) to analyze codebases. This multi-pass workflow can encounter specific failure modes that affect review completeness and accuracy.

## Risk areas

**Subagent coordination failures**: The workflow depends on all three subagents (`security-reviewer`, `quality-reviewer`, `test-gap-reviewer`) completing successfully before synthesis. If any subagent times out or returns malformed results, the consolidated report may be incomplete or skip entire review domains without clear indication.

**Large codebase memory exhaustion**: The workflow processes entire codebases through the Claude Agent SDK. Repositories with thousands of files or very large individual files can exceed token limits, causing truncated analysis where later files receive superficial review or are skipped entirely.

**Inconsistent severity scoring**: Each subagent applies its own severity scale, but the consolidated report assumes these scales are compatible. A "high" security finding and "high" quality finding may represent very different risk levels, leading to misleading prioritization in the final suggestions section.

**Path resolution errors**: The workflow expects valid file paths in the `{path}` parameter. Relative paths, symlinks, or paths to non-existent directories can cause the review to fail silently or produce reports for incorrect codebases.

## How to avoid problems

**Monitor subagent completion**: Check that all three specialized reviewers contribute to your consolidated report. Missing sections indicate subagent failures that need investigation.

**Scope reviews appropriately**: For large codebases, consider reviewing specific directories or file patterns rather than entire repositories to stay within Claude's context limits.

**Validate severity mappings**: When acting on consolidated findings, cross-reference the original subagent outputs to understand what "high severity" means in each domain before prioritizing fixes.

**Use absolute paths**: Always provide absolute paths to the codebase directory to avoid ambiguous path resolution that could target the wrong code.

**Test with representative codebases**: Before deploying changes to `DeepReviewAgentSDKWorkflow`, test with codebases similar in size and complexity to your production targets.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
