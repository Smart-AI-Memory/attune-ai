"""Regression guard: "parse hostile input, then degrade" must actually degrade.

Library-review batch 2 (thread ``q-attune-ai-review-checkpoint1-001``)
confirmed eight instances of one class across the invoked surface, plus
three widening siblings. The shape has two variants:

A. A parsed **non-dict** reaches a ``.get``/``[]`` chain and raises
   ``AttributeError``/``TypeError``.
B. The parser raises **outside the caught set** — ``yaml.YAMLError`` is
   not a ``ValueError`` subclass, and ``ast.parse`` raises ``ValueError``
   (not ``SyntaxError``) on a null byte.

Each test below pins one confirmed site: it failed before the fix and
passes after. The curator's source readers are the clean counter-example
this class should be measured against.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

MALFORMED_YAML = "features:\n  - foo: [unclosed\n bad: : :\n"

#: Run subprocess probes against THIS tree. The editable install's
#: finder maps ``attune`` to the main checkout, so a worktree run
#: would otherwise exercise main's code, not the code under test.
_SRC = str(Path(__file__).resolve().parents[3] / "src")


def _env(home: Path) -> dict[str, str]:
    """Subprocess env pinned to this tree with an isolated home."""
    return {
        **os.environ,
        "ATTUNE_HOME": str(home),
        "PYTHONPATH": os.pathsep.join([_SRC, os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
    }


# ---------------------------------------------------------------------------
# Variant B — parser raises outside the caught set
# ---------------------------------------------------------------------------


def test_fact_check_survives_malformed_features_yaml(tmp_path: Path) -> None:
    """F1: yaml.YAMLError must not abort the whole fact-check run."""
    from attune.authoring import fact_check

    (tmp_path / ".help").mkdir()
    (tmp_path / ".help" / "features.yaml").write_text(MALFORMED_YAML, encoding="utf-8")
    (tmp_path / "polished.md").write_text("This project ships 5 features.\n", encoding="utf-8")

    fact_check.check_polished_file(tmp_path / "polished.md", project_root=tmp_path)


def test_load_manifest_raises_value_error_on_malformed_yaml(tmp_path: Path) -> None:
    """F2: the documented ValueError contract must hold for broken YAML."""
    from attune.help.manifest import load_manifest

    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(MALFORMED_YAML, encoding="utf-8")

    with pytest.raises(ValueError):
        load_manifest(help_dir)


def test_related_preambles_degrade_on_malformed_manifest(tmp_path: Path) -> None:
    """F2: the degrade-by-contract caller must survive a corrupt manifest."""
    from attune.help.preamble import get_related_preambles

    help_dir = tmp_path / ".help"
    (help_dir / "templates" / "security").mkdir(parents=True)
    (help_dir / "features.yaml").write_text(MALFORMED_YAML, encoding="utf-8")

    assert get_related_preambles("security", help_dir=help_dir) == []


def test_source_introspection_skips_null_byte_file(tmp_path: Path) -> None:
    """F5: ast.parse raises ValueError on a null byte — skip, don't abort."""
    from attune.authoring.source_introspection import _extract_source_info

    (tmp_path / "good.py").write_text("def good():\n    return 1\n", encoding="utf-8")
    (tmp_path / "corrupt.py").write_bytes(b"x = 1\x00y = 2\n")

    _extract_source_info(["good.py", "corrupt.py"], tmp_path)


# ---------------------------------------------------------------------------
# Variant A — parsed non-dict reaching a .get / [] chain
# ---------------------------------------------------------------------------


def test_help_session_degrades_on_non_dict_cache(tmp_path: Path, monkeypatch) -> None:
    """F3: a non-dict cache must yield defaults, not crash at import."""
    import attune.help.session as session

    cache = tmp_path / "help_session.json"
    cache.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(session, "_SESSION_FILE", cache)

    assert session._load_session() == session._defaults()


