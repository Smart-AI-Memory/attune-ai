"""Edge-case coverage for the absorbed authoring staleness trio.

The upstream ``_relocated`` suites (``test_manifest.py`` /
``test_staleness.py`` / ``test_symbols.py``) cover the mainline paths;
this module targets the signature-formatting, byte-hash-fallback,
frontmatter-parsing, manifest-validation, and convenience-wrapper
branches they leave uncovered — the T2a absorb (see
``docs/specs/attune-author-consolidation/``) added these modules whole,
so the edges matter for the drift signal ``help_data`` now depends on.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from attune.authoring.manifest import (
    Feature,
    FeatureManifest,
    load_manifest,
    save_manifest,
)
from attune.authoring.staleness import (
    _infer_kind,
    _read_frontmatter_value,
    _read_stored_hash_from_template,
    check_workspace_staleness,
    compute_semantic_hash,
    compute_source_hash,
)
from attune.authoring.symbols import SymbolExtractor

# ---------------------------------------------------------------------------
# symbols.py — signature formatting variants
# ---------------------------------------------------------------------------


def _extract(tmp_path: Path, src: str) -> dict:
    f = tmp_path / "m.py"
    f.write_text(src, encoding="utf-8")
    return {r.qualname: r for r in SymbolExtractor().extract(f)}


def test_signature_covers_posonly_varargs_kwonly_kwargs_async(tmp_path: Path) -> None:
    src = (
        "def posonly(a, /, b):\n    return a\n\n"
        "def variadic(*args, **kwargs):\n    return args\n\n"
        "def kwonly(*, j, k=1):\n    return j\n\n"
        "async def afunc(x: int) -> int:\n    return x\n"
    )
    recs = _extract(tmp_path, src)
    assert "/" in recs["posonly"].signature
    assert "*args" in recs["variadic"].signature
    assert "**kwargs" in recs["variadic"].signature
    # bare ``*`` marker (kwonly args with no ``*args``)
    assert "*, " in recs["kwonly"].signature or recs["kwonly"].signature.count("*") >= 1
    assert "k=1" in recs["kwonly"].signature
    assert recs["afunc"].signature.startswith("async def")
    assert "-> int" in recs["afunc"].signature


def test_class_public_attrs_and_methods_extracted(tmp_path: Path) -> None:
    src = (
        "class C:\n"
        "    x = 1\n"
        "    y: int = 2\n"
        "    _private = 3\n"
        "    def method(self):\n        return self.x\n"
        "    def _hidden(self):\n        return 0\n"
    )
    recs = _extract(tmp_path, src)
    assert "x" in recs["C"].public_attrs
    assert "y" in recs["C"].public_attrs
    assert "_private" not in recs["C"].public_attrs
    assert "C.method" in recs
    assert "C._hidden" not in recs


# ---------------------------------------------------------------------------
# staleness.py — hashing fallbacks + frontmatter/kind helpers
# ---------------------------------------------------------------------------


def test_mixed_content_feature_uses_byte_hash(tmp_path: Path) -> None:
    """A feature mixing .py and non-.py files uses byte-concatenation."""
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("plain text\n", encoding="utf-8")
    feat = Feature(name="mixed", description="", files=["a.py", "b.txt"])
    digest, matched = compute_source_hash(feat, tmp_path)
    assert matched == ["a.py", "b.txt"]
    assert len(digest) == 64


def test_semantic_hash_syntax_error_falls_back_to_bytes(tmp_path: Path) -> None:
    """A .py file that won't parse falls back to a byte hash, not a crash."""
    (tmp_path / "bad.py").write_text("def f(:\n", encoding="utf-8")
    feat = Feature(name="bad", description="", files=["bad.py"])
    digest, matched = compute_semantic_hash(feat, tmp_path)
    assert matched == ["bad.py"]
    assert len(digest) == 64


