"""Tests for attune_help.staleness."""

from __future__ import annotations

from pathlib import Path

from attune.authoring.manifest import Feature, FeatureManifest
from attune.authoring.staleness import (
    DocStaleness,
    FeatureStaleness,
    StalenessReport,
    build_doc_footer,
    check_staleness,
    compute_source_hash,
    parse_doc_footer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(*features: Feature) -> FeatureManifest:
    return FeatureManifest(version=1, features={f.name: f for f in features})


def _write_src(root: Path, rel: str, content: str = "# code") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _write_concept(help_dir: Path, feature: str, source_hash: str) -> Path:
    p = help_dir / "templates" / feature / "concept.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"---\nsource_hash: {source_hash}\n---\n\n# Concept\n",
        encoding="utf-8",
    )
    return p


def _write_doc(root: Path, rel: str, source_hash: str, feature: str, kind: str) -> Path:
    footer = build_doc_footer(
        source_hash=source_hash,
        feature=feature,
        kind=kind,
        generated_at="2026-04-23",
    )
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Doc\n\nContent here.\n\n{footer}\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parse_doc_footer
# ---------------------------------------------------------------------------


def test_parse_doc_footer_present():
    text = (
        "# Title\n\nSome content.\n\n"
        "<!-- attune-generated: source_hash=abc123 feature=foo "
        "kind=how-to generated_at=2026-04-23 -->"
    )
    attrs = parse_doc_footer(text)
    assert attrs["source_hash"] == "abc123"
    assert attrs["feature"] == "foo"
    assert attrs["kind"] == "how-to"
    assert attrs["generated_at"] == "2026-04-23"


def test_parse_doc_footer_absent():
    assert parse_doc_footer("# No footer here\n") == {}


def test_parse_doc_footer_partial_comment():
    text = "<!-- something else -->"
    assert parse_doc_footer(text) == {}


# ---------------------------------------------------------------------------
# build_doc_footer
# ---------------------------------------------------------------------------


def test_build_doc_footer_round_trips():
    footer = build_doc_footer("deadbeef", "auth", "how-to", "2026-04-23")
    attrs = parse_doc_footer(footer)
    assert attrs["source_hash"] == "deadbeef"
    assert attrs["feature"] == "auth"
    assert attrs["kind"] == "how-to"
    assert attrs["generated_at"] == "2026-04-23"


def test_build_doc_footer_is_single_line():
    footer = build_doc_footer("h", "f", "k", "d")
    assert "\n" not in footer


# ---------------------------------------------------------------------------
# compute_source_hash
# ---------------------------------------------------------------------------


def test_compute_source_hash_basic(tmp_path: Path):
    _write_src(tmp_path, "src/auth/login.py", "def login(): pass")
    feat = Feature(name="auth", description="Auth", files=["src/auth/**"])
    digest, matched = compute_source_hash(feat, tmp_path)
    assert len(digest) == 64  # sha256 hex
    assert "src/auth/login.py" in matched


def test_compute_source_hash_empty_globs(tmp_path: Path):
    feat = Feature(name="nothing", description="", files=[])
    digest, matched = compute_source_hash(feat, tmp_path)
    assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert matched == []


def test_compute_source_hash_excludes_pycache(tmp_path: Path):
    _write_src(tmp_path, "src/auth/login.py", "code")
    _write_src(tmp_path, "src/auth/__pycache__/login.cpython-311.pyc", "bytecode")
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    _, matched = compute_source_hash(feat, tmp_path)
    assert all("__pycache__" not in p for p in matched)


def test_compute_source_hash_deterministic(tmp_path: Path):
    _write_src(tmp_path, "src/a.py", "x")
    _write_src(tmp_path, "src/b.py", "y")
    feat = Feature(name="f", description="", files=["src/**"])
    h1, _ = compute_source_hash(feat, tmp_path)
    h2, _ = compute_source_hash(feat, tmp_path)
    assert h1 == h2


def test_compute_source_hash_changes_on_edit(tmp_path: Path):
    f = _write_src(tmp_path, "src/auth/login.py", "def login(name: str) -> str:\n    return name\n")
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    h1, _ = compute_source_hash(feat, tmp_path)
    f.write_text(
        "def login(name: str, password: str) -> bool:\n    return True\n", encoding="utf-8"
    )
    h2, _ = compute_source_hash(feat, tmp_path)
    assert h1 != h2


def test_compute_source_hash_stable_across_docstring_edit(tmp_path: Path):
    """Semantic hashing: docstring-only edits do not trigger staleness."""
    f = _write_src(
        tmp_path,
        "src/auth/login.py",
        'def login(name: str) -> str:\n    """Log in."""\n    return name\n',
    )
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    h1, _ = compute_source_hash(feat, tmp_path)
    f.write_text(
        "def login(name: str) -> str:\n"
        '    """Very detailed login documentation."""\n'
        "    return name\n",
        encoding="utf-8",
    )
    h2, _ = compute_source_hash(feat, tmp_path)
    assert h1 == h2


