"""Render the attune-forms demo fixtures from the production form API.

The website's live form demo (``website/public/forms-demo/``) and the
README/website capture GIFs are projections of the form definitions in
this script. Regenerate after any change to the widget renderer or to
these definitions:

    python scripts/render_demo_forms.py

then re-record the captures if the visuals changed (the GIFs under
``docs/assets/images/`` and ``website/public/images/`` are recordings
of these fixtures being driven in a browser).

The fixtures exercise the real pipeline — ``form_from_dict`` ->
``form_to_widget_html`` — so a rendering change in ``attune_forms``
shows up here, never a hand-maintained copy drifting from the product.
The page shell supplies what the widget host normally provides: the
charset, the ``.sr-only`` rule, a centered column, and a ``sendPrompt``
shim so Submit reaches its real "Submitted" state on a static page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from attune.elicitation import form_from_dict, form_to_widget_html

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "website" / "public" / "forms-demo"

SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #faf9f5; font-family: -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  .sr-only {{ position: absolute; width: 1px; height: 1px;
    overflow: hidden; clip: rect(0 0 0 0); }}
  main {{ max-width: 680px; margin: 0 auto; padding: 24px 20px 48px; }}
</style>
<script>function sendPrompt(t) {{ /* host shim for standalone demo */ }}</script>
</head><body><main>{body}</main></body></html>
"""

AUDIT: dict[str, Any] = {
    "form_id": "demo-audit-scope",
    "title": "Scope the security audit",
    "description": "Five controls, one form - pick and go.",
    "fields": [
        {
            "id": "depth",
            "type": "decision",
            "text": "How deep should this audit go?",
            "options": ["Changed files only", "Full tree", "Dependencies only"],
            "recommended": "Changed files only",
            "rationale": (
                "Covers the diff under review in ~2 min; the full tree "
                "re-scans code vetted last week."
            ),
            "option_notes": {
                "Changed files only": "Fast; exactly the pre-merge surface.",
                "Full tree": "Thorough but ~20 min.",
                "Dependencies only": ("CVE sweep of the lockfile; skips first-party code."),
            },
        },
        {
            "id": "focus",
            "type": "multi_select",
            "text": "Focus areas",
            "options": [
                "Injection / eval-exec",
                "Path traversal",
                "Hardcoded secrets",
                "Dependency CVEs",
            ],
        },
        {
            "id": "tier",
            "type": "single_select",
            "text": "Model tier for the LLM pass",
            "options": ["Cheap (Haiku)", "Capable (Sonnet)", "Premium (Fable 5)"],
            "default": "Capable (Sonnet)",
            "help_text": ("Escalation is automatic when findings need a second look."),
        },
        {
            "id": "max_findings",
            "type": "number",
            "text": "Cap the report at how many findings?",
            "minimum": 5,
            "maximum": 50,
            "default": 20,
        },
        {
            "id": "path",
            "type": "text_input",
            "text": "Limit to a path (blank = whole scope)",
            "required": False,
        },
    ],
}

RETRO: dict[str, Any] = {
    "form_id": "retro-demo",
    "title": "Session retro - 2026-08-29",
    "description": ("Rule each item; ratifications are recorded before the session " "closes."),
    "fields": [
        {
            "id": "opportunities",
            "type": "triage",
            "text": "Opportunities",
            "dispositions": [
                "do now",
                "queue to starter",
                "needs discussion",
                "skip",
            ],
            "triage_items": [
                {
                    "id": "schema_docs",
                    "tag": "1",
                    "label": "Document the form_from_dict decision keys",
                    "detail": (
                        "First render attempt guessed 'recommendation' + "
                        "option dicts; the real keys are 'recommended'/"
                        "'rationale'/'option_notes'. A worked example in "
                        "the docs would have saved the retry."
                    ),
                },
                {
                    "id": "fixture_script",
                    "tag": "2",
                    "label": "Commit a render_demo_forms.py fixture script",
                    "detail": (
                        "Demo assets re-render from the live API, so "
                        "captures can never drift from the product."
                    ),
                },
            ],
        },
        {
            "id": "friction",
            "type": "triage",
            "text": "Friction",
            "dispositions": [
                "do now",
                "queue to starter",
                "needs discussion",
                "skip",
            ],
            "triage_items": [
                {
                    "id": "preview_static",
                    "tag": "3",
                    "label": ("Preview pane renders out-of-project files as " "static snapshots"),
                    "detail": (
                        "Cost two navigation retries before the fixture "
                        "moved inside the project folder."
                    ),
                },
            ],
        },
        {
            "id": "keep",
            "type": "triage",
            "text": "Keep",
            "dispositions": [
                "do now",
                "queue to starter",
                "needs discussion",
                "skip",
            ],
            "triage_items": [
                {
                    "id": "dogfood_widget",
                    "tag": "4",
                    "label": ("Scoping questions asked through the product's " "own form widget"),
                    "detail": (
                        "The planning form for the demo captures was "
                        "itself a live attune-forms widget - the demo "
                        "demoed itself."
                    ),
                },
                {
                    "id": "reserved_slot",
                    "tag": "5",
                    "label": "README already reserved the demo-gif-slot",
                    "detail": (
                        "Filled an existing placeholder instead of " "inventing a new surface."
                    ),
                },
            ],
        },
    ],
}

FIXTURES: list[tuple[str, dict[str, Any], str]] = [
    ("audit", AUDIT, "Before I run the audit, five quick calls:"),
    ("retro", RETRO, "Session close-out: rule each item, one tap each."),
]


def main() -> None:
    """Render every fixture into ``website/public/forms-demo/``."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec, message in FIXTURES:
        form = form_from_dict(spec)
        body = form_to_widget_html(form, message=message)
        page = SHELL.format(title=spec["title"], body=body)
        out = OUT_DIR / f"{name}.html"
        out.write_text(page, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
