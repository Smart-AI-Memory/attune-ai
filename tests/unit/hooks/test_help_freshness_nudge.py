"""Behavioral tests for the help_freshness_nudge SessionStart hook.

The hook inspects a repo's .help/ tree and prints a one-line nudge when
templates are orphaned, incomplete, or coarsely stale. These tests build a
throwaway .help/ layout under tmp_path and monkeypatch ``_repo_root`` so
the manifest parser, the staleness comparison, and every branch of
``main`` (early-return, all-clean, and each nudge reason) are exercised
against real files without touching the actual repo.
"""

from __future__ import annotations

import os

from attune.hooks.scripts import help_freshness_nudge as hook

EXPECTED_KINDS = hook.EXPECTED_KINDS


def _make_help_tree(root):
    help_dir = root / ".help"
    templates = help_dir / "templates"
    templates.mkdir(parents=True)
    return help_dir, templates


def _complete_feature(templates, name):
    feat = templates / name
    feat.mkdir()
    for kind in EXPECTED_KINDS:
        (feat / f"{kind}.md").write_text(f"# {kind}\n", encoding="utf-8")
    return feat


def _write_manifest(help_dir, features):
    lines = ["features:"]
    for name, globs in features.items():
        lines.append(f"  {name}:")
        lines.append("    files:")
        for g in globs:
            lines.append(f"      - {g}")
    (help_dir / "features.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# _load_manifest
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_missing_file_returns_empty(self, tmp_path):
        assert hook._load_manifest(tmp_path) == {}

    def test_parses_features_and_file_globs(self, tmp_path):
        help_dir, _ = _make_help_tree(tmp_path)
        _write_manifest(help_dir, {"memory": ["src/a.py", "src/b.py"], "auth": []})

        manifest = hook._load_manifest(help_dir)
        assert manifest["memory"] == ["src/a.py", "src/b.py"]
        assert manifest["auth"] == []

    def test_stops_collecting_at_dedented_line(self, tmp_path):
        help_dir, _ = _make_help_tree(tmp_path)
        # a non-indented line after a files block ends collection
        (help_dir / "features.yaml").write_text(
            "features:\n" "  memory:\n" "    files:\n" "      - src/a.py\n" "trailing: value\n",
            encoding="utf-8",
        )
        manifest = hook._load_manifest(help_dir)
        assert manifest["memory"] == ["src/a.py"]


# ---------------------------------------------------------------------------
# _coarse_staleness
# ---------------------------------------------------------------------------


class TestCoarseStaleness:
    def test_skips_feature_without_concept(self, tmp_path):
        _, templates = _make_help_tree(tmp_path)
        (templates / "memory").mkdir()  # no concept.md
        assert hook._coarse_staleness({"memory": ["src/*.py"]}, tmp_path, templates) == []

    def test_flags_feature_with_newer_source(self, tmp_path):
        _, templates = _make_help_tree(tmp_path)
        feat = templates / "memory"
        feat.mkdir()
        concept = feat / "concept.md"
        concept.write_text("# c\n", encoding="utf-8")
        src = tmp_path / "mod.py"
        src.write_text("x = 1\n", encoding="utf-8")
        # force the source to be newer than the concept
        os.utime(concept, (1, 1))
        os.utime(src, (10_000, 10_000))

        stale = hook._coarse_staleness({"memory": ["mod.py"]}, tmp_path, templates)
        assert stale == ["memory"]

    def test_not_stale_when_concept_newer(self, tmp_path):
        _, templates = _make_help_tree(tmp_path)
        feat = templates / "memory"
        feat.mkdir()
        concept = feat / "concept.md"
        concept.write_text("# c\n", encoding="utf-8")
        src = tmp_path / "mod.py"
        src.write_text("x = 1\n", encoding="utf-8")
        os.utime(src, (1, 1))
        os.utime(concept, (10_000, 10_000))

        assert hook._coarse_staleness({"memory": ["mod.py"]}, tmp_path, templates) == []


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_returns_zero_when_no_help_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hook, "_repo_root", lambda: tmp_path)
        assert hook.main() == 0

    def test_clean_tree_prints_nothing(self, tmp_path, monkeypatch, capsys):
        help_dir, templates = _make_help_tree(tmp_path)
        _complete_feature(templates, "memory")
        _write_manifest(help_dir, {"memory": []})
        monkeypatch.setattr(hook, "_repo_root", lambda: tmp_path)

        assert hook.main() == 0
        assert capsys.readouterr().out == ""

    def test_reports_orphan_directory(self, tmp_path, monkeypatch, capsys):
        help_dir, templates = _make_help_tree(tmp_path)
        _complete_feature(templates, "ghost")  # on disk, not in manifest
        _write_manifest(help_dir, {})
        monkeypatch.setattr(hook, "_repo_root", lambda: tmp_path)

        assert hook.main() == 0
        assert "1 orphan" in capsys.readouterr().out

    def test_reports_incomplete_feature(self, tmp_path, monkeypatch, capsys):
        help_dir, templates = _make_help_tree(tmp_path)
        feat = templates / "memory"
        feat.mkdir()
        (feat / "concept.md").write_text("# c\n", encoding="utf-8")  # missing kinds
        _write_manifest(help_dir, {"memory": []})
        monkeypatch.setattr(hook, "_repo_root", lambda: tmp_path)

        assert hook.main() == 0
        assert "1 incomplete" in capsys.readouterr().out

    def test_reports_stale_feature(self, tmp_path, monkeypatch, capsys):
        help_dir, templates = _make_help_tree(tmp_path)
        feat = _complete_feature(templates, "memory")
        src = tmp_path / "mod.py"
        src.write_text("x = 1\n", encoding="utf-8")
        os.utime(feat / "concept.md", (1, 1))
        os.utime(src, (10_000, 10_000))
        _write_manifest(help_dir, {"memory": ["mod.py"]})
        monkeypatch.setattr(hook, "_repo_root", lambda: tmp_path)

        assert hook.main() == 0
        assert "1 stale" in capsys.readouterr().out


def test_repo_root_points_at_a_directory():
    # _repo_root walks up from the module file; it should resolve to a dir
    assert hook._repo_root().is_dir()
