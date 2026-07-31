"""Spec intake: derived candidates, form validity, contract
composition — real tmp trees, no mocks (mirrors test_fix_intake)."""

from __future__ import annotations

from pathlib import Path

from attune.elicitation.spec_intake import (
    OTHER,
    area_candidates,
    build_spec_intake_form,
    compose_spec_contract,
    existing_spec_slugs,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for pkg in ("workflows", "elicitation"):
        d = repo / "src" / "attune" / pkg
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (repo / "src" / "attune" / "__pycache__").mkdir()
    for slug in ("outcome-first-fix", "local-first-reports"):
        (repo / "docs" / "specs" / slug).mkdir(parents=True)
    return repo


def test_area_candidates_are_packages_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src" / "attune" / "not_a_pkg").mkdir()
    areas = area_candidates(repo)
    assert areas == ["src/attune/elicitation", "src/attune/workflows"]


def test_existing_spec_slugs_listed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert existing_spec_slugs(repo) == ["local-first-reports", "outcome-first-fix"]
    assert existing_spec_slugs(tmp_path / "empty") == []


def test_form_builds_with_areas_and_offers_other(tmp_path: Path) -> None:
    form = build_spec_intake_form(["src/attune/workflows"])
    ids = [q.id for q in form.questions]
    assert ids == ["outcome", "done_when", "area", "slug"]
    area_q = form.questions[2]
    assert area_q.type.value == "single_select"
    assert area_q.options[-1] == OTHER
    assert form.questions[3].required is False


def test_form_degrades_to_free_text_without_areas() -> None:
    form = build_spec_intake_form([])
    area_q = form.questions[2]
    assert area_q.type.value == "text_input"
    assert area_q.required


def test_compose_contract_full() -> None:
    block = compose_spec_contract(
        {
            "outcome": "a spec intake form ships",
            "done_when": "PR merged green",
            "area": "src/attune/elicitation",
            "slug": "spec-intake",
        },
        taken_slugs=["outcome-first-fix"],
    )
    assert "- **Outcome:** a spec intake form ships" in block
    assert "- **Done when:** PR merged green" in block
    assert "- **Scope:** src/attune/elicitation" in block
    assert "- **Spec:** docs/specs/spec-intake/" in block
    assert "WARNING" not in block


def test_compose_contract_slug_collision_warns() -> None:
    block = compose_spec_contract(
        {"outcome": "x", "done_when": "y", "slug": "outcome-first-fix"},
        taken_slugs=["outcome-first-fix"],
    )
    assert "WARNING" in block
    assert "amend that spec or pick a new slug" in block


def test_compose_contract_omits_other_area_and_blank_slug() -> None:
    block = compose_spec_contract(
        {"outcome": "x", "done_when": "y", "area": OTHER, "slug": ""},
        taken_slugs=[],
    )
    assert "Scope" not in block
    assert "docs/specs/" not in block