def test_cross_links_non_dict_degrades_to_empty(tmp_path: Path) -> None:
    """F4: a corrupt cross_links.json must not crash template rendering."""
    from attune.help import templates

    (tmp_path / "cross_links.json").write_text("[]", encoding="utf-8")

    links = templates._load_cross_links(tmp_path)
    assert links == {}
    assert templates._resolve_related("err-foo", links) == []


@pytest.mark.parametrize(
    "content",
    [
        '{"timestamp":"2030-01-01","cost":1}\n123\n',  # non-dict row
        '{"timestamp":"not-a-date","cost":1}\n',  # non-ISO timestamp
        '{"timestamp":"2030-01-01","tokens":5}\n',  # non-dict tokens
    ],
)
def test_metrics_skips_malformed_rows(tmp_path: Path, content: str) -> None:
    """E1: the skip-malformed-rows contract must cover every shape.

    The non-dict-``tokens`` variant is the class documented on
    2026-08-01 (production bug #7) and never fixed at this site.
    """
    from attune.monitoring.metrics import collect_metrics

    (tmp_path / "usage.jsonl").write_text(content, encoding="utf-8")
    collect_metrics(tmp_path)


def test_audit_query_drops_non_dict_rows(tmp_path: Path) -> None:
    """Widening: a non-dict row must not be returned AS an audit event."""
    from attune.memory.security.query import AuditQueryMixin

    log = tmp_path / "audit.jsonl"
    log.write_text(
        '{"event_type":"a","user_id":"u","status":"ok"}\n'
        "123\n"
        '{"event_type":"a","user_id":"u","status":"ok"}\n',
        encoding="utf-8",
    )

    class _Query(AuditQueryMixin):
        def __init__(self, path: Path) -> None:
            self.log_path = path

    results = _Query(log).query(limit=10)
    assert len(results) == 2
    assert all(isinstance(row, dict) for row in results)


def test_file_session_degrades_on_non_dict(tmp_path: Path) -> None:
    """Widening: a non-dict session file must start a fresh session."""
    from attune.memory.file_session_persistence import PersistenceMixin

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "current.json").write_text("[1,2,3]", encoding="utf-8")

    class _Store(PersistenceMixin):
        def __init__(self) -> None:
            self.user_id = "tester"
            self.config = type("_Cfg", (), {"sessions_dir": sessions, "session_ttl_hours": 24})()
            self.saved: list = []

        def _save_current(self, state) -> None:
            self.saved.append(state)

    state = _Store()._load_current_or_create()
    assert state.session_id


# ---------------------------------------------------------------------------
# CLI / compose boundaries — real subprocess round trips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", ["[1,2,3]", "5", '"hello"', "null", "{bad"])
def test_workflow_input_reports_cli_error_exit_3(payload: str, tmp_path: Path) -> None:
    """D1: a non-dict --input is a CLI error (exit 3), not a crash (exit 1)."""
    result = subprocess.run(
        [sys.executable, "-m", "attune.cli_minimal", "workflow", "run", "bug-predict"]
        + ["--input", payload],
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert result.returncode == 3, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("module", ["spec_intake", "fix_intake"])
@pytest.mark.parametrize("payload", ["[]", "42", "null", "notjson"])
def test_compose_seams_reject_non_object_answers(module: str, payload: str, tmp_path: Path) -> None:
    """E2: the compose seams must report cleanly, never traceback."""
    result = subprocess.run(
        [sys.executable, "-m", f"attune.elicitation.{module}", "--compose"],
        input=payload,
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_compose_dict_probes_does_not_emit_bogus_probe(tmp_path: Path) -> None:
    """E2: a dict ``probes`` used to be iterated to its KEYS at exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "attune.elicitation.fix_intake", "--compose"],
        input=json.dumps({"request": "x", "probes": {"a": 1}}),
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert result.returncode == 0
    assert "--probe" not in result.stdout
