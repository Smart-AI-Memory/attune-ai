"""INTERNAL workspace scoping, end to end (I-3).

Library-review I-3: ``check_access`` compared ``metadata["workspace"]``
against ``metadata["current_workspace"]`` — both read from the SAME
stored record — so nothing a caller supplied took part in the decision.
And no writer had ever set ``current_workspace``, so the branch never
ran at all. The comment above it claimed "Patterns created in one
project are invisible from another".

These tests run the real pipeline in real directories: a pattern is
STORED from one checkout and RETRIEVED from another, with the workspace
identity resolved from the actual working directory. Nothing about the
comparison is supplied by a fixture, because a record naming the
workspace it is judged against is exactly the defect.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.memory.long_term_integration import SecureMemDocsIntegration
from attune.memory.long_term_types import Classification, PermissionError


@pytest.fixture()
def store(tmp_path):
    """One shared store, reachable from either checkout."""
    return SecureMemDocsIntegration(
        storage_dir=str(tmp_path / "storage"),
        audit_log_dir=str(tmp_path / "audit"),
        enable_encryption=False,
    )


def _checkout(tmp_path, name: str):
    path = tmp_path / name
    (path / ".git").mkdir(parents=True)
    return path


def test_writer_stamps_the_workspace_it_stored_from(store, tmp_path, monkeypatch):
    """The operand the rule compares against is actually written."""
    project_a = _checkout(tmp_path, "project-a")
    monkeypatch.chdir(project_a)

    result = store.store_pattern(
        content="internal architecture note",
        pattern_type="architecture",
        user_id="alice",
        explicit_classification=Classification.INTERNAL,
        auto_classify=False,
    )

    stored = json.loads(
        (store.storage.storage_dir / f"{result['pattern_id']}.json").read_text(encoding="utf-8")
    )
    assert stored["metadata"]["workspace"] == str(project_a.resolve())


def test_internal_pattern_is_invisible_from_another_checkout(store, tmp_path, monkeypatch):
    """The claim the comment made, now true: stored in A, denied in B."""
    project_a = _checkout(tmp_path, "project-a")
    project_b = _checkout(tmp_path, "project-b")

    monkeypatch.chdir(project_a)
    result = store.store_pattern(
        content="internal architecture note",
        pattern_type="architecture",
        user_id="alice",
        explicit_classification=Classification.INTERNAL,
        auto_classify=False,
    )

    monkeypatch.chdir(project_b)
    with pytest.raises(PermissionError):
        store.retrieve_pattern(result["pattern_id"], user_id="alice")


def test_internal_pattern_is_readable_from_the_checkout_that_stored_it(
    store, tmp_path, monkeypatch
):
    """The other polarity — scoping must not deny the owning project."""
    project_a = _checkout(tmp_path, "project-a")
    monkeypatch.chdir(project_a)

    result = store.store_pattern(
        content="internal architecture note",
        pattern_type="architecture",
        user_id="alice",
        explicit_classification=Classification.INTERNAL,
        auto_classify=False,
    )

    retrieved = store.retrieve_pattern(result["pattern_id"], user_id="alice")

    assert "internal architecture note" in retrieved["content"]


def test_legacy_pattern_without_a_workspace_stays_readable(store, tmp_path, monkeypatch):
    """Records written before the stamp existed must not become unreadable."""
    project_a = _checkout(tmp_path, "project-a")
    monkeypatch.chdir(project_a)
    result = store.store_pattern(
        content="legacy internal note",
        pattern_type="architecture",
        user_id="alice",
        explicit_classification=Classification.INTERNAL,
        auto_classify=False,
    )

    # Strip the field, exactly as a pre-stamp record on disk lacks it.
    path = store.storage.storage_dir / f"{result['pattern_id']}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    del stored["metadata"]["workspace"]
    path.write_text(json.dumps(stored), encoding="utf-8")

    monkeypatch.chdir(_checkout(tmp_path, "project-b"))

    assert store.retrieve_pattern(result["pattern_id"], user_id="alice") is not None
