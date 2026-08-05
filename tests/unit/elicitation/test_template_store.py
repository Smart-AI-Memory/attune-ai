"""Tests for the V7 form-template library (template_store.py).

Covers R1–R3 (store, loader, slot substitution) and AC-3 (a malformed
template fails with the same every-problem-listed FormValidationError a
hand-built dict gets).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_from_template,
    list_templates,
    template_store,
)

SESSION_CONTRACT_ANSWERS: dict[str, Any] = {
    "mode": "Executing a planned spec",
    "outcome": "V7 template library shipped on a PR",
    "done_when": "R1-R4 implemented, tests green, PR open",
    "effort_cap": "one PR",
}


class TestListTemplates:
    def test_session_contract_is_stored(self) -> None:
        assert "session-contract" in list_templates()

    def test_names_are_sorted(self) -> None:
        names = list_templates()
        assert names == sorted(names)


class TestFormFromTemplate:
    def test_loads_and_substitutes_slots(self) -> None:
        form = form_from_template("session-contract", {"project": "attune-ai"})
        assert form.title == "Session contract — attune-ai"
        assert [q.id for q in form.questions] == [
            "mode",
            "outcome",
            "done_when",
            "effort_cap",
        ]

    def test_round_trip_carries_template_id(self) -> None:
        """AC-2 join key: responses from the same template are joinable."""
        form = form_from_template("session-contract", {"project": "attune-ai"})
        response = collect_form_response(
            form, SESSION_CONTRACT_ANSWERS, template_id="session-contract"
        )
        assert response.template_id == "session-contract"
        assert response.responses["mode"] == "Executing a planned spec"

    def test_missing_slot_value_listed(self) -> None:
        with pytest.raises(FormValidationError) as exc:
            form_from_template("session-contract", {})
        assert any("missing value for slot 'project'" in p for p in exc.value.problems)

    def test_extra_slot_value_listed(self) -> None:
        with pytest.raises(FormValidationError) as exc:
            form_from_template("session-contract", {"project": "x", "nonexistent": "y"})
        assert any("unexpected slot value 'nonexistent'" in p for p in exc.value.problems)

    def test_missing_and_extra_listed_together(self) -> None:
        """Every problem listed in one raise, not fail-on-first."""
        with pytest.raises(FormValidationError) as exc:
            form_from_template("session-contract", {"nonexistent": "y"})
        joined = "\n".join(exc.value.problems)
        assert "missing value for slot 'project'" in joined
        assert "unexpected slot value 'nonexistent'" in joined

    def test_non_string_slot_value_listed(self) -> None:
        with pytest.raises(FormValidationError) as exc:
            form_from_template("session-contract", {"project": 42})
        assert any("must be a string, got int" in p for p in exc.value.problems)

    def test_unknown_template_names_available(self) -> None:
        with pytest.raises(FormValidationError) as exc:
            form_from_template("no-such-template")
        assert any("session-contract" in p for p in exc.value.problems)

    @pytest.mark.parametrize("bad_name", ["../escape", "a/b", "UPPER", "", "x.json"])
    def test_invalid_names_rejected_before_any_read(self, bad_name: str) -> None:
        with pytest.raises(FormValidationError) as exc:
            form_from_template(bad_name)
        assert any("invalid template name" in p for p in exc.value.problems)


def _write_store(tmp_path: Path, name: str, content: Any) -> None:
    text = content if isinstance(content, str) else json.dumps(content)
    (tmp_path / f"{name}.json").write_text(text, encoding="utf-8")


class TestMalformedTemplateParity:
    """AC-3: malformed templates fail exactly like hand-built dicts."""

    @pytest.fixture(autouse=True)
    def _tmp_store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(template_store, "_TEMPLATE_DIR", tmp_path)
        self.store = tmp_path

    def test_bad_type_and_duplicate_id_match_hand_built_errors(self) -> None:
        malformed = {
            "title": "Bad form",
            "fields": [
                {"id": "a", "type": "not-a-type", "text": "Q1"},
                {"id": "a", "type": "boolean", "text": "Q2"},
            ],
        }
        with pytest.raises(FormValidationError) as hand_built:
            form_from_dict(malformed)

        _write_store(self.store, "bad", {**malformed, "slots": []})
        with pytest.raises(FormValidationError) as templated:
            form_from_template("bad")

        assert templated.value.problems == hand_built.value.problems

    def test_invalid_json_fails_with_listed_problem(self) -> None:
        _write_store(self.store, "broken", "{not json")
        with pytest.raises(FormValidationError) as exc:
            form_from_template("broken")
        assert any("not valid JSON" in p for p in exc.value.problems)

    def test_non_object_template_rejected(self) -> None:
        _write_store(self.store, "listy", ["not", "a", "form"])
        with pytest.raises(FormValidationError) as exc:
            form_from_template("listy")
        assert any("must be a JSON object" in p for p in exc.value.problems)

    def test_undeclared_placeholder_rejected(self) -> None:
        _write_store(
            self.store,
            "sneaky",
            {
                "slots": [],
                "title": "Uses {undeclared}",
                "fields": [{"id": "a", "type": "boolean", "text": "Q"}],
            },
        )
        with pytest.raises(FormValidationError) as exc:
            form_from_template("sneaky")
        assert any("undeclared placeholder '{undeclared}'" in p for p in exc.value.problems)

    def test_bad_slots_declaration_rejected(self) -> None:
        _write_store(
            self.store,
            "badslots",
            {
                "slots": "project",
                "title": "T",
                "fields": [{"id": "a", "type": "boolean", "text": "Q"}],
            },
        )
        with pytest.raises(FormValidationError) as exc:
            form_from_template("badslots")
        assert any("'slots' must be a list of strings" in p for p in exc.value.problems)

    def test_valid_template_in_tmp_store_loads(self) -> None:
        """The loader itself works against any store directory."""
        _write_store(
            self.store,
            "minimal",
            {
                "slots": ["who"],
                "title": "Hello {who}",
                "fields": [{"id": "ok", "type": "boolean", "text": "Proceed for {who}?"}],
            },
        )
        form = form_from_template("minimal", {"who": "Patrick"})
        assert form.title == "Hello Patrick"
        assert form.questions[0].text == "Proceed for Patrick?"
        assert list_templates() == ["minimal"]
