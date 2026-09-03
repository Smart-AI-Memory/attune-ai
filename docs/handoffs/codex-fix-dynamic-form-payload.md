# Agent work handoff

## Goal

Make Fix and Spec intake CLI payloads render on strict native MCP form schemas by omitting absent optional field properties instead of serializing them as JSON `null`.

## Acceptance criteria

- The Fix intake CLI payload validates unchanged against the `elicitation_ask` form schema.
- The Spec intake CLI payload validates unchanged against the same schema.
- The real local renderer accepts the generated Fix payload and returns a successful widget render receipt.
- Focused lint and tests pass with no Anthropic spend.

## Scope and assumptions

- Branch/worktree: `codex/fix-dynamic-form-payload` at `/private/tmp/attune-ai-fix-dynamic-form`
- Provider/session: Codex local session, Thursday, September 3, 2026
- Assumptions:
  - This branch stays scoped to the dynamic-form payload fix and its direct receipts.
  - The original checkout at `/Users/patrickroebuck/attune-ai` keeps its unrelated untracked plan file and is not touched.

## Current state

- Status: ready for review, commit, push, and PR creation.
- Changed files:
  - `CHANGELOG.md`
  - `src/attune/elicitation/fix_intake.py`
  - `src/attune/elicitation/spec_intake.py`
  - `tests/unit/elicitation/test_fix_intake.py`
  - `tests/unit/elicitation/test_spec_intake.py`
- Decisions:
  - Preserve valid falsey values such as `required: false` and empty option lists; drop only keys whose value is `None`.
  - Keep the fix symmetric between Fix and Spec intake serialization paths.
  - Record the user-visible effect in `CHANGELOG.md` under `[Unreleased]`.
- Risks or open questions:
  - None known in the local branch after focused tests and renderer receipt.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Focused files are the only branch changes. | `git status --short && git diff --stat` | Pass: only the five intended files are modified before commit. |
| The branch is current with `origin/main`. | `git fetch origin` then `git rev-list --left-right --count origin/main...HEAD` | Pass: `0 0`. |
| The payload fix keeps the diff syntactically clean. | `git diff --check` | Pass. |
| Pinned formatting and lint are clean on the changed files. | `uv run --with pre-commit pre-commit run black --files CHANGELOG.md src/attune/elicitation/fix_intake.py src/attune/elicitation/spec_intake.py tests/unit/elicitation/test_fix_intake.py tests/unit/elicitation/test_spec_intake.py` and `uv run ruff check src/attune/elicitation/fix_intake.py src/attune/elicitation/spec_intake.py tests/unit/elicitation/test_fix_intake.py tests/unit/elicitation/test_spec_intake.py` | Pass. |
| The changed surfaces pass focused tests without Anthropic spend. | `unset ANTHROPIC_API_KEY` then `uv run --frozen pytest tests/unit/elicitation/test_fix_intake.py tests/unit/elicitation/test_spec_intake.py tests/unit/mcp/test_tool_schemas.py tests/unit/mcp/handlers/test_elicitation_ask.py tests/unit/scripts/test_sync_form_design_tokens.py -q` | Pass: `94 passed`. |
| Changed-code coverage stays above the project floor. | `uv run --frozen pytest tests/unit/elicitation/test_fix_intake.py tests/unit/elicitation/test_spec_intake.py --cov=attune.elicitation.fix_intake --cov=attune.elicitation.spec_intake --cov-report=term-missing --cov-fail-under=85 -q` | Pass: total `91.87%`, `fix_intake` `92.76%`, `spec_intake` `88.61%`. |
| The real renderer accepts the generated Fix payload unchanged. | Local MCP call to `elicitation_render_widget` using the generated fixed payload | Pass: `success=true`, `html_present=true`, fields `request`, `scope`, `probes`. |

## Next action

Stage the six branch files including this handoff, create the conventional commit, push `codex/fix-dynamic-form-payload`, and open the PR against `main`.
