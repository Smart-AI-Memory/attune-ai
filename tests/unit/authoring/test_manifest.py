"""Tests for attune_help.manifest."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.authoring.manifest import (
    Feature,
    FeatureManifest,
    is_safe_feature_name,
    load_manifest,
    match_files_to_features,
    resolve_topic,
    save_manifest,
    slugify,
)

# ---------------------------------------------------------------------------
# is_safe_feature_name
# ---------------------------------------------------------------------------


def test_safe_name_accepts_simple():
    assert is_safe_feature_name("authentication") is True


def test_safe_name_accepts_hyphenated():
    assert is_safe_feature_name("memory-storage") is True


def test_safe_name_rejects_slash():
    assert is_safe_feature_name("a/b") is False


def test_safe_name_rejects_backslash():
    assert is_safe_feature_name("a\\b") is False


def test_safe_name_rejects_dotdot():
    assert is_safe_feature_name("../etc") is False


def test_safe_name_rejects_null_byte():
    assert is_safe_feature_name("foo\x00bar") is False


def test_safe_name_rejects_empty():
    assert is_safe_feature_name("") is False


def test_safe_name_rejects_non_string():
    assert is_safe_feature_name(42) is False  # type: ignore[arg-type]
    assert is_safe_feature_name(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# load_manifest
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / ".help" / "features.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(content, encoding="utf-8")
    return tmp_path / ".help"


def test_load_manifest_basic(tmp_path: Path):
    help_dir = _write_yaml(
        tmp_path,
        """\
