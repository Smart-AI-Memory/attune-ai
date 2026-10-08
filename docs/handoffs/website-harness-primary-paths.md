# Agent work handoff

## Goal

Make Harness the website's current focus, with useful engineering goals
and context-driven next-step review leading over command inventories.
Preserve existing technical references and the approved site theme.

## Acceptance criteria

- Shared navigation, footer and Docs point first to Harness.
- AI setup/workflow routes remain accessible as earlier-project references.
- Context copy distinguishes supported recall/checkpoints from proposed
  opportunity ranking and selection; it claims no whole-history access.
- Existing release marker and static documentation remain intact.
- Build, appropriate guards, independent review, rendered acceptance and
  exact-head CI pass before merge; production claims require live receipts.

## Scope and assumptions

- Branch: `website/harness-primary-paths`, isolated task clone.
- Provider/session: native Codex integration with gpt-6-astra advisory review.
- Base: live `ad1a55f457921b0aa542e76525f5d9d70b9badac`, PR2550 already merged.
- Authority: prepare the follow-up PR under the website update direction.
  Review and merge/deployment remain separate from PR preparation.
- Offers remain exploratory; no new commercial promises or collection.

## Current state

- Six website files are prepared and tested: `app/page.tsx`,
  `app/docs/page.tsx`, `app/how-it-works/page.tsx`,
  `components/Navigation.tsx`, `components/Footer.tsx`, `lib/metadata.ts`.
- Review report: [Harness-first review](../reports/website-harness-primary-paths-review-2026-10-08.md).
- Existing docs, CSS, API and generated Forms tokens are unchanged.
- Native planning/building remain experimental; Antigravity/native panel
  delivery unverified. Rich context mining GUI remains proposed.
- The previous PR's automation-only `when-green` job failed credential
  HTTP401; no credential repair or protection bypass is authorized here.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| The copy matches reviewed source | Six source SHA-256 values compared with built/rendered checkpoint | All six unchanged |
| Static docs and version contract preserved | Diff scope and exact marker inspection | Zero static doc changes; one exact marker |
| Production source compiles | Fresh Next Webpack build with TypeScript | Passed |
| Version/release contracts hold | Existing targeted release/version guards | 52 passed |
| Governance projections remain valid | Established-interpreter collaboration preflight | 87 passed |
| Rendered route/control behavior | Isolated browser, 10 home cases,72 route cases,18 links | Passed; zero page errors |
| Claims and links have source support | Different-model source/evidence-chain review | No actionable finding |
| Follow-up CI and production | Exact PR head/deployment observation | Pending; not claimed live |

## Next action

Inspect the follow-up PR and exact-head CI, then present the reviewable
change to Patrick/parent before merge. Do not merge PR2550 again. Retain
experimental product boundaries and current route references. Use existing
Git/Vercel integration without account, credential, protection or billing
changes. Delete this temporary handoff when its branch merges.
