"""Spec intake — derived candidates and the new-spec intake form.

The `/spec` analog of :mod:`attune.elicitation.fix_intake` (same
pattern, chair-requested 2026-07-31): one form batches the
dimensions a NEW spec needs — what should exist, the acceptance
criteria, the primary code area, and an optional slug — instead of
N sequential question turns. Candidates are DERIVED from the tree
(package directories, existing spec slugs); nothing is
hand-maintained.

The composed output is a session-contract block (outcome /
done-when / scope), which is what a spec's Stage 1 brainstorm
actually consumes.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from attune.elicitation.bridge import form_from_dict
from attune.meta_workflows.models import FormSchema

#: Free-text sentinel offered alongside derived options.
OTHER = "other (name an area)"

_SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", ".git"})


def existing_spec_slugs(repo_root: Path) -> list[str]:
    """Slugs already taken under ``docs/specs/`` (collision check)."""
    specs_dir = repo_root / "docs" / "specs"
    if not specs_dir.is_dir():
        return []
    return sorted(d.name for d in specs_dir.iterdir() if d.is_dir() and d.name not in _SKIP_DIRS)


def area_candidates(repo_root: Path, limit: int = 6) -> list[str]:
    """Likely primary code areas: packages under ``src/attune/``.

    Mechanical derivation — a directory with an ``__init__.py`` is a
    package. Capped at ``limit``; the form always appends a free-text
    escape, so the cap bounds noise, not reach.
    """
    pkg_root = repo_root / "src" / "attune"
    if not pkg_root.is_dir():
        return []
    areas = [
        f"src/attune/{d.name}"
        for d in sorted(pkg_root.iterdir())
        if d.is_dir() and (d / "__init__.py").is_file() and d.name not in _SKIP_DIRS
    ]
    return areas[:limit]


def build_spec_intake_form(areas: list[str]) -> FormSchema:
    """The one new-spec intake form (D21: widget-first, batched)."""
    fields: list[dict[str, Any]] = [
        {
            "id": "outcome",
            "text": "What should exist when this spec is done?",
            "type": "textarea",
            "required": True,
            "help_text": "One or two sentences — becomes the spec's outcome statement.",
        },
        {
            "id": "done_when",
            "text": "Done when? (acceptance criteria)",
            "type": "textarea",
            "required": True,
            "help_text": "Cheap to write, expensive to skip — e.g. 'PR merged green, regression test landed'.",
        },
    ]
    if areas:
        fields.append(
            {
                "id": "area",
                "text": "Primary code area?",
                "type": "single_select",
                "options": [*areas, OTHER],
                "help_text": "Where most of the change lands — bounds the design conversation.",
            }
        )
    else:
        fields.append(
            {
                "id": "area",
                "text": "Primary code area? (path or name)",
                "type": "text_input",
                "required": True,
            }
        )
    fields.append(
        {
            "id": "slug",
            "text": "Spec slug (optional — leave blank to derive one)",
            "type": "text_input",
            "required": False,
            "help_text": "kebab-case directory name under docs/specs/.",
        }
    )
    return form_from_dict(
        {
            "title": "New spec intake",
            "description": "Frame the spec before brainstorming: outcome, acceptance, area.",
            "fields": fields,
        }
    )


def compose_spec_contract(answers: dict[str, Any], taken_slugs: list[str]) -> str:
    """Render answers as the session-contract block Stage 1 consumes.

    A slug collision is surfaced as a WARNING line rather than an
    error — the existing spec may be exactly where the work belongs
    (amend, don't fork), and that call is the user's.
    """
    outcome = str(answers.get("outcome", "")).strip()
    done_when = str(answers.get("done_when", "")).strip()
    area = str(answers.get("area", "")).strip()
    slug = str(answers.get("slug", "")).strip()
    lines = [
        "## Session contract",
        "",
        f"- **Outcome:** {outcome}",
        f"- **Done when:** {done_when}",
    ]
    if area and area != OTHER:
        lines.append(f"- **Scope:** {area}")
    if slug:
        lines.append(f"- **Spec:** docs/specs/{slug}/")
        if slug in taken_slugs:
            lines.append(
                f"- **WARNING:** docs/specs/{slug}/ already exists — "
                "amend that spec or pick a new slug."
            )
    return "\n".join(lines) + "\n"


def _main(argv: list[str]) -> int:
    """CLI seam for the /spec skill (mirrors fix_intake's contract).

    Default: print ``{"form": ..., "areas": [...], "taken_slugs":
    [...]}`` for the current repo. With ``--compose``, read answers
    JSON on stdin and print the composed session-contract block.
    """
    repo_root = Path.cwd()
    if "--compose" in argv:
        answers = json.load(sys.stdin)
        print(compose_spec_contract(answers, existing_spec_slugs(repo_root)))
        return 0
    areas = area_candidates(repo_root)
    form = build_spec_intake_form(areas)
    payload = {
        "form": {
            "title": form.title,
            "description": form.description,
            "fields": [
                {
                    "id": q.id,
                    "text": q.text,
                    "type": q.type.value,
                    "options": list(q.options),
                    "default": q.default,
                    "help_text": q.help_text,
                    "required": q.required,
                }
                for q in form.questions
            ],
        },
        "areas": areas,
        "taken_slugs": existing_spec_slugs(repo_root),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover — thin seam, tested via functions
    raise SystemExit(_main(sys.argv[1:]))
