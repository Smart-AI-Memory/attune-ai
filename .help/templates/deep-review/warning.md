---
type: warning
name: deep-review-warning
feature: deep-review
depth: warning
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 0166eb83fb8436c203cdd073439a7339645f40e53cdfe39db4fbed0559eac81d
status: generated
---

# Deep Review Cautions

`deep_review` coordinates three specialized subagents — `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` — and synthesizes their findings into a single report. Because results depend on all three subagents completing successfully, a failure or misconfiguration in any one of them affects the entire consolidated output.

## Risk areas

### Incomplete synthesis when a subagent produces no findings

`DeepReviewAgentSDKWorkflow.execute()` relies on each subagent reporting independently before the orchestrator synthesizes results. If a subagent returns empty output — due to a scoped `path` argument that excludes relevant files, a timeout, or a permissions issue — the consolidated report silently omits that domain. A clean **Security** or **Test Gaps** section does not necessarily mean no issues exist; it may mean the subagent had nothing to analyze.

**Mitigation:** Verify that the `path` you pass to `deep_review(path="...")` covers the full scope you intend to review. Spot-check individual section counts in the **Summary** (overall findings by severity) against what you expect for your codebase size.

### Private subagent names and prompt templates can change without notice

The subagent identifiers (`security-reviewer`, `quality-reviewer`, `test-gap-reviewer`) and the task prompt are defined in module-level private constants (`_SUBAGENT_NAMES`, `_TASK_PROMPT_TEMPLATE`). Any code that references or patches these constants directly — for example, to override prompts or redirect subagents — will break silently when those constants change, because private names carry no stability guarantee.

**Mitigation:** Interact with `deep_review` exclusively through its public interface: `DeepReviewAgentSDKWorkflow.execute(**kwargs)` and the `deep_review(path="...")` tool call. Do not import or monkey-patch `_SUBAGENT_NAMES` or `_TASK_PROMPT_TEMPLATE`.

### Path scoping produces misleading scores

The workflow reports an overall code health score (0–100) calibrated to the files it actually analyzed. Passing a narrow `path` — a single subdirectory or file — produces a score and finding counts that reflect only that scope. Treating a partial-scope score as a whole-project health indicator leads to incorrect conclusions.

**Mitigation:** When you need a whole-project assessment, pass the repository root as `path`. When you intentionally scope to a subdirectory, note the scope explicitly when sharing or acting on the report.

## How to avoid problems

1. **Use the public API only.** `DeepReviewAgentSDKWorkflow.execute(**kwargs)` is the supported entry point. Subclassing `DeepReviewAgentSDKWorkflow` or overriding internal methods may appear to work but will break as the orchestration logic evolves.

2. **Treat an empty section as unverified, not clear.** The consolidated report separates findings into **Security**, **Quality**, and **Test Gaps** sections. An empty section means that subagent reported nothing for the given path — not that the code is free of issues in that domain.

3. **Check file paths and line numbers in findings.** The orchestrator's system prompt instructs subagents to cite file paths and line numbers. If a finding lacks that detail, treat it as lower confidence and verify manually before acting on it.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