def test_compute_source_hash_changes_on_signature_edit(tmp_path: Path):
    """Semantic hashing: adding a parameter changes the hash."""
    f = _write_src(tmp_path, "src/auth/login.py", "def login(name: str) -> str:\n    return name\n")
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    h1, _ = compute_source_hash(feat, tmp_path)
    f.write_text("def login(name: str, password: str) -> str:\n    return name\n", encoding="utf-8")
    h2, _ = compute_source_hash(feat, tmp_path)
    assert h1 != h2


# ---------------------------------------------------------------------------
# check_staleness — help templates
# ---------------------------------------------------------------------------


def test_check_staleness_help_fresh(tmp_path: Path):
    _write_src(tmp_path, "src/auth/login.py", "def login(): ...")
    help_dir = tmp_path / ".help"
    feat = Feature(name="auth", description="Auth", files=["src/auth/**"])
    manifest = _make_manifest(feat)
    current_hash, _ = compute_source_hash(feat, tmp_path)
    _write_concept(help_dir, "auth", current_hash)

    report = check_staleness(manifest, help_dir, tmp_path)
    assert len(report.help_entries) == 1
    entry = report.help_entries[0]
    assert entry.feature == "auth"
    assert not entry.is_stale
    assert entry.stored_hash == current_hash


def test_check_staleness_help_stale(tmp_path: Path):
    _write_src(tmp_path, "src/auth/login.py", "updated code")
    help_dir = tmp_path / ".help"
    _write_concept(help_dir, "auth", "oldhashabc123")
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    manifest = _make_manifest(feat)

    report = check_staleness(manifest, help_dir, tmp_path)
    entry = report.help_entries[0]
    assert entry.is_stale
    assert entry.stored_hash == "oldhashabc123"


def test_check_staleness_help_missing_concept(tmp_path: Path):
    _write_src(tmp_path, "src/auth/login.py", "code")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(name="auth", description="", files=["src/auth/**"])
    manifest = _make_manifest(feat)

    report = check_staleness(manifest, help_dir, tmp_path)
    entry = report.help_entries[0]
    assert entry.is_stale
    assert entry.stored_hash is None


# ---------------------------------------------------------------------------
# check_staleness — project docs
# ---------------------------------------------------------------------------


def test_check_staleness_doc_fresh(tmp_path: Path):
    _write_src(tmp_path, "src/foo/main.py", "# foo")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="foo",
        description="Foo",
        files=["src/foo/**"],
        doc_kinds=["how-to"],
        doc_path="docs/how-to/foo.md",
    )
    manifest = _make_manifest(feat)
    current_hash, _ = compute_source_hash(feat, tmp_path)
    _write_concept(help_dir, "foo", current_hash)
    _write_doc(tmp_path, "docs/how-to/foo.md", current_hash, "foo", "how-to")

    report = check_staleness(manifest, help_dir, tmp_path)
    assert len(report.doc_entries) == 1
    doc = report.doc_entries[0]
    assert doc.feature == "foo"
    assert doc.kind == "how-to"
    assert not doc.is_stale
    assert not doc.missing


def test_check_staleness_doc_stale_hash(tmp_path: Path):
    _write_src(tmp_path, "src/foo/main.py", "# foo updated")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="foo",
        description="Foo",
        files=["src/foo/**"],
        doc_path="docs/how-to/foo.md",
    )
    manifest = _make_manifest(feat)
    _write_concept(help_dir, "foo", "stale_hash")
    _write_doc(tmp_path, "docs/how-to/foo.md", "stale_hash", "foo", "how-to")

    report = check_staleness(manifest, help_dir, tmp_path)
    doc = report.doc_entries[0]
    assert doc.is_stale
    assert not doc.missing
    assert doc.stored_hash == "stale_hash"


def test_check_staleness_doc_missing(tmp_path: Path):
    _write_src(tmp_path, "src/foo/main.py", "# foo")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="foo",
        description="Foo",
        files=["src/foo/**"],
        doc_path="docs/how-to/foo.md",
    )
    manifest = _make_manifest(feat)

    report = check_staleness(manifest, help_dir, tmp_path)
    doc = report.doc_entries[0]
    assert doc.is_stale
    assert doc.missing
    assert doc.stored_hash is None


