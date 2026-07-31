"""Tests for the absorbed deterministic authoring core.

Covers `attune.authoring` — the projector + source-introspection
machinery absorbed from attune-author (consolidation spec). These prove
the absorbed code is importable in-repo and that its pure transforms
(scaffold hashing, AST introspection) behave deterministically. The
byte-identical projection guarantee is verified live against the
elicitation-forms master at migration time (golden git-diff).
"""

from __future__ import annotations

import textwrap

from attune.authoring import project_feature, validate_master_file
from attune.authoring.source_introspection import (
    _extract_source_info,
    compute_scaffold_hash,
)


class TestPublicSurface:
    def test_projector_public_callables_import_in_repo(self):
        # The consumers (scripts/project_features.py) import these — they
        # must resolve from attune.authoring, not attune_author.
        assert callable(project_feature)
        assert callable(validate_master_file)


class TestScaffoldHash:
    def test_deterministic(self):
        text = "# Title\n\nbody line\n"
        assert compute_scaffold_hash(text) == compute_scaffold_hash(text)

    def test_excludes_volatile_metadata_lines(self):
        # Lines carrying generated_at / scaffold_hash / source_hash are
        # normalized out, so two renders differing only in those fields
        # hash equal (the whole point — re-polishing them is a no-op).
        a = "generated_at: 2026-01-01T00:00:00\nbody\n"
        b = "generated_at: 2099-12-31T23:59:59\nbody\n"
        assert compute_scaffold_hash(a) == compute_scaffold_hash(b)

    def test_content_change_changes_hash(self):
        assert compute_scaffold_hash("body one\n") != compute_scaffold_hash("body two\n")


class TestSourceIntrospection:
    def test_extracts_public_function(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            textwrap.dedent(
                '''
                """Module doc."""


                def public_fn(x: int) -> int:
                    """Doc for public_fn."""
                    return x


                def _private():
                    pass
                '''
            )
        )
        info = _extract_source_info(["mod.py"], tmp_path)
        names = {f["name"] for f in info.public_functions}
        assert "public_fn" in names
        assert "_private" not in names  # underscore-private excluded

    def test_counts_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        info = _extract_source_info(["a.py", "b.py"], tmp_path)
        assert info.file_count == 2

    def test_unparseable_file_is_skipped_not_fatal(self, tmp_path):
        (tmp_path / "broken.py").write_text("def (:\n")  # syntax error
        # Should not raise — best-effort introspection logs and continues.
        info = _extract_source_info(["broken.py"], tmp_path)
        assert info.file_count == 1

    def test_non_python_file_counted_but_not_parsed(self, tmp_path):
        (tmp_path / "data.txt").write_text("not python\n")
        info = _extract_source_info(["data.txt"], tmp_path)
        assert info.file_count == 1
        assert info.module_docstrings == []

    def test_extracts_public_class_with_signature(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            textwrap.dedent(
                '''
                class Widget:
                    """A public widget."""

                    def render(self) -> str:
                        return ""


                class _Hidden:
                    pass
                '''
            )
        )
        info = _extract_source_info(["mod.py"], tmp_path)
        assert [c["name"] for c in info.public_classes] == ["Widget"]
        (sig,) = info.class_signatures
        assert sig["name"] == "Widget"
        assert sig["doc"] == "A public widget."
        assert "render(self) -> str" in sig["methods"]
        assert sig["is_dataclass"] is False

    def test_module_constant_records_source_file(self, tmp_path):
        (tmp_path / "consts.py").write_text('ALLOWED = ("a", "b")\n')
        info = _extract_source_info(["consts.py"], tmp_path)
        (const,) = info.module_constants
        assert const["name"] == "ALLOWED"
        assert const["values"] == ["a", "b"]
        assert const["file"] == "consts.py"
