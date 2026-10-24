# Agent work handoff

## Goal

Serve current Harness 1.5.1 Help and an organized historical archive through the existing website URLs.

## Acceptance criteria

Current guides name published 1.5.1; historical guides, screenshots and receipts retain their identities. Exact merged-source import, all current-head checks, protected integration and public route/browser verification must pass. Windows limits and qualification assertions remain unchanged.

## Scope and assumptions

- Branch: codex/harness-help-150; isolated publishing checkout.
- Canonical Help source: signed merged `5929c18c542a667a8a175a06b67ca5f2f571b73a`, tree `9f9d0dbb8c271934c1f66568d785a7efc44df91f`; equal to tested `84f70c86d5de13a4b82962268c81c50611cde775`.
- Runtime release: `ebb5b03b8a4398325df7ddabd28c08186451452e` / `v1.5.1`.
- Only Help publication is in scope. Other website changes remain separate.

## Current state

The export has 14 pages and 27 files, including an archive grouped by version and release state. All 26 generated files match the CI-verified candidate; only import source commit/URL changed for final merged provenance. The build and all payload hashes are unchanged. Original historical inputs and saved example wording remain intact.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Exact canonical projection | Node importer/check, CI ZIP digest and all output-byte comparisons | Pass; 27 files/14 pages |
| Current site and refusal guards | Full website tests | 79 passed |
| Repository process consistency | Read-only governance preflight | 87 passed; prepared-tree warnings retained |
| Build compatibility | TypeScript, scoped lint, actual Vercel build command | Pass |
| Existing public routes remain usable | Local Next production server, all file hashes, IDs, unknown route and historical redirect | 27 files match; 245 IDs preserved; 404/308 correct |
| Independent review | GPT-6 Astra review of original boundary and current publication/archive delta | Approved; no actionable findings; final provenance delta recorded before push |
| Hosted/deployed result | Current-head workflows and final production inspection | Pending |

## Next action

Wait all fresh current-head checks and review, then perform protected pinned integration. Verify signed main tree against the tested head and public Help/archive/goals delivery. Earlier heads, local success and historical walkthroughs do not qualify public deployment, model quality or full Windows parity.
