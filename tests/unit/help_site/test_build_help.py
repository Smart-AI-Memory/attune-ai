"""Tests for the public help-site build script (attune-ai-dev/build_help.py).

The script is not importable as a package module (it lives under the
static-site dir), so it's loaded via importlib. ``markdown-it-py`` is
a build-time-only dep (not in the project's runtime extras), so the
whole module is skipped when it's absent.

build_help.py renders the ``.help/`` corpus to static pages; these
tests exercise its pure helpers plus a full build against a small
fake corpus (no dependency on the real corpus content).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("markdown_it")  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_HELP = REPO_ROOT / "attune-ai-dev" / "build_help.py"


def _load_build_help():
    spec = importlib.util.spec_from_file_location("_build_help", BUILD_HELP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bh = _load_build_help()


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_title_case_dashes_and_underscores(self):
        assert bh._title_case("bug-predict") == "Bug Predict"
        assert bh._title_case("help_system") == "Help System"

    def test_first_para_skips_headings(self):
        assert bh._first_para("# Title\n\nHello world.") == "Hello world."

    def test_first_para_truncates(self):
        body = "x" * 500
        assert len(bh._first_para(body, max_chars=200)) == 200

    def test_crumbs_links_and_plain(self):
        c = bh._crumbs(("Home", "/"), ("Now", None))
        assert '<a href="/">Home</a>' in c
        assert "<span>Now</span>" in c

    def test_crumbs_escapes_label(self):
        c = bh._crumbs(("a<b", None))
        assert "a&lt;b" in c

    def test_page_carries_brand_and_help_css(self):
        page = bh._page(
            title="T",
            desc="D",
            crumbs="C",
            body="<main></main>",
            canonical="https://attune-ai.dev/help",
        )
        assert "<title>T</title>" in page
        assert "--primary" in page  # brand.css token reused
        assert ".help-nav" in page  # help-specific css
        assert "API &amp; contributor docs" in page  # mkdocs cross-link


# ---------------------------------------------------------------------------
# Full build against a fake corpus
# ---------------------------------------------------------------------------


def _fake_corpus(root: Path) -> None:
    demo = root / ".help" / "templates" / "demo"
    demo.mkdir(parents=True)
    (demo / "concept.md").write_text(
        "---\nfeature: demo\ndepth: concept\n---\n\n# Demo\n\nA demo feature.\n",
        encoding="utf-8",
    )
    (demo / "task.md").write_text(
        "---\nfeature: demo\ndepth: task\n---\n\n# Work with demo\n\nDo the thing.\n",
        encoding="utf-8",
    )


def _config_for(tmp_path: Path):
    try:
        from attune.ops.config import Config
    except Exception:  # noqa: BLE001
        pytest.skip("attune.ops not importable in this environment")
    return Config(project_root=tmp_path, attune_home=tmp_path)


class TestBuild:
    def test_build_renders_corpus(self, tmp_path):
        _fake_corpus(tmp_path)
        cfg = _config_for(tmp_path)
        out = tmp_path / "help"

        assert bh.build(out, cfg=cfg) == 0

        assert (out / "index.html").is_file()
        assert (out / "demo" / "index.html").is_file()
        assert (out / "demo" / "concept.html").is_file()
        assert (out / "demo" / "task.html").is_file()
        assert (out / "search.js").is_file()

    def test_kind_page_reuses_brand_and_renders_markdown(self, tmp_path):
        _fake_corpus(tmp_path)
        cfg = _config_for(tmp_path)
        out = tmp_path / "help"
        bh.build(out, cfg=cfg)

        page = (out / "demo" / "concept.html").read_text(encoding="utf-8")
        assert "--primary" in page  # brand reuse
        assert "<h1>Demo</h1>" in page  # markdown rendered
        assert "A demo feature." in page

    def test_search_index_is_well_formed(self, tmp_path):
        _fake_corpus(tmp_path)
        cfg = _config_for(tmp_path)
        out = tmp_path / "help"
        bh.build(out, cfg=cfg)

        idx = json.loads((out / "search-index.json").read_text(encoding="utf-8"))
        assert isinstance(idx, list) and idx
        entry = next(e for e in idx if e["feature"] == "demo" and e["kind"] == "concept")
        assert entry["url"] == "/help/demo/concept"
        assert entry["title"]
        assert "demo" in entry["keywords"]

    def test_empty_corpus_returns_nonzero(self, tmp_path):
        (tmp_path / ".help" / "templates").mkdir(parents=True)
        cfg = _config_for(tmp_path)
        assert bh.build(tmp_path / "help", cfg=cfg) == 1

    def test_check_mode_detects_drift(self, tmp_path):
        _fake_corpus(tmp_path)
        cfg = _config_for(tmp_path)
        out = tmp_path / "help"
        bh.build(out, cfg=cfg)

        # Identical rebuild → no drift.
        scratch = tmp_path / "scratch"
        bh.build(scratch, cfg=cfg)
        assert bh._diff_trees(out, scratch) == []

        # Mutate one page → drift detected.
        (out / "demo" / "concept.html").write_text("tampered", encoding="utf-8")
        drift = bh._diff_trees(out, scratch)
        assert any("changed" in d and "concept.html" in d for d in drift)
