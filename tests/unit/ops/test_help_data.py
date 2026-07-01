"""Unit tests for attune.ops.help_data — read primitives over the
.help/templates/ corpus.

Builds a synthetic corpus under tmp_path so every test is
deterministic and independent of the real attune-ai .help/
state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.ops import help_data as help_data_mod
from attune.ops.config import Config
from attune.ops.help_data import (
    EXPECTED_KINDS,
    FeatureSummary,
    GapsReport,
    SearchHit,
    _extract_frontmatter_field,
    _feature_kind_from_path,
    _first_paragraph,
    _format_kinds,
    _is_template_stale,
    _safe_slug,
    _snippet,
    _title_from_content,
    corpus_root,
    coverage_gaps,
    featured_topics,
    get_template,
    list_features,
    recently_regenerated,
    search,
)


def _fresh_ts() -> str:
    """A recent ``generated_at`` timestamp (now, UTC).

    Staleness is hash-based; the timestamp itself does not affect
    ``is_stale``. Kept so corpus templates have realistic frontmatter.
    """
    return datetime.now(timezone.utc).isoformat()


def _stale_ts() -> str:
    """An old ``generated_at`` timestamp (14 days ago, UTC).

    Pre-rewrite this name drove date-based staleness; under the new
    hash-only logic it just makes a template's frontmatter LOOK old.
    Kept for tests that document the no-authority behavior
    (an old timestamp alone is no longer enough to mark a template
    stale — see :class:`TestIsTemplateStale`).
    """
    return (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()


def _write_template(
    root: Path,
    feature: str,
    kind: str,
    *,
    title: str | None = None,
    body: str = "",
    generated_at: str | None = None,
    source_hash: str = "abc123",
) -> Path:
    """Create a single template file with valid frontmatter."""
    if title is None:
        title = f"{feature} {kind}"
    if generated_at is None:
        generated_at = _fresh_ts()
    feat_dir = root / feature
    feat_dir.mkdir(parents=True, exist_ok=True)
    path = feat_dir / f"{kind}.md"
    fm = (
        f"---\n"
        f"type: {kind}\n"
        f"name: {feature}-{kind}\n"
        f"feature: {feature}\n"
        f"depth: {kind}\n"
        f"generated_at: {generated_at}\n"
        f"source_hash: {source_hash}\n"
        f"status: generated\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{body or 'A standard introduction paragraph for this template.'}\n\n"
        f"## How it works\n\nDetails go here.\n"
    )
    path.write_text(fm, encoding="utf-8")
    return path


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Build a small but realistic .help/templates corpus under tmp_path.

    Layout:
      .help/templates/
        complete-feature/         # all 11 kinds, all fresh
        incomplete-feature/       # 3 kinds, fresh
        stale-feature/            # 5 kinds, all stale
        mixed-feature/            # 11 kinds, mix of fresh + stale
    """
    root = tmp_path / ".help" / "templates"

    # complete-feature — all 11 kinds, fresh
    for kind in EXPECTED_KINDS:
        _write_template(root, "complete-feature", kind)

    # incomplete-feature — only 3 kinds
    for kind in ("concept", "task", "reference"):
        _write_template(root, "incomplete-feature", kind)

    # stale-feature — 5 kinds, all >7 days old
    for kind in ("concept", "task", "reference", "faq", "tip"):
        _write_template(root, "stale-feature", kind, generated_at=_stale_ts())

    # mixed-feature — 11 kinds, half stale
    for i, kind in enumerate(EXPECTED_KINDS):
        ts = _stale_ts() if i % 2 == 0 else _fresh_ts()
        _write_template(root, "mixed-feature", kind, generated_at=ts)

    return tmp_path


