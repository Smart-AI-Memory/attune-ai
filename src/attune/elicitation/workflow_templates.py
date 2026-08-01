"""Workflow intake templates — the third-consumer expansion.

Chair-ordered 2026-08-01 (workflow-intake-forms decisions.md D3):
templates for every registry workflow whose schema forms well —
ONE shared "standard analysis" template bound per-workflow for the
path+depth(+budget) family, individual templates for the four
rich-form candidates. Poor fits (dict-context workflows:
doc-orchestrator, the health-check family, release-gate/prep) are
deliberately NOT registered — they hit the ruled free-text
fallback and the demand marker.

Every option value below is verified against the tree, never
invented (lessons: invented-form-options): depth values from the
workflow docstrings/dispatch, deep-review focus from its literal
valid set, sweep output_format from its kwargs contract, sweep
source names derived LIVE from ``default_sources()``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from attune.elicitation.fix_intake import scope_candidates
from attune.elicitation.intake_template import (
    PROVIDERS,
    TEMPLATES,
    FieldSlot,
    FormTemplate,
    ProviderContext,
)

#: Free-text sentinel for path pickers (matches the fix intake's).
OTHER_PATH = "other (type a path)"

#: Verified depth vocabulary (code_review.py and siblings:
#: "quick", "standard", "deep"; default "standard").
DEPTH_OPTIONS = ["quick", "standard", "deep"]

#: The standard-analysis family: path + depth (+ optional budget).
#: One shared shape, bound per-workflow so schema cross-checks run.
STANDARD_ANALYSIS: dict[str, str | None] = {
    "bug-predict": "max_budget_usd",
    "code-review": None,
    "dependency-check": "max_budget_usd",
    "doc-audit": "max_budget_usd",
    "doc-gen": None,
    "perf-audit": "max_budget_usd",
    "rag-code-gen": None,
    "refactor-plan": None,
    "release-notes": None,
    "research-synthesis": None,
    "security-audit": "max_budget_usd",
    "simplify-code": None,
    "test-gen": None,
}

#: Deliberately template-less (dict-shaped context inputs form
#: badly); they fall back to free text + the demand marker.
POOR_FITS = frozenset(
    {
        "doc-orchestrator",
        "health-check",
        "orchestrated-health-check",
        "release-gate",
        "release-prep",
    }
)


def _provider_analysis_paths(ctx: ProviderContext) -> list[str]:
    """Path candidates for any analysis target (fix's derivation)."""
    return scope_candidates(ctx.repo_root)


def _provider_changed_files(ctx: ProviderContext) -> list[str]:
    """Changed-file candidates (files lead in the fix derivation)."""
    return [c for c in scope_candidates(ctx.repo_root) if "." in c.rsplit("/", 1)[-1]]


def _provider_deep_review_focus(ctx: ProviderContext) -> list[str]:
    """Deep-review pass names — the workflow's literal valid set."""
    return ["security", "quality", "test-gaps"]


def _provider_sweep_sources(ctx: ProviderContext) -> list[str]:
    """Sweep source names, derived live from the adapter registry."""
    from attune.workflows.discovery_sweep.cli_workflow import default_sources

    return [s.name for s in default_sources()]


PROVIDERS["analysis_paths"] = _provider_analysis_paths
PROVIDERS["changed_files"] = _provider_changed_files
PROVIDERS["deep_review_focus"] = _provider_deep_review_focus
PROVIDERS["sweep_sources"] = _provider_sweep_sources


def _path_slot(text: str = "What should be analyzed? (--path)") -> FieldSlot:
    return FieldSlot(
        key="path",
        text=text,
        provider="analysis_paths",
        other=OTHER_PATH,
        fallback_text=f"{text} (path)",
        help_text="Changed paths first, recent directories on a clean tree.",
    )


def _depth_slot() -> FieldSlot:
    return FieldSlot(
        key="depth",
        text="How deep should the analysis go?",
        options=list(DEPTH_OPTIONS),
        default="standard",
        help_text="quick = fast pass; deep = thorough, slower.",
    )


def standard_analysis_template(workflow: str, budget_key: str | None) -> FormTemplate:
    """The ONE shared standard-analysis intake, bound per-workflow."""
    fields = [_path_slot(), _depth_slot()]
    if budget_key:
        fields.append(
            FieldSlot(
                key=budget_key,
                text="Spend ceiling for this run? (USD)",
                control="number",
                help_text="Leave blank for the configured default.",
            )
        )
    title = workflow.replace("-", " ").title()
    return FormTemplate(
        title=f"{title} intake",
        description="Scope the run: target, depth" + (", budget." if budget_key else "."),
        fields=fields,
        workflow=workflow,
    )


for _name, _budget in STANDARD_ANALYSIS.items():
    TEMPLATES[_name] = standard_analysis_template(_name, _budget)


TEMPLATES["deep-review"] = FormTemplate(
    title="Deep Review intake",
    description="Scope the multi-pass review: target, depth, passes.",
    workflow="deep-review",
    fields=[
        _path_slot("What should be reviewed? (--path)"),
        _depth_slot(),
        FieldSlot(
            key="focus",
            text="Which passes? (all when unset)",
            provider="deep_review_focus",
            control="multi_select",
            help_text="security / quality / test-gaps — the workflow's pass roster.",
        ),
    ],
)

TEMPLATES["discovery-sweep"] = FormTemplate(
    title="Discovery Sweep intake",
    description="Scope the sweep: target, depth, sources, budget, output.",
    workflow="discovery-sweep",
    fields=[
        _path_slot("What should be swept? (--path)"),
        _depth_slot(),
        FieldSlot(
            key="source",
            text="Run one source only? (all when unset)",
            provider="sweep_sources",
            help_text="Source names come from the live adapter registry.",
        ),
        FieldSlot(
            key="no_llm",
            text="Keyless sources only (skip LLM-backed)?",
            control="boolean",
        ),
        FieldSlot(
            key="budget_usd",
            text="Spend ceiling for this sweep? (USD)",
            control="number",
            help_text="Leave blank for the configured default.",
        ),
        FieldSlot(
            key="output_format",
            text="Output format?",
            options=["markdown", "json"],
            default="markdown",
        ),
    ],
)

TEMPLATES["secure-release"] = FormTemplate(
    title="Secure Release intake",
    description="Scope the release security pass: target, changed set.",
    workflow="secure-release",
    fields=[
        _path_slot("What is being released? (--path)"),
        FieldSlot(
            key="files_changed",
            text="Which changed files are in scope?",
            provider="changed_files",
            control="multi_select",
            fallback_text="Which changed files are in scope? (paths, comma-separated)",
            help_text="Derived from the working tree's changed set.",
        ),
        FieldSlot(
            key="since",
            text="Diff since which ref/tag? (optional)",
        ),
    ],
)

TEMPLATES["test-audit"] = FormTemplate(
    title="Test Audit intake",
    description="Scope the audit: tests, source, depth, budget.",
    workflow="test-audit",
    fields=[
        _path_slot("Which tests should be audited? (--path)"),
        FieldSlot(
            key="src_path",
            text="Which source tree do they cover? (--src-path)",
            provider="analysis_paths",
            other=OTHER_PATH,
            fallback_text="Which source tree do they cover? (path)",
        ),
        _depth_slot(),
        FieldSlot(
            key="max_budget_usd",
            text="Spend ceiling for this run? (USD)",
            control="number",
            help_text="Leave blank for the configured default.",
        ),
    ],
)
