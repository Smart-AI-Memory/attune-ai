# Implementation review, 2026-09-07 UTC

Author: Codex. Advisory reviewer: GPT-5.6 Sol, Codex subagent
`/root/review_prompt_refinement`. Receipt types: evidence-chain and behavioral
subprocess/suite checks. This was a real different-model subagent review, not a
Claude subscription or roundtable board run. Findings were checked centrally.

Initial scope: shared module, hook and registration, MCP adapter/schema, CLI,
planning source/mirror, tests, spec/guide, generated references and surrounding
path-validation/docs configuration. Later inventory changes were reviewed in
the follow-up. The initial report did not provide an exact file count; no
complete-file manifest is claimed.

## Dispositions

1. Navigation: reviewer initially claimed, verbatim, "The new public guide is
   absent from MkDocs navigation/exclusions, so strict docs CI should reject it
   as an orphan." Rejected as stated: `mkdocs.yml` configures
   `validation.nav.omitted_files: info`, so this is not evidence of a CI failure.
   Reviewer retracted that failure claim. The discoverability improvement was
   adopted: link the guide under How-to.
2. Repeated context: accepted. Removed duplicate host instructions from the
   per-turn hook and shortened the shared policy. Disabled delivery retains only
   a compact status and re-enable instructions. Tests bound active context to
   2,200 characters and disabled context to 650; there is still per-turn context
   cost, and no unverified once-per-session cache is introduced.
3. Model-call wording: accepted. The module makes no separate model/API request;
   asking questions can add ordinary host conversation turns. Docs now say so.
4. Unfamiliar preference data: accepted. Read and write require exactly a boolean
   `enabled` field. Extra keys produce visible degradation and are not overwritten.

## Follow-up scope and result

Nine files reviewed: `src/attune/prompt_refinement.py`,
`plugin/hooks/prompt_refinement.py`, `tests/unit/test_prompt_refinement.py`,
`docs/guides/prompt-refinement.md`, this spec's `requirements.md`, `mkdocs.yml`,
the host-surface-parity `parity-registry.json` and `producer_baseline.json`, and
`tests/unit/gates/test_surface_parity.py`. No remaining defect reported in that
bounded scope. Host-delivery/model-interpretation obligations remain pending.

The strongest counter-case remains context cost in already-clear conversations.
Shorter guidance mitigates that cost; it does not establish that refinement
improves outcomes or that every host follows MCP instructions.