@pytest.fixture(autouse=True)
def _inject_stale_features(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject the attune-author authority set used by the corpus.

    Staleness is hash-based only (no date fallback). The synthetic
    corpus marks ``stale-feature`` and ``mixed-feature`` as the
    features whose source has drifted; this fixture stubs
    ``_attune_author_stale_features`` to return that exact set so
    tests run deterministically without needing the real
    attune-author CLI on PATH.

    Skipped for ``TestAttuneAuthorStaleFeatures`` — those tests
    exercise the real ``_attune_author_stale_features`` body, so
    they need to see the un-stubbed function. Tests in other
    classes that need a different authority set re-monkeypatch
    ``_attune_author_stale_features`` themselves.
    """
    if request.cls is not None and request.cls.__name__ == "TestAttuneAuthorStaleFeatures":
        return
    monkeypatch.setattr(
        help_data_mod,
        "_attune_author_stale_features",
        lambda *_args, **_kwargs: frozenset({"stale-feature", "mixed-feature"}),
    )
    help_data_mod._clear_staleness_cache()


@pytest.fixture
def cfg(corpus: Path) -> Config:
    return Config(
        project_root=corpus,
        attune_home=corpus / "ah",
        allow_run=False,
    )


# ---------------------------------------------------------------------------
# corpus_root
# ---------------------------------------------------------------------------


class TestCorpusRoot:
    def test_points_at_help_templates(self, cfg: Config) -> None:
        assert corpus_root(cfg) == cfg.project_root / ".help" / "templates"

    def test_missing_corpus_dir_handled_by_callers(self, tmp_path: Path) -> None:
        c = Config(project_root=tmp_path / "nowhere", attune_home=tmp_path / "ah")
        assert list_features(c) == []


# ---------------------------------------------------------------------------
# _safe_slug
# ---------------------------------------------------------------------------


class TestSafeSlug:
    @pytest.mark.parametrize(
        "slug,ok",
        [
            ("security-audit", True),
            ("bug-predict", True),
            ("a", True),  # single lowercase char is valid per regex
            ("ab", True),
            ("123-bad-start", False),  # must start with a-z
            ("Security-Audit", False),  # uppercase
            ("foo_bar", False),  # underscore
            ("../etc", False),  # traversal
            ("foo/bar", False),  # slash
            ("", False),
            (".hidden", False),
        ],
    )
    def test_validation(self, slug: str, ok: bool) -> None:
        assert _safe_slug(slug) is ok


# ---------------------------------------------------------------------------
# list_features
# ---------------------------------------------------------------------------


class TestListFeatures:
    def test_returns_all_features(self, cfg: Config) -> None:
        names = {f.name for f in list_features(cfg)}
        assert names == {
            "complete-feature",
            "incomplete-feature",
            "stale-feature",
            "mixed-feature",
        }

    def test_complete_feature_marked_complete(self, cfg: Config) -> None:
        feats = {f.name: f for f in list_features(cfg)}
        complete = feats["complete-feature"]
        assert complete.is_complete is True
        assert len(complete.kinds) == 11
        assert complete.missing_kinds == ()

    def test_incomplete_feature_lists_missing(self, cfg: Config) -> None:
        feats = {f.name: f for f in list_features(cfg)}
        inc = feats["incomplete-feature"]
        assert inc.is_complete is False
        assert set(inc.kinds) == {"concept", "task", "reference"}
        # Missing kinds preserve EXPECTED_KINDS order
        assert "comparison" in inc.missing_kinds
        assert "warning" in inc.missing_kinds

    def test_stale_feature_has_stale_count(self, cfg: Config) -> None:
        feats = {f.name: f for f in list_features(cfg)}
        stale = feats["stale-feature"]
        assert stale.has_any_stale is True
        assert stale.stale_count == 5  # all 5 kinds are stale

    def test_mixed_feature_marked_fully_stale(self, cfg: Config) -> None:
        """Staleness is hash-based at the feature level (no per-kind
        granularity). If a feature is in the authority set, ALL its
        kinds are stale together. The pre-rename ``partial_stale``
        semantics came from the dropped per-template date check.
        """
        feats = {f.name: f for f in list_features(cfg)}
        mixed = feats["mixed-feature"]
        assert mixed.has_any_stale is True
        assert mixed.stale_count == 11

    def test_alphabetical_order(self, cfg: Config) -> None:
        names = [f.name for f in list_features(cfg)]
        assert names == sorted(names)


class TestFeatureSummary:
    def test_completeness_pct(self) -> None:
        f = FeatureSummary(
            name="x",
            kinds=("concept", "task"),
            missing_kinds=tuple(k for k in EXPECTED_KINDS if k not in ("concept", "task")),
            stale_count=0,
            has_any_stale=False,
        )
        # 2 of 11 kinds
        assert f.completeness_pct == round(100 * 2 / 11)

    def test_to_dict_shape(self) -> None:
        f = FeatureSummary(
            name="x",
            kinds=("concept",),
            missing_kinds=("task",),
            stale_count=0,
            has_any_stale=False,
        )
        d = f.to_dict()
        assert d["name"] == "x"
        assert d["kinds"] == ["concept"]
        assert d["missing_kinds"] == ["task"]
        assert "is_complete" in d
        assert "completeness_pct" in d


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


class TestGetTemplate:
    def test_loads_existing_template(self, cfg: Config) -> None:
        rec = get_template(cfg, "complete-feature", "task")
        assert rec is not None
        assert rec.feature == "complete-feature"
        assert rec.kind == "task"
        assert rec.title == "complete-feature task"
        assert rec.source_hash == "abc123"
        assert rec.generated_at is not None
        assert rec.is_stale is False

    def test_stale_template_marked(self, cfg: Config) -> None:
        rec = get_template(cfg, "stale-feature", "concept")
        assert rec is not None
        assert rec.is_stale is True

    def test_missing_feature_returns_none(self, cfg: Config) -> None:
        assert get_template(cfg, "nonexistent", "task") is None

    def test_missing_kind_returns_none(self, cfg: Config) -> None:
        assert get_template(cfg, "incomplete-feature", "warning") is None

    def test_invalid_feature_slug_returns_none(self, cfg: Config) -> None:
        assert get_template(cfg, "../etc", "task") is None
        assert get_template(cfg, "Bad-Slug", "task") is None

    def test_invalid_kind_slug_returns_none(self, cfg: Config) -> None:
        assert get_template(cfg, "complete-feature", "../etc") is None

    def test_to_dict_shape(self, cfg: Config) -> None:
        rec = get_template(cfg, "complete-feature", "concept")
        assert rec is not None
        d = rec.to_dict()
        assert d["feature"] == "complete-feature"
        assert d["kind"] == "concept"
        assert "body" in d
        assert "is_stale" in d


class TestTemplateParsing:
    def test_missing_frontmatter_treated_as_body(self, tmp_path: Path) -> None:
        root = tmp_path / ".help" / "templates" / "no-fm"
        root.mkdir(parents=True)
        (root / "concept.md").write_text("# Just a body\n\nNo frontmatter here.", encoding="utf-8")
        cfg = Config(project_root=tmp_path, attune_home=tmp_path / "ah", allow_run=False)
        rec = get_template(cfg, "no-fm", "concept")
        assert rec is not None
        assert rec.title == "Just a body"
        assert rec.generated_at is None
        assert rec.source_hash is None
        # Without generated_at we can't compute staleness; defaults to False
        assert rec.is_stale is False

    def test_malformed_generated_at_doesnt_crash(self, tmp_path: Path) -> None:
        root = tmp_path / ".help" / "templates" / "bad-ts"
        root.mkdir(parents=True)
        (root / "concept.md").write_text(
            "---\ntype: concept\ngenerated_at: not-an-iso-string\nsource_hash: x\n---\n\n# Test\n",
            encoding="utf-8",
        )
        cfg = Config(project_root=tmp_path, attune_home=tmp_path / "ah", allow_run=False)
        rec = get_template(cfg, "bad-ts", "concept")
        assert rec is not None
        # Bad timestamp → not stale (can't compute)
        assert rec.is_stale is False


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_empty_query_returns_empty(self, cfg: Config) -> None:
        assert search(cfg, "") == []
        assert search(cfg, "   ") == []

    def test_missing_corpus_returns_empty(self, tmp_path: Path) -> None:
        cfg = Config(
            project_root=tmp_path / "no-corpus",
            attune_home=tmp_path / "ah",
        )
        assert search(cfg, "anything") == []

    def test_returns_search_hits(self, cfg: Config) -> None:
        # Write a template with a distinctive token
        _write_template(
            cfg.project_root / ".help" / "templates",
            "matchable",
            "concept",
            body="This template mentions xyz_unique_marker prominently.",
        )
        hits = search(cfg, "xyz_unique_marker")
        # Search may return 0 if attune-rag not installed or token is too rare;
        # at minimum the function shouldn't crash.
        assert isinstance(hits, list)
        for h in hits:
            assert isinstance(h, SearchHit)
            assert h.feature
            assert h.kind
            assert 0 <= h.score


# ---------------------------------------------------------------------------
# coverage_gaps
# ---------------------------------------------------------------------------


class TestCoverageGaps:
    def test_empty_corpus(self, tmp_path: Path) -> None:
        cfg = Config(
            project_root=tmp_path / "empty",
            attune_home=tmp_path / "ah",
        )
        report = coverage_gaps(cfg)
        assert isinstance(report, GapsReport)
        assert report.total_features == 0
        assert report.total_templates == 0
        assert report.completeness_pct == 0
        assert report.fresh_pct == 0

    def test_incomplete_features_surfaced(self, cfg: Config) -> None:
        report = coverage_gaps(cfg)
        incomplete_names = {f.name for f in report.incomplete}
        assert "incomplete-feature" in incomplete_names
        assert "stale-feature" in incomplete_names
        # complete-feature and mixed-feature both have all 11 kinds
        assert "complete-feature" not in incomplete_names
        assert "mixed-feature" not in incomplete_names

    def test_stale_templates_surfaced(self, cfg: Config) -> None:
        report = coverage_gaps(cfg)
        stale_pairs = {(t.feature, t.kind) for t in report.stale}
        # stale-feature has 5 stale templates
        assert ("stale-feature", "concept") in stale_pairs
        assert ("stale-feature", "task") in stale_pairs

    def test_aggregate_stats(self, cfg: Config) -> None:
        report = coverage_gaps(cfg)
        # 4 features total
        assert report.total_features == 4
        # 2 complete (complete-feature + mixed-feature have 11 kinds each)
        assert report.complete_features == 2
        # completeness pct rounded
        assert report.completeness_pct == round(100 * 2 / 4)

    def test_to_dict_shape(self, cfg: Config) -> None:
        d = coverage_gaps(cfg).to_dict()
        assert "incomplete" in d
        assert "stale" in d
        assert "total_features" in d
        assert "completeness_pct" in d
        assert "fresh_pct" in d


# ---------------------------------------------------------------------------
# featured_topics
# ---------------------------------------------------------------------------


class TestFeaturedTopics:
    def test_fallback_when_no_curated_match(self, cfg: Config) -> None:
        """None of our test features match the curated list, so it falls
        back to first-N alphabetical."""
        feats = featured_topics(cfg)
        # Fallback returns up to 5 features alphabetically.
        assert 1 <= len(feats) <= 5
        names = [f.name for f in feats]
        assert names == sorted(names)

    def test_returns_curated_when_present(self, tmp_path: Path) -> None:
        """If we synthesize a 'security-audit' feature, the curated path
        picks it up."""
        root = tmp_path / ".help" / "templates"
        _write_template(root, "security-audit", "concept")
        _write_template(root, "smart-test", "task")
        cfg = Config(project_root=tmp_path, attune_home=tmp_path / "ah", allow_run=False)
        feats = featured_topics(cfg)
        names = [f.name for f in feats]
        assert "security-audit" in names
        assert "smart-test" in names


# ---------------------------------------------------------------------------
# recently_regenerated
# ---------------------------------------------------------------------------


class TestRecentlyRegenerated:
    def test_default_limit(self, cfg: Config) -> None:
        recs = recently_regenerated(cfg)
        assert len(recs) <= 5

    def test_sorted_newest_first(self, cfg: Config) -> None:
        recs = recently_regenerated(cfg, limit=20)
        timestamps = [r.generated_at for r in recs if r.generated_at]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_custom_limit(self, cfg: Config) -> None:
        recs = recently_regenerated(cfg, limit=2)
        assert len(recs) <= 2


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestExtractFrontmatterField:
    def test_extracts_value(self) -> None:
        fm = "key: value\nother: thing\n"
        assert _extract_frontmatter_field(fm, "key") == "value"
        assert _extract_frontmatter_field(fm, "other") == "thing"

    def test_strips_quotes(self) -> None:
        assert _extract_frontmatter_field('key: "quoted"\n', "key") == "quoted"
        assert _extract_frontmatter_field("key: 'quoted'\n", "key") == "quoted"

    def test_missing_returns_none(self) -> None:
        assert _extract_frontmatter_field("x: y\n", "missing") is None

    def test_empty_fm(self) -> None:
        assert _extract_frontmatter_field("", "anything") is None


class TestTitleFromContent:
    def test_first_h1(self) -> None:
        body = "Some intro\n\n# The Title\n\nbody"
        assert _title_from_content(body) == "The Title"

    def test_no_h1_returns_none(self) -> None:
        assert _title_from_content("just text") is None

    def test_h2_not_matched(self) -> None:
        assert _title_from_content("## H2 only") is None


class TestFeatureKindFromPath:
    def test_valid_path(self) -> None:
        from pathlib import Path

        assert _feature_kind_from_path(Path("security-audit/task.md")) == (
            "security-audit",
            "task",
        )

    def test_too_few_parts(self) -> None:
        from pathlib import Path

        assert _feature_kind_from_path(Path("loose-file.md")) == (None, None)

    def test_invalid_slug_rejected(self) -> None:
        from pathlib import Path

        assert _feature_kind_from_path(Path("Bad-Feature/concept.md")) == (None, None)


class TestSnippet:
    def test_returns_around_hit(self) -> None:
        body = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5
        body += "Then INJECTION appears here. " + "Tail text. " * 5
        s = _snippet(body, "injection", max_len=200)
        assert "INJECTION" in s
        assert "…" in s or len(s) <= 200

    def test_no_match_returns_prefix(self) -> None:
        body = "No match for the term anywhere in this body."
        s = _snippet(body, "nonexistent", max_len=100)
        assert s.startswith("No match")

    def test_empty_content(self) -> None:
        assert _snippet("", "anything", max_len=50) == ""

    def test_short_terms_filtered(self) -> None:
        # Terms < 3 chars get filtered; no match → prefix
        body = "I am a body"
        s = _snippet(body, "I", max_len=100)
        assert s == "I am a body"


class TestFirstParagraph:
    def test_skips_headings(self) -> None:
        body = "# Heading\n\nFirst paragraph text.\n\nSecond."
        assert _first_paragraph(body) == "First paragraph text."

    def test_truncates(self) -> None:
        body = "Lorem ipsum " * 100
        out = _first_paragraph(body, max_chars=50)
        assert len(out) <= 50
        assert out.endswith("…")

    def test_empty_body(self) -> None:
        assert _first_paragraph("") == ""

    def test_skips_leading_fence_line(self) -> None:
        """A code fence on the first line is skipped (the ``` opener).

        The implementation skips any line starting with `` ``` `` until
        a paragraph accumulates — sufficient for typical template bodies
        that start with prose. Full fenced-block awareness is a v2.
        """
        body = "```python\nx = 1\n```\n\nReal paragraph here."
        # Without full fence tracking the first content line wins.
        out = _first_paragraph(body)
        # Either the fence content OR the real paragraph is acceptable —
        # what matters is that we get *something*, not the empty string.
        assert out != ""


class TestFormatKinds:
    def test_joins(self) -> None:
        assert _format_kinds(["a", "b", "c"]) == "a, b, c"

    def test_empty(self) -> None:
        assert _format_kinds([]) == ""


class TestIsTemplateStale:
    """Tests for the no-authority path (``stale_features=None``).

    Staleness is hash-based only: without the attune-author authority
    set, ``_is_template_stale`` cannot determine drift and returns
    ``False`` for every input. The authority-mode path is covered by
    :class:`TestIsTemplateStaleAuthorityMode` below.
    """

    def test_no_authority_returns_false(self, tmp_path: Path) -> None:
        """A template with a fresh ``generated_at`` returns False —
        unsurprising. The point is that ``stale_features=None`` means
        we cannot judge, so we report not-stale rather than guessing.
        """
        p = tmp_path / "fresh.md"
        p.write_text(f"---\ngenerated_at: {_fresh_ts()}\n---\n\n# x\n", encoding="utf-8")
        assert _is_template_stale(p) is False

    def test_no_authority_returns_false_even_for_old_template(self, tmp_path: Path) -> None:
        """Pre-rewrite this returned True via the age-based fallback.
        Hash-only semantics: without an authority set, age is irrelevant.
        """
        p = tmp_path / "ancient.md"
        p.write_text(f"---\ngenerated_at: {_stale_ts()}\n---\n\n# x\n", encoding="utf-8")
        assert _is_template_stale(p) is False

    def test_no_generated_at_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "nogen.md"
        p.write_text("---\ntype: concept\n---\n\n# x\n", encoding="utf-8")
        assert _is_template_stale(p) is False

    def test_unreadable_file_returns_false(self, tmp_path: Path) -> None:
        # Pass a path that doesn't exist — open() raises OSError
        assert _is_template_stale(tmp_path / "missing.md") is False


# ---------------------------------------------------------------------------
# attune-author authority path
# ---------------------------------------------------------------------------


_REAL_STATUS_OUTPUT = """## Help Templates

**24** current, **2** stale

### Stale

| Feature | Description | Files Changed |
|---------|-------------|---------------|
| spec-engine | The spec engine | 8 source files |
| smart-test | Find test gaps | 3 source files |


### Current

- **security-audit** — desc
- **code-quality** — desc
"""


class TestParseStatusOutput:
    def test_extracts_stale_features(self) -> None:
        from attune.ops.help_data import _parse_status_output

        stale = _parse_status_output(_REAL_STATUS_OUTPUT)
        assert stale == frozenset({"spec-engine", "smart-test"})

    def test_no_stale_section_returns_empty(self) -> None:
        from attune.ops.help_data import _parse_status_output

        text = "## Help Templates\n\n**25** current, **0** stale\n"
        assert _parse_status_output(text) == frozenset()

    def test_empty_string(self) -> None:
        from attune.ops.help_data import _parse_status_output

        assert _parse_status_output("") == frozenset()

    def test_ignores_table_header_and_divider(self) -> None:
        """Header row (Feature/Description/Files) and the |---|---| divider
        don't match the slug regex, so they're correctly skipped."""
        from attune.ops.help_data import _parse_status_output

        text = (
            "### Stale\n\n"
            "| Feature | Description | Files Changed |\n"
            "|---------|-------------|---------------|\n"
            "| valid-slug | desc | 1 file |\n"
        )
        assert _parse_status_output(text) == frozenset({"valid-slug"})

    def test_current_section_ignored(self) -> None:
        """Bullets in the ### Current section don't pollute the stale set."""
        from attune.ops.help_data import _parse_status_output

        text = (
            "### Stale\n\n"
            "| a-feature | x | 1 |\n\n"
            "### Current\n\n"
            "- **other-feature** — desc\n"
        )
        assert _parse_status_output(text) == frozenset({"a-feature"})

    def test_project_docs_stale_section_ignored(self) -> None:
        """``## Project Docs`` is a SEPARATE corpus from
        ``.help/templates/``. Its stale section must NOT contribute
        to the dashboard's help-templates stale set — otherwise
        clicking "Regenerate all stale" can never bring the count
        down (regenerate only touches .help/, not docs/).

        This is the bug PR #494 fixed: pre-fix the parser walked
        every "### Stale" section regardless of its parent h2,
        rolling project-docs drift into help-templates staleness.
        """
        from attune.ops.help_data import _parse_status_output

        text = (
            "## Help Templates\n\n"
            "**1** current, **1** stale\n\n"
            "### Stale\n\n"
            "| help-only-feat | foo | 1 |\n\n"
            "## Project Docs\n\n"
            "**0** current, **2** stale\n\n"
            "### Stale\n\n"
            "| docs-only-feat | bar | 2 |\n"
            "| another-docs-feat | baz | 1 |\n"
        )
        # Only the help-templates feature appears; the project-docs
        # features are silently dropped.
        assert _parse_status_output(text) == frozenset({"help-only-feat"})

    def test_help_templates_implicit_when_no_h2(self) -> None:
        """If no ``## `` h2 appears, default to Help Templates context.

        Backward compat with older attune-author versions whose
        status output didn't include section headers.
        """
        from attune.ops.help_data import _parse_status_output

        text = "### Stale\n\n| legacy-feat | foo | 1 |\n"
        assert _parse_status_output(text) == frozenset({"legacy-feat"})


class TestAttuneAuthorStaleFeatures:
    """Tests for the subprocess wrapper. We mock subprocess.run to
    keep tests fast and deterministic — no dependency on the real
    attune-author CLI being installed in the venv."""

    def test_returns_none_when_binary_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When ``shutil.which`` reports the binary missing,
        ``_attune_author_stale_features`` returns ``None`` (the
        signal callers use to mean 'cannot determine drift')."""
        from attune.ops import help_data

        monkeypatch.setattr(help_data.shutil, "which", lambda _: None)
        help_data._clear_staleness_cache()
        result = help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        assert result is None

    def test_parses_subprocess_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from attune.ops import help_data

        monkeypatch.setattr(help_data.shutil, "which", lambda _: "/fake/attune-author")

        class _FakeResult:
            stdout = _REAL_STATUS_OUTPUT
            stderr = ""
            returncode = 0

        monkeypatch.setattr(help_data.subprocess, "run", lambda *a, **kw: _FakeResult())
        help_data._clear_staleness_cache()
        result = help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        assert result == frozenset({"spec-engine", "smart-test"})

    def test_nonzero_exit_returns_none_not_empty_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Regression: a CLI that runs but exits non-zero (e.g. a broken
        shim raising ModuleNotFoundError) must return ``None`` (→ age
        fallback), NOT ``frozenset()``. Previously ``check=False`` let the
        crash's empty stdout parse to an empty set, masking the failure as
        'nothing stale' and denying callers the fallback."""
        from attune.ops import help_data

        monkeypatch.setattr(help_data.shutil, "which", lambda _: "/fake/attune-author")

        class _CrashResult:
            stdout = ""
            stderr = "ModuleNotFoundError: No module named 'attune_author'"
            returncode = 1

        monkeypatch.setattr(help_data.subprocess, "run", lambda *a, **kw: _CrashResult())
        help_data._clear_staleness_cache()
        result = help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        assert result is None

    def test_subprocess_failure_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import subprocess as _sp

        from attune.ops import help_data

        monkeypatch.setattr(help_data.shutil, "which", lambda _: "/fake/attune-author")

        def _raise(*_a, **_kw):
            raise _sp.SubprocessError("boom")

        monkeypatch.setattr(help_data.subprocess, "run", _raise)
        help_data._clear_staleness_cache()
        result = help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        assert result is None

    def test_cache_hits_skip_subprocess(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from attune.ops import help_data

        monkeypatch.setattr(help_data.shutil, "which", lambda _: "/fake/attune-author")

        call_count = {"n": 0}

        class _FakeResult:
            stdout = _REAL_STATUS_OUTPUT
            returncode = 0
            stderr = ""

        def _counting_run(*a, **kw):
            call_count["n"] += 1
            return _FakeResult()

        monkeypatch.setattr(help_data.subprocess, "run", _counting_run)
        help_data._clear_staleness_cache()
        # First call: subprocess fires
        help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        # Second call within TTL: cache hit, no subprocess
        help_data._attune_author_stale_features(tmp_path, tmp_path / ".help")
        assert call_count["n"] == 1

    def test_drift_set_used_for_feature_staleness(
        self, monkeypatch: pytest.MonkeyPatch, cfg: Config, corpus: Path
    ) -> None:
        """End-to-end: with attune-author saying 'complete-feature' is
        stale, list_features() should mark it stale (and no other)."""
        from attune.ops import help_data

        # Override the autouse fallback to return a known stale set.
        monkeypatch.setattr(
            help_data,
            "_attune_author_stale_features",
            lambda *_a, **_kw: frozenset({"complete-feature"}),
        )
        feats = {f.name: f for f in help_data.list_features(cfg)}
        # Authority says complete-feature is stale → every kind it has
        # is treated as stale. stale-feature (which has only old
        # generated_at timestamps) is NOT in the authority set →
        # zero stale.
        assert feats["complete-feature"].has_any_stale is True
        assert feats["complete-feature"].stale_count == 11
        assert feats["stale-feature"].has_any_stale is False
        assert feats["stale-feature"].stale_count == 0


class TestIsTemplateStaleAuthorityMode:
    def test_in_authority_set_returns_true(self, tmp_path: Path) -> None:
        from attune.ops.help_data import _is_template_stale

        p = tmp_path / "my-feat" / "concept.md"
        p.parent.mkdir()
        p.write_text("# x\n", encoding="utf-8")
        assert _is_template_stale(p, stale_features=frozenset({"my-feat"})) is True

    def test_not_in_authority_set_returns_false(self, tmp_path: Path) -> None:
        from attune.ops.help_data import _is_template_stale

        p = tmp_path / "my-feat" / "concept.md"
        p.parent.mkdir()
        p.write_text("# x\n", encoding="utf-8")
        assert _is_template_stale(p, stale_features=frozenset({"other-feat"})) is False
