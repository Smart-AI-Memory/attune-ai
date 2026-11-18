# Windows onboarding website handoff

## Goal

Give Windows learners explicit setup and shell commands for the reporting course, and describe the current 1.8.1 evidence without claiming full Windows qualification.

## Acceptance criteria

- Import Help and course files from the same exact reviewed Harness commit.
- Keep historical course archives unchanged and verify both current ZIPs.
- Render the setup, shell selection, copy controls and Windows evidence page locally.
- Retain missing browser-download, native-machine and learner evidence explicitly.
- Present the changes for review; publication requires a separate decision.

## Scope and assumptions

- Branch: `codex/windows-onboarding-review`, isolated worktree based on `73bc4e66c68696b333f6d43cac841f7044e46ec9`.
- Provider/session: Codex, configured independent read-only review lane.
- Source: Harness draft [PR #367](https://github.com/Smart-AI-Memory/attune-harness/pull/367), exact commit `12b03c18342bbd248ab06608e803bac40fb24032`.
- Published Harness 1.8.1 is the tested runtime. The revised course is a review candidate.

## Current state

- Status: ready for content review; source PR remains draft and production is unchanged.
- Changed files: exact Help/course exports, Windows status page and this handoff.
- Decisions: keep command-based extraction distinct from Edge/Explorer evidence; keep the separate diagnostic helper outside the public learner route. Use the selected Python executable directly, with no environment activation or execution-policy change.
- Risks: actual Windows Edge download and Explorer extraction remain unverified because guest UI automation did not reach those controls. Native x64 and unaided learner acceptance remain open. The diagnostic helper trust experiment does not establish that the collaborator's Prepare succeeds. Timeout, descendant-stop and recovery gaps remain outside this change.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Exact source imports | Both export guards check complete inventories and hashes | Passed: 28 Help payloads and 92 training payloads at the same source SHA |
| Current downloads | Compare committed practice and example ZIP bytes | Passed; practice `52ade57bf4784fb0d1dc1693ab1c8b1849495fd8d8c9ab5fa0af7fd292be4bdd`, example `f8420dee8eefb2413cb63a3a64b921e76099c798fb4fe7c2b91bbf27128fe352` |
| Website regressions | `ATTUNE_PYTHON` selects the existing project environment; `vitest run` | 15 files, 121 tests passed |
| Production bundle | `NEXT_TELEMETRY_DISABLED=1 next build` | Passed locally; no deployment or IndexNow notification |
| Collaboration preflight | Project environment runs `scripts/collaboration_preflight.py` | 87 passed, zero failures, two workspace-state warnings |
| Source prose delta | Course, shell-view and Help tests | 42 passed; printable and interactive wording reviewed independently |
| Browser UI | Local Chrome preview, shell selection persistence and copied command check | Passed on Mac; not a Windows browser claim |
| Windows archive handling | HTTPS download inside Windows, then each shell's `Expand-Archive` | Exact ZIP and all nine members matched in PowerShell 5.1 and 7; this method created no download-origin mark |
| Download-origin refusal | Synthetic Zone.Identifier, helper-only unblock, invalid-stage binding | Per-shell checks passed; script body never ran, policy and other files unchanged. Initial batch's missing PS7 test path remains retained separately |
| Full course workflow | Previously approved published-1.8.1 rehearsals using unchanged executable ZIP | Both shells passed two protected 77-test probes, exact HTML and preserved protected files; ARM64 Parallels with x64 Python under emulation |

Local receipts and screenshots are retained privately. They are not public attachments or evidence of recipient access. No new checkpoint was accepted and no new BUILD ran for this onboarding follow-up.

## Next action

Review the source and website candidates together. Before publication, settle source PR #367, update imports to its exact merged commit, verify the resulting checks and downloads, and obtain publication approval. Keep checkpoint and BUILD decisions separate. Record an actual Edge/Explorer attempt and native learner results before extending the corresponding compatibility claims.