def test_check_staleness_arch_path(tmp_path: Path):
    _write_src(tmp_path, "src/foo/main.py", "code")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="foo",
        description="Foo",
        files=["src/foo/**"],
        doc_path="docs/how-to/foo.md",
        arch_path="docs/architecture/foo.md",
    )
    manifest = _make_manifest(feat)
    current_hash, _ = compute_source_hash(feat, tmp_path)
    _write_doc(tmp_path, "docs/how-to/foo.md", current_hash, "foo", "how-to")
    _write_doc(tmp_path, "docs/architecture/foo.md", current_hash, "foo", "architecture")

    report = check_staleness(manifest, help_dir, tmp_path)
    assert len(report.doc_entries) == 2
    kinds = {d.kind for d in report.doc_entries}
    assert "how-to" in kinds
    assert "architecture" in kinds


def test_check_staleness_no_doc_fields_no_doc_entries(tmp_path: Path):
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(name="plain", description="", files=[])
    manifest = _make_manifest(feat)

    report = check_staleness(manifest, help_dir, tmp_path)
    assert report.doc_entries == []


# ---------------------------------------------------------------------------
# StalenessReport aggregates
# ---------------------------------------------------------------------------


def test_staleness_report_counts():
    report = StalenessReport(
        help_entries=[
            FeatureStaleness("a", is_stale=True, current_hash="x", stored_hash=None),
            FeatureStaleness("b", is_stale=False, current_hash="y", stored_hash="y"),
        ],
        doc_entries=[
            DocStaleness(
                "a",
                "docs/a.md",
                "how-to",
                is_stale=True,
                missing=False,
                current_hash="x",
            ),
        ],
    )
    assert report.stale_count == 2
    assert report.current_count == 1
    assert report.stale_features == ["a"]
    assert len(report.stale_docs) == 1


def test_staleness_report_filter_features(tmp_path: Path):
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat_a = Feature(name="a", description="", files=[])
    feat_b = Feature(name="b", description="", files=[])
    manifest = _make_manifest(feat_a, feat_b)

    report = check_staleness(manifest, help_dir, tmp_path, features=["a"])
    assert len(report.help_entries) == 1
    assert report.help_entries[0].feature == "a"


def test_check_staleness_unknown_feature_skipped(tmp_path: Path):
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(name="known", description="", files=[])
    manifest = _make_manifest(feat)

    report = check_staleness(manifest, help_dir, tmp_path, features=["unknown"])
    assert report.help_entries == []
    assert report.doc_entries == []


def test_check_staleness_iterates_multiple_doc_paths(tmp_path: Path):
    """A feature with ``doc_paths=[a, b, c]`` produces three doc_entries.

    Locks in the staleness change that iterates the full list rather
    than reading only the primary ``doc_path``.
    """
    _write_src(tmp_path, "src/memory/main.py", "# memory")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="memory",
        description="Memory",
        files=["src/memory/**"],
        doc_kinds=["how-to"],
        doc_paths=[
            "docs/how-to/memory-graph.md",
            "docs/how-to/unified-memory-system.md",
            "docs/how-to/short-term-memory-implementation.md",
        ],
    )
    manifest = _make_manifest(feat)
    current_hash, _ = compute_source_hash(feat, tmp_path)
    _write_concept(help_dir, "memory", current_hash)
    # First two docs fresh; third missing on disk.
    _write_doc(tmp_path, "docs/how-to/memory-graph.md", current_hash, "memory", "how-to")
    _write_doc(
        tmp_path,
        "docs/how-to/unified-memory-system.md",
        current_hash,
        "memory",
        "how-to",
    )

    report = check_staleness(manifest, help_dir, tmp_path)
    assert len(report.doc_entries) == 3
    paths = {d.doc_path: d for d in report.doc_entries}
    assert paths["docs/how-to/memory-graph.md"].is_stale is False
    assert paths["docs/how-to/unified-memory-system.md"].is_stale is False
    assert paths["docs/how-to/short-term-memory-implementation.md"].missing is True


def test_check_staleness_one_stale_doc_among_many(tmp_path: Path):
    """When N doc_paths exist and only one's hash drifts, only that one is stale."""
    _write_src(tmp_path, "src/memory/main.py", "# memory")
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    feat = Feature(
        name="memory",
        description="Memory",
        files=["src/memory/**"],
        doc_paths=["docs/a.md", "docs/b.md"],
    )
    manifest = _make_manifest(feat)
    current_hash, _ = compute_source_hash(feat, tmp_path)
    _write_concept(help_dir, "memory", current_hash)
    _write_doc(tmp_path, "docs/a.md", current_hash, "memory", "how-to")
    _write_doc(tmp_path, "docs/b.md", "stale_hash", "memory", "how-to")

    report = check_staleness(manifest, help_dir, tmp_path)
    stale = [d for d in report.doc_entries if d.is_stale]
    current = [d for d in report.doc_entries if not d.is_stale]
    assert len(stale) == 1
    assert stale[0].doc_path == "docs/b.md"
    assert len(current) == 1
    assert current[0].doc_path == "docs/a.md"
