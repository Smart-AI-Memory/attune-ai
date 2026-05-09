---
type: error
name: two-codeql-setups-can-coexist-in-one-repo-and-deadlock-merges
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Error: Two CodeQL setups can coexist in one repo and
  deadlock merges silently

## Signature

))'` shows both and their `state`. Attempted fix that DID NOT work: `gh workflow enable codeql.yml` + `gh workflow run codeql.yml --ref <branch>` — the re-enabled custom workflow DOES run, but its SARIF upload step fails with `##[error]Code Scanning could not process the submitted SARIF file: CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled`. The two setups conflict at the code-scanning API layer: default setup

## Root Cause

`attune-ai` had BOTH `.github/workflows/codeql.yml` (custom, with `pull_request:` trigger) AND GitHub's default CodeQL setup (`"schedule":"weekly"`, no PR trigger). The custom workflow was disabled manually at some point (probably when default setup was enabled), leaving only the weekly cron. Required merge gate was `Analyze (python)` — which ONLY the custom workflow produces on PRs. Result: PR #173 sat with 24 passing checks + `Analyze (python)` silently absent from the rollup, and admin-merge couldn't bypass because the gate was declared "expected" but missing. Diagnosis commands: `gh api repos/X/code-scanning/default-setup --jq .schedule` (weekly/quarterly/etc.) + `gh api repos/X/actions/workflows --jq '.workflows[] | select(.path | contains("codeql"))'` shows both and their `state`. Attempted fix that DID NOT work: `gh workflow enable codeql.yml` + `gh workflow run codeql.yml --ref <branch>` — the re-enabled custom workflow DOES run, but its SARIF upload step fails with `##[error]Code Scanning could not process the submitted SARIF file: CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled`. The two setups conflict at the code-scanning API layer: default setup "owns" SARIF uploads for the repo, and any competing analysis gets rejected. Real fix is structural: pick ONE CodeQL setup and stick with it. Either (a) drop the custom workflow and remove the required-check rule (default setup is simpler, weekly scans, no merge gate); or (b) disable default setup via `gh api repos/X/code-scanning/default-setup -X PATCH -f state=not-configured` and keep the custom workflow with its PR-level gate. **Resolution in attune-ai (post-v6.3.0):** option (a) — `.github/workflows/codeql.yml` deleted, `Analyze (python)` removed from required_status_checks, default setup remains the sole code-scanning path. The on-demand advice above is retained for OTHER repos that haven't yet reconciled the conflict, since the diagnostic sequence (SARIF error message, surprised-empty rollup) is the same everywhere.

## Resolution

1. `attune-ai` had BOTH `.github/workflows/codeql.yml` (custom, with `pull_request:` trigger) AND GitHub's default CodeQL setup (`"schedule":"weekly"`, no PR trigger)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Two CodeQL setups can coexist in one repo and
  deadlock merges silently
- Task: Update test mocks and assertions
