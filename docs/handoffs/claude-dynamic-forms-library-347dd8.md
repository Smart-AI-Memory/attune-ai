# Agent work handoff

## Goal

Extract the elicitation subsystem into a standalone, reusable
`attune-forms` PyPI package (own repo), with attune-ai as its first
consumer — chair-ruled 2026-08-12 via decision form (distribution:
separate PyPI package/own repo; name: `attune_forms`; artifact tier:
direct extraction PR).

## Acceptance criteria

- `~/attune-forms` repo: full library (models, bridge, widget, theme,
  elicitation_schema, template_store, reference_form, intake_template
  with host seams, form_events), tests green, wheel builds.
- attune-ai: consumes `attune-forms`; legacy import paths
  (`attune.elicitation.*`, form classes in `meta_workflows.models`,
  `attune.telemetry.form_events`) stay working via `sys.modules`
  aliases; full unit suite green.
- Publish sequencing respected: the attune-ai PR merges only AFTER
  `attune-forms` 0.1.0 is on PyPI (a published wheel cannot carry a
  git dependency).

## Scope and assumptions

- Branch/worktree: `claude/dynamic-forms-library-347dd8` at
  `.claude/worktrees/reverent-colden-2f8e11`; new repo at
  `/Users/patrickroebuck/attune-forms` (local commit `fdf4bb9`, not
  yet pushed — no GitHub repo exists yet).
- Provider/session: Claude (lead), 2026-08-12.
- Assumptions: attune-specific intakes (fix, spec, 17 workflow
  templates) STAY in attune-ai, registered through the library's
  `WORKFLOW_SCHEMA_RESOLVER` + `TEMPLATE_LOADERS` seams. Display
  kernels (`attune/widgets/chartkit`) are out of scope (different
  substrate).

## Current state

- Status: both sides code-complete and locally green; blocked on the
  chair gates (public repo push, PyPI publish).
- Changed files (attune-ai): `src/attune/elicitation/__init__.py`
  (alias shim + host seams), deleted `bridge.py` / `widget.py` /
  `theme.py` / `elicitation_schema.py` / `template_store.py` /
  `reference_form.py` / `intake_template.py` / `templates/` /
  `telemetry/form_events.py`, `meta_workflows/models.py` (form classes
  re-imported from `attune_forms.models`), `telemetry/__init__.py`
  (form_events alias), `pyproject.toml` (`attune-forms>=0.1.0,<0.2.0`),
  `tests/unit/gates/test_path_validation_gate.py` (allowlist shrink:
  2 stale entries), `CHANGELOG.md`.
- Decisions: `sys.modules` aliasing (the `os.path` pattern) chosen over
  re-export shims so monkeypatching and class identity are preserved;
  library seams are plain module attributes (no framework), per
  simpler-is-better.
- Risks or open questions: attune-ai CI cannot go green until
  `attune-forms` is installable from PyPI; local dev needs
  `uv pip install -e ~/attune-forms` until then. The `attune-forms`
  repo needs GH Actions + (optionally) trusted publishing configured
  by the chair.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Library standalone-correct | `~/attune-forms: .venv/bin/python -m pytest -q` (no attune-ai installed) | 358 passed |
| Wheel packages data | `uv build`; unzip listing shows `templates/session-contract.json` | pass |
| Aliases + identity hold | import probe: `attune.elicitation.bridge is attune_forms.bridge`; `FormSchema` identity; fix intake resolves via loader seam | pass |
| attune-ai unaffected | full `tests/unit` keyless (`ANTHROPIC_API_KEY=""`, worktree PYTHONPATH) | 20,625 passed / 108 skipped / 6 xfailed |
| Lint clean on touched files | `ruff check` + `black --check` (venv-pinned; pre-commit uv resolve failed on this machine) | pass |

## Next action

1. Chair: authorize `gh repo create Smart-AI-Memory/attune-forms` +
   push; then publish 0.1.0 to PyPI (trusted publishing or
   `uv publish`).
2. After PyPI shows 0.1.0 (verify via `/pypi/attune-forms/0.1.0/json`,
   not the package-level endpoint): open the attune-ai PR from this
   branch; CI should resolve the dependency and go green.
