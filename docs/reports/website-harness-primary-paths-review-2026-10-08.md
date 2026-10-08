# Harness-first website follow-up review — 8 October 2026

The shared navigation, documentation entry point and homepage now make
Attune Harness the current focus. Goals and engineering benefits lead;
command references support the claims. Attune AI remains available as an
earlier-project reference, with its existing technical documentation and
routes retained. This positioning does not establish technical deprecation
or full replacement.

Scope: six website files on `website/harness-primary-paths`, based on
published commit `ad1a55f457921b0aa542e76525f5d9d70b9badac`. Supporting review
and branch-handoff documents accompany the change. No theme, static
documentation, Forms token, API or release-tool changes are included.

## Claims and boundaries

- Published Harness 1.3.0 source supports bounded recall against configured
  sources and retained opportunity-review checkpoints. The richer
  opportunity-ranking and selection journey remains proposed. The new copy
  does not claim automatic access to whole agent histories or a shipped
  mining GUI.
- Native planning and building remain experimental. Claude Code and Codex
  setup is documented; Antigravity integration and native MCP panel delivery
  remain unverified in this review. Intent approval and paid execution
  permission remain separate.
- The exporter example describes one documented comparison: real CLI checks
  exposed three defects that direct serializer checks missed. It establishes
  neither general model reliability nor productivity.
- Collaborate remains primary; pilot and sponsorship paths remain equally
  secondary, exploratory offers. No pricing, sponsor benefits, demand,
  measured commercial outcomes or delivery guarantees are added.

Sources: [1.3.0 package and qualification guide](https://pypi.org/project/attune-harness/1.3.0/),
[CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md),
[migration boundaries](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/migration-from-attune-ai.md),
[bounded exporter comparison](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/plan-build-native-results.md),
[proposed opportunity journey](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/specs/task-opportunities/journey.md).

## Independent review and integration evidence

A gpt-6-astra native advisory lane inspected all six changed website files,
the release source and tests, the evidence chain and literal internal link
targets. No actionable source issue was found. It confirmed the one exact
`<span>v16.4.0</span>` marker and zero static documentation changes. Its
collaboration preflight passed 87 governance tests. It inspected Harness
tests without claiming a fresh Harness test run. No external review
executor, board thread or countersigned receipt is claimed.

The integrating session completed a fresh production Webpack build with
TypeScript, 52 existing release/version guards and pinned hooks. Built-site
browser acceptance passed 10 homepage viewport/theme cases, 72
representative route cases and 18 internal links with zero page errors.
Checks covered desktop/mobile navigation, light/dark themes, keyboard
disclosures/focus and native Material documentation theme/drawer behavior.
All six website file hashes were subsequently verified unchanged against
the source checkpoint associated with those receipts.

The existing theme update from PR2550 is already live and independently
verified against its exact production commit. This follow-up's PR CI,
merge and production deployment are separate, pending gates. No form
submission, real-device/Safari/screen-reader or contact delivery test was
performed. A passing check establishes only what it tested.