def test_read_frontmatter_value_edges() -> None:
    assert _read_frontmatter_value("no frontmatter here", "source_hash") is None
    assert _read_frontmatter_value("---\nunclosed block\n", "source_hash") is None
    assert _read_frontmatter_value("---\nsource_hash: abc123\n---\n", "source_hash") == "abc123"


def test_read_stored_hash_unsafe_name_and_missing(tmp_path: Path) -> None:
    assert _read_stored_hash_from_template("../evil", tmp_path) is None
    assert _read_stored_hash_from_template("does-not-exist", tmp_path) is None


def test_check_workspace_staleness_no_manifest_is_empty(tmp_path: Path) -> None:
    report = check_workspace_staleness(tmp_path)
    assert report.help_entries == []
    assert report.stale_count == 0


def test_check_workspace_staleness_with_manifest(tmp_path: Path) -> None:
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        yaml.safe_dump({"version": 1, "features": {"f": {"description": "d"}}}),
        encoding="utf-8",
    )
    report = check_workspace_staleness(tmp_path)
    assert isinstance(report.help_entries, list)
    assert len(report.help_entries) == 1


def test_infer_kind_variants() -> None:
    arch = Feature(name="f", description="", arch_path="docs/a.md")
    assert _infer_kind(arch, "arch_path") == "architecture"
    # first non-architecture kind wins
    ff = Feature(name="f", description="", doc_kinds=["architecture", "reference"])
    assert _infer_kind(ff, "doc_path") == "reference"
    # default when no doc_kinds
    plain = Feature(name="f", description="")
    assert _infer_kind(plain, "doc_path") == "how-to"


# ---------------------------------------------------------------------------
# manifest.py — load validation + save round-trip
# ---------------------------------------------------------------------------


def _write_manifest_yaml(help_dir: Path, data: object) -> None:
    help_dir.mkdir(parents=True, exist_ok=True)
    (help_dir / "features.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_manifest_non_mapping_raises(tmp_path: Path) -> None:
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected mapping"):
        load_manifest(help_dir)


def test_load_manifest_version_mismatch_still_loads(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_manifest_yaml(tmp_path / ".help", {"version": 999, "features": {}})
    manifest = load_manifest(tmp_path / ".help")  # warns, does not raise
    assert manifest.version == 999


def test_load_manifest_features_not_mapping_raises(tmp_path: Path) -> None:
    _write_manifest_yaml(tmp_path / ".help", {"features": ["a", "b"]})
    with pytest.raises(ValueError, match="'features' must be a mapping"):
        load_manifest(tmp_path / ".help")


def test_load_manifest_unsafe_feature_name_raises(tmp_path: Path) -> None:
    _write_manifest_yaml(tmp_path / ".help", {"features": {"../evil": {"description": "x"}}})
    with pytest.raises(ValueError, match="Invalid feature name"):
        load_manifest(tmp_path / ".help")


def test_load_manifest_feature_spec_not_mapping_raises(tmp_path: Path) -> None:
    _write_manifest_yaml(tmp_path / ".help", {"features": {"f": "not-a-dict"}})
    with pytest.raises(ValueError, match="must be a mapping"):
        load_manifest(tmp_path / ".help")


def test_save_manifest_round_trips_all_fields(tmp_path: Path) -> None:
    manifest = FeatureManifest(
        version=1,
        features={
            "f": Feature(
                name="f",
                description="d",
                files=["x.py"],
                tags=["t"],
                doc_kinds=["how-to"],
                doc_paths=["docs/f.md"],
                arch_path="docs/arch.md",
                doc_nav_section="Guides",
                cli_command="ops",
            )
        },
    )
    out = save_manifest(manifest, tmp_path / ".help")
    assert out.exists()
    reloaded = load_manifest(tmp_path / ".help")
    feat = reloaded.features["f"]
    assert feat.cli_command == "ops"
    assert feat.arch_path == "docs/arch.md"
    assert feat.doc_nav_section == "Guides"
