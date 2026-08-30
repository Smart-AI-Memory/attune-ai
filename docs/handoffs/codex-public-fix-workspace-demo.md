# Agent work handoff

## Goal

Publish a safe, browser-only Fix approval workspace on both
`attune-ai.dev` and `smartaimemory.com` without exposing an MCP,
workflow, subprocess, persistence, or file-mutation boundary.

## Acceptance criteria

- One canonical interaction source projects to both domains with only
  host-specific absolute asset roots adapted.
- Visitors can edit a contract, render its exact command and SHA-256
  approval hash, authorize it once, and observe replay rejection.
- The page states clearly that it is an educational simulation and
  never executes Fix.
- Both sites expose a discoverable route and include it in their
  sitemap.
- Projection drift, contract construction, hash generation, and state
  transitions have automated coverage.
- Website typecheck/build and a real interactive browser pass.

## Scope and assumptions

- Branch/worktree: `codex/public-fix-workspace-demo` at
  `Documents/Codex/2026-08-29/are/work/attune-ai-public-fix`
- Provider/session: Codex; Patrick is chair and has approved autonomous
  implementation and publication under the standing handoff.
- Assumptions: `attune-ai.dev/fix-workspace` is the canonical standalone
  sandbox; `smartaimemory.com/fix-workspace` supplies the branded host
  page around the same projected asset.

## Current state

- Status: implementation, primary verification, advisory review, and
  remediation re-review complete; commit and PR publication remain
- Changed files: canonical static sandbox under
  `attune-ai-dev/fix-workspace/`, host-adapted website projection,
  Next route/embed, navigation/sitemaps/CSP, projection script, tests,
  and this handoff
- Decisions: no server/API route; exact production contract vocabulary
  and canonical JSON ordering are reproduced in browser-only code.
- Risks or open questions: final marketing placement may need chair copy
  tuning after the live preview.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Isolated current branch | `python scripts/collaboration_preflight.py` | pass; dirty main preserved |
| No overlapping PR | `gh pr list --state open ...` | pass; zero open PRs |
| Both hosts are distinct surfaces | live opens of both domains + repo inspection | pass |
| Canonical hash matches production | JS fixture vs Python `StructuredFixPreview.contract_hash()` | pass: `487ff289…b9e5` |
| Browser state transitions | live edit → re-render → approve → replay | pass; revisions 0/1/2, new hash, execution false, replay rejected |
| Website tests | `ATTUNE_PYTHON=… npm test` | pass: 32/32 |
| Website claim guards | verified Python env + `test_website_version_accuracy.py` | pass: 16/16 |
| Type/lint | `npx tsc --noEmit`; scoped ESLint | pass |
| Production build | `VERCEL=1 npx next build --webpack` | pass: 111 static pages; `/fix-workspace` prerendered |
| Turbopack local build | `VERCEL=1 npx next build` | host-blocked: CSS worker cannot bind IPC port; Vercel PR check remains authoritative |
| Advisory primary lane | Antigravity staged review | clean on 12 sent files; 4 omissions re-laned |
| Advisory scoped lane | Antigravity review of 4 omitted files | 3 findings verified: clean-URL asset bug real/medium; form names real/low and hardened; `_top` external navigation rejected as intentional iframe escape |
| Advisory remediation lane | Antigravity scoped review of 4 changed files | clean; 4 sent, 0 omitted, 0 findings |

## Next action

Create a signed commit, push the branch, and open the PR.
