---
type: warning
feature: code-quality
depth: warning
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Code Quality cautions

## What to watch for

The code quality review orchestrates four specialized subagents that can produce conflicting or overwhelming results when not properly scoped.

## Risk areas

**Large repository scans overwhelm the output.** Running `/code-quality .` on a project with hundreds of files generates reports that are too long to parse effectively. The four subagents (security, quality, performance, and architecture reviewers) each contribute findings, creating noise that obscures critical issues.

**Subagent coordination can mask critical findings.** The `CodeReviewWorkflow` synthesizes results from all four reviewers into a single health score. High-severity security issues can get averaged out by clean style scores, giving a misleadingly positive overall rating.

**Deep reviews trigger expensive analysis.** The deep scan mode enables security and architecture analysis that examines cross-file dependencies and control flow. This can time out on complex codebases or consume significant compute resources when run repeatedly.

**False confidence from partial scans.** Quick scans only check style and formatting, but the unified health score doesn't clearly indicate this limited scope. You might ship code thinking it's been thoroughly reviewed when only cosmetic issues were checked.

## How to avoid problems

**Scope reviews to specific directories or files.** Use `/code-quality src/auth/` instead of `/code-quality .` to keep results focused and actionable.

**Check the depth setting matches your needs.** Reserve deep reviews for critical modules before release. Use standard depth for pull requests and quick scans only for pre-commit style checks.

**Read category breakdowns, not just the overall score.** A score of 85/100 could hide three critical security vulnerabilities if the style and performance scores are perfect.

**Test the workflow on small samples first.** Before running a full project scan, verify the setup works correctly on a single file: `/code-quality src/config.py`.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
