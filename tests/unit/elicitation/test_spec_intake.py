"""Spec intake: derived candidates, form validity, contract
composition — real tmp trees, no mocks (mirrors test_fix_intake)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from attune.elicitation.spec_intake import (
    OTHER,
    _main,
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


def test_main_default_prints_form_and_areas_payload(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    assert _main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["areas"] == ["src/attune/elicitation", "src/attune/workflows"]
    assert payload["taken_slugs"] == ["local-first-reports", "outcome-first-fix"]
    field_ids = [f["id"] for f in payload["form"]["fields"]]
    assert field_ids == ["outcome", "done_when", "area", "slug"]
    assert payload["form"]["title"] == "New spec intake"
    outcome_field = payload["form"]["fields"][0]
    assert outcome_field["required"] is True
    assert outcome_field["type"] == "textarea"
    assert all(
        value is not None for field in payload["form"]["fields"] for value in field.values()
    ), "CLI form payload must be accepted unchanged by strict MCP tool schemas"

    import jsonschema

    from attune.mcp.tool_schemas import get_elicitation_tools

    schema = get_elicitation_tools()["elicitation_ask"]["input_schema"]["properties"]["form"]
    jsonschema.validate(payload["form"], schema)


def test_main_default_degrades_without_areas(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert _main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["areas"] == []
    assert payload["taken_slugs"] == []
    area_field = payload["form"]["fields"][2]
    assert area_field["type"] == "text_input"


def test_main_compose_reads_answers_from_stdin(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    answers = {
        "outcome": "a spec intake form ships",
        "done_when": "PR merged green",
        "area": "src/attune/elicitation",
        "slug": "spec-intake",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(answers)))
    assert _main(["--compose"]) == 0
    expected = compose_spec_contract(answers, existing_spec_slugs(repo))
    assert capsys.readouterr().out.strip() == expected.strip()


def test_main_compose_warns_on_slug_collision(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    answers = {"outcome": "x", "done_when": "y", "slug": "outcome-first-fix"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(answers)))
    assert _main(["--compose"]) == 0
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "amend that spec or pick a new slug" in out