version: 1
features:
  auth:
    description: Authentication module
    files:
      - src/auth/**
    tags:
      - login
""",
    )
    manifest = load_manifest(help_dir)
    assert manifest.version == 1
    assert "auth" in manifest.features
    feat = manifest.features["auth"]
    assert feat.description == "Authentication module"
    assert feat.files == ["src/auth/**"]
    assert feat.tags == ["login"]


def test_load_manifest_doc_fields(tmp_path: Path):
    help_dir = _write_yaml(
        tmp_path,
        """\
version: 1
features:
  foo:
    description: Foo module
    files:
      - src/attune/foo/**
    doc_kinds:
      - how-to
      - architecture
    doc_path: docs/how-to/foo.md
    arch_path: docs/architecture/foo-architecture.md
    doc_nav_section: "How-to > Advanced"
""",
    )
    manifest = load_manifest(help_dir)
    feat = manifest.features["foo"]
    assert feat.doc_kinds == ["how-to", "architecture"]
    assert feat.doc_path == "docs/how-to/foo.md"
    assert feat.arch_path == "docs/architecture/foo-architecture.md"
    assert feat.doc_nav_section == "How-to > Advanced"


def test_load_manifest_missing_doc_fields_defaults_none(tmp_path: Path):
    help_dir = _write_yaml(
        tmp_path,
        """\
version: 1
features:
  bar:
    description: Bar module
""",
    )
    manifest = load_manifest(help_dir)
    feat = manifest.features["bar"]
    assert feat.doc_kinds == []
    assert feat.doc_path is None
    assert feat.arch_path is None
    assert feat.doc_nav_section is None


def test_load_manifest_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / ".help")


def test_load_manifest_invalid_yaml_raises(tmp_path: Path):
    help_dir = _write_yaml(tmp_path, "not a mapping at all")
    with pytest.raises(ValueError, match="expected mapping"):
        load_manifest(help_dir)


def test_load_manifest_invalid_feature_name_raises(tmp_path: Path):
    help_dir = _write_yaml(
        tmp_path,
        """\
version: 1
features:
  ../evil:
    description: bad
""",
    )
    with pytest.raises(ValueError, match="Invalid feature name"):
        load_manifest(help_dir)


# ---------------------------------------------------------------------------
# save_manifest / round-trip
# ---------------------------------------------------------------------------


def test_save_and_reload_manifest(tmp_path: Path):
    help_dir = tmp_path / ".help"
    manifest = FeatureManifest(
        version=1,
        features={
            "auth": Feature(
                name="auth",
                description="Auth module",
                files=["src/auth/**"],
                tags=["login"],
                doc_kinds=["how-to"],
                doc_path="docs/how-to/auth.md",
                arch_path=None,
                doc_nav_section="How-to",
            )
        },
    )
    save_manifest(manifest, help_dir)
    reloaded = load_manifest(help_dir)
    feat = reloaded.features["auth"]
    assert feat.doc_kinds == ["how-to"]
    assert feat.doc_path == "docs/how-to/auth.md"
    assert feat.doc_nav_section == "How-to"


def test_save_omits_empty_doc_fields(tmp_path: Path):
    help_dir = tmp_path / ".help"
    manifest = FeatureManifest(
        version=1,
        features={"plain": Feature(name="plain", description="No docs")},
    )
    save_manifest(manifest, help_dir)
    yaml_text = (help_dir / "features.yaml").read_text(encoding="utf-8")
    assert "doc_kinds" not in yaml_text
    assert "doc_path" not in yaml_text


# ---------------------------------------------------------------------------
# match_files_to_features
# ---------------------------------------------------------------------------


def _manifest_with(*features: tuple[str, list[str]]) -> FeatureManifest:
    feats = {
        name: Feature(name=name, description=name, files=patterns) for name, patterns in features
    }
    return FeatureManifest(version=1, features=feats)


def test_match_files_single_feature():
    manifest = _manifest_with(("auth", ["src/auth/*.py"]))
    result = match_files_to_features(["src/auth/login.py"], manifest)
    assert result == {"auth": ["src/auth/login.py"]}


def test_match_files_no_match():
    manifest = _manifest_with(("auth", ["src/auth/*.py"]))
    result = match_files_to_features(["src/other/foo.py"], manifest)
    assert result == {}


def test_match_files_double_star():
    manifest = _manifest_with(("mem", ["src/mem/**"]))
    result = match_files_to_features(["src/mem/store/redis.py"], manifest)
    assert result == {"mem": ["src/mem/store/redis.py"]}


# ---------------------------------------------------------------------------
# resolve_topic
# ---------------------------------------------------------------------------


def _simple_manifest() -> FeatureManifest:
    return FeatureManifest(
        version=1,
        features={
            "auth": Feature(
                name="auth",
                description="Authentication and login",
                tags=["login", "session"],
            ),
            "memory": Feature(
                name="memory",
                description="Persistent memory storage",
                tags=["redis", "cache"],
            ),
        },
    )


def test_resolve_exact():
    assert resolve_topic("auth", _simple_manifest()) == "auth"


def test_resolve_substring_name():
    assert resolve_topic("mem", _simple_manifest()) == "memory"


def test_resolve_description():
    assert resolve_topic("login", _simple_manifest()) == "auth"


def test_resolve_tag():
    assert resolve_topic("redis", _simple_manifest()) == "memory"


def test_resolve_ambiguous_returns_none():
    manifest = FeatureManifest(
        version=1,
        features={
            "auth": Feature(name="auth", description="auth things", tags=["shared"]),
            "memory": Feature(name="memory", description="mem things", tags=["shared"]),
        },
    )
    assert resolve_topic("shared", manifest) is None


def test_resolve_no_match_returns_none():
    assert resolve_topic("zzz", _simple_manifest()) is None


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert slugify("Memory Storage") == "memory-storage"


def test_slugify_already_slug():
    assert slugify("auth") == "auth"


def test_slugify_special_chars():
    assert slugify("foo & bar!") == "foo-bar"


# ---------------------------------------------------------------------------
# doc_paths / _docs schema (attune-help 0.9 extensions)
# ---------------------------------------------------------------------------


def test_feature_post_init_coalesces_doc_path_to_doc_paths():
    """Legacy-style Feature with only ``doc_path`` populates ``doc_paths``."""
    feat = Feature(name="x", description="", doc_path="docs/how-to/x.md")
    assert feat.doc_paths == ["docs/how-to/x.md"]
    assert feat.doc_path == "docs/how-to/x.md"


def test_feature_post_init_coalesces_doc_paths_to_doc_path():
    """New-style Feature with only ``doc_paths`` populates ``doc_path``."""
    feat = Feature(
        name="x",
        description="",
        doc_paths=["docs/how-to/a.md", "docs/how-to/b.md"],
    )
    assert feat.doc_path == "docs/how-to/a.md"


def test_feature_multiple_doc_paths_preserved():
    """A feature may carry multiple doc paths."""
    feat = Feature(
        name="memory",
        description="",
        doc_paths=[
            "docs/how-to/memory-graph.md",
            "docs/how-to/short-term-memory-implementation.md",
            "docs/how-to/unified-memory-system.md",
        ],
    )
    assert len(feat.doc_paths) == 3
    assert feat.doc_path == "docs/how-to/memory-graph.md"


def test_load_manifest_accepts_legacy_doc_path_scalar(tmp_path):
    """Legacy YAML using ``doc_path:`` (scalar) loads into ``doc_paths``."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "version: 1\n"
        "features:\n"
        "  auth:\n"
        "    description: Authentication\n"
        "    doc_path: docs/how-to/auth.md\n",
        encoding="utf-8",
    )
    manifest = load_manifest(help_dir)
    feat = manifest.features["auth"]
    assert feat.doc_paths == ["docs/how-to/auth.md"]
    assert feat.doc_path == "docs/how-to/auth.md"


def test_load_manifest_doc_paths_wins_over_legacy_doc_path(tmp_path):
    """When both forms are present, ``doc_paths`` (new) takes precedence."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "version: 1\n"
        "features:\n"
        "  auth:\n"
        "    description: Authentication\n"
        "    doc_path: docs/how-to/legacy.md\n"
        "    doc_paths:\n"
        "      - docs/how-to/new-primary.md\n"
        "      - docs/how-to/new-secondary.md\n",
        encoding="utf-8",
    )
    manifest = load_manifest(help_dir)
    feat = manifest.features["auth"]
    assert feat.doc_paths == [
        "docs/how-to/new-primary.md",
        "docs/how-to/new-secondary.md",
    ]
    assert feat.doc_path == "docs/how-to/new-primary.md"


def test_load_manifest_parses_top_level_docs_bucket(tmp_path):
    """The ``_docs:`` bucket loads into ``FeatureManifest.docs``."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "version: 1\n"
        "_docs:\n"
        "  - docs/reference/FAQ.md\n"
        "  - docs/reference/glossary.md\n"
        "features:\n"
        "  auth:\n"
        "    description: Authentication\n",
        encoding="utf-8",
    )
    manifest = load_manifest(help_dir)
    assert manifest.docs == [
        "docs/reference/FAQ.md",
        "docs/reference/glossary.md",
    ]


def test_load_manifest_missing_docs_bucket_defaults_to_empty(tmp_path):
    """Omitting ``_docs:`` entirely yields an empty list."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "version: 1\nfeatures: {}\n",
        encoding="utf-8",
    )
    assert load_manifest(help_dir).docs == []


def test_load_manifest_rejects_non_list_docs_bucket(tmp_path):
    """``_docs:`` must be a list, not a mapping or scalar."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "version: 1\n_docs:\n  FAQ: docs/reference/FAQ.md\nfeatures: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="'_docs' must be a list"):
        load_manifest(help_dir)


def test_save_manifest_emits_doc_paths_not_doc_path(tmp_path):
    """Saving a Feature with doc_paths writes the list form, not the scalar."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    manifest = FeatureManifest(
        version=1,
        features={
            "memory": Feature(
                name="memory",
                description="Memory graph",
                doc_paths=["docs/how-to/memory-graph.md", "docs/how-to/unified.md"],
            )
        },
    )
    save_manifest(manifest, help_dir)
    raw = (help_dir / "features.yaml").read_text(encoding="utf-8")
    assert "doc_paths:" in raw
    assert "doc_path:" not in raw


def test_save_manifest_emits_top_level_docs_bucket(tmp_path):
    """FeatureManifest.docs round-trips through save/load."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    original = FeatureManifest(
        version=1,
        features={},
        docs=["docs/reference/FAQ.md", "docs/reference/glossary.md"],
    )
    save_manifest(original, help_dir)
    reloaded = load_manifest(help_dir)
    assert reloaded.docs == original.docs


def test_save_manifest_omits_empty_docs_bucket(tmp_path):
    """Empty ``docs`` list is not written to YAML (clean output)."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    manifest = FeatureManifest(
        version=1,
        features={"x": Feature(name="x", description="")},
        docs=[],
    )
    save_manifest(manifest, help_dir)
    raw = (help_dir / "features.yaml").read_text(encoding="utf-8")
    assert "_docs" not in raw


def test_load_manifest_malformed_yaml_raises_valueerror(tmp_path):
    """A syntactically-broken features.yaml raises the DOCUMENTED ValueError.

    Regression guard: ``yaml.YAMLError`` is not a ``ValueError`` subclass,
    so before the fix it escaped ``load_manifest``'s documented contract
    and defeated ``ops/help_data.py``'s ``except (OSError, ValueError)``
    degrade path (library-review batch-2 F2 twin).
    """
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "features:\n  - foo: [unclosed\n bad: : :\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid manifest YAML"):
        load_manifest(help_dir)


def test_load_manifest_malformed_yaml_caught_by_degrade_callers(tmp_path):
    """The (OSError, ValueError) degrade shape used by callers holds."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("a: [1, 2\nb: : :\n", encoding="utf-8")

    try:
        load_manifest(help_dir)
    except (OSError, ValueError):
        pass  # degrade path reached, as ops/help_data.py expects
    else:
        pytest.fail("malformed manifest did not raise")
