"""Tests for the per-page maintenance contract (regen safety).

The core guarantee under test: regeneration NEVER drops hand-written
content. ``manual`` pages are skipped; ``hybrid`` pages keep their
fenced regions; any ambiguous fence structure fails safe to the
on-disk file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.authoring.maintenance_contract import (
    AUTO,
    HYBRID,
    MANUAL,
    MANUAL_FENCE_END,
    MANUAL_FENCE_START,
    HybridMergeError,
    PageMaintenance,
    extract_manual_regions,
    format_maintenance_report,
    merge_hybrid,
    read_maintenance_mode,
    resolve_write_content,
    scan_maintenance,
)


def _fenced(body: str) -> str:
    return f"{MANUAL_FENCE_START}{body}{MANUAL_FENCE_END}"


def _doc(maintenance: str | None = None, status: str | None = None, body: str = "x") -> str:
    lines = ["---", "type: help-concept"]
    if maintenance is not None:
        lines.append(f"maintenance: {maintenance}")
    if status is not None:
        lines.append(f"status: {status}")
    lines += ["---", body, ""]
    return "\n".join(lines)


class TestReadMaintenanceMode:
    def test_absent_defaults_auto(self) -> None:
        assert read_maintenance_mode(_doc()) == AUTO

    def test_no_frontmatter_defaults_auto(self) -> None:
        assert read_maintenance_mode("# just a heading\n") == AUTO

    @pytest.mark.parametrize("mode", [AUTO, MANUAL, HYBRID])
    def test_explicit_modes(self, mode: str) -> None:
        assert read_maintenance_mode(_doc(maintenance=mode)) == mode

    def test_status_manual_is_alias(self) -> None:
        assert read_maintenance_mode(_doc(status="manual")) == MANUAL

    def test_unknown_value_fails_open_to_auto(self) -> None:
        assert read_maintenance_mode(_doc(maintenance="frozen")) == AUTO

    def test_case_insensitive(self) -> None:
        assert read_maintenance_mode(_doc(maintenance="Hybrid")) == HYBRID

    def test_maintenance_field_wins_over_status(self) -> None:
        # An explicit maintenance:auto un-freezes a legacy status:manual.
        assert read_maintenance_mode(_doc(maintenance="auto", status="manual")) == AUTO


class TestFenceExtraction:
    def test_extracts_regions_in_order(self) -> None:
        text = "intro" + _fenced("ALPHA") + "mid" + _fenced("BETA") + "end"
        assert extract_manual_regions(text) == ["ALPHA", "BETA"]

    def test_no_fences(self) -> None:
        assert extract_manual_regions("nothing here") == []


class TestMergeHybrid:
    def test_preserves_existing_regions_takes_new_auto_text(self) -> None:
        existing = "OLD-AUTO" + _fenced("HANDWRITTEN") + "OLD-TAIL"
        regenerated = "NEW-AUTO" + _fenced("placeholder") + "NEW-TAIL"
        merged = merge_hybrid(regenerated=regenerated, existing=existing)
        assert "NEW-AUTO" in merged and "NEW-TAIL" in merged
        assert "HANDWRITTEN" in merged
        assert "placeholder" not in merged
        assert "OLD-AUTO" not in merged

    def test_multiple_regions_matched_by_order(self) -> None:
        existing = _fenced("A") + "x" + _fenced("B")
        regenerated = _fenced("1") + "y" + _fenced("2")
        merged = merge_hybrid(regenerated=regenerated, existing=existing)
        assert extract_manual_regions(merged) == ["A", "B"]
        assert "y" in merged  # new auto text between regions

    def test_count_mismatch_raises(self) -> None:
        with pytest.raises(HybridMergeError):
            merge_hybrid(regenerated="no fences", existing=_fenced("KEEP"))

    def test_unbalanced_existing_raises(self) -> None:
        with pytest.raises(HybridMergeError):
            merge_hybrid(
                regenerated=_fenced("x"),
                existing=MANUAL_FENCE_START + "dangling",
            )

    def test_nested_fences_raise(self) -> None:
        nested = MANUAL_FENCE_START + _fenced("inner") + MANUAL_FENCE_END
        with pytest.raises(HybridMergeError):
            merge_hybrid(regenerated=_fenced("x"), existing=nested)


class TestResolveWriteContent:
    def test_no_existing_file_returns_regenerated(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        assert resolve_write_content(out, "NEW") == "NEW"

    def test_auto_returns_regenerated(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        out.write_text(_doc(maintenance="auto", body="OLD"), encoding="utf-8")
        regenerated = _doc(maintenance="auto", body="NEW")
        assert "NEW" in resolve_write_content(out, regenerated)

    def test_hybrid_merges_and_carries_field(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        out.write_text(
            _doc(maintenance="hybrid", body="OLD-AUTO" + _fenced("KEEPME")),
            encoding="utf-8",
        )
        # Regenerated comes from the template: fences present, field absent.
        regenerated = _doc(body="NEW-AUTO" + _fenced("placeholder"))
        result = resolve_write_content(out, regenerated)
        assert "KEEPME" in result  # hand-written region preserved
        assert "NEW-AUTO" in result  # auto text refreshed
        assert "placeholder" not in result
        assert read_maintenance_mode(result) == HYBRID  # field carried over

    def test_hybrid_failsafe_keeps_existing_when_fences_mismatch(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        existing = _doc(maintenance="hybrid", body="OLD" + _fenced("PRECIOUS"))
        out.write_text(existing, encoding="utf-8")
        # Template emitted NO fences -> can't place the region -> fail safe.
        regenerated = _doc(body="NEW with no fences")
        result = resolve_write_content(out, regenerated)
        assert result == existing  # untouched; PRECIOUS never dropped
        assert "PRECIOUS" in result

    def test_unbalanced_regenerated_failsafe(self, tmp_path: Path) -> None:
        # Existing is well-formed hybrid; the regenerated content has a
        # dangling fence -> merge_hybrid raises -> fail safe keeps existing.
        out = tmp_path / "concept.md"
        existing = _doc(maintenance="hybrid", body=_fenced("KEEP"))
        out.write_text(existing, encoding="utf-8")
        regenerated = _doc(body=MANUAL_FENCE_START + "dangling")
        assert resolve_write_content(out, regenerated) == existing

    def test_carry_noop_when_source_has_no_maintenance_field(self, tmp_path: Path) -> None:
        # Existing auto page with NO maintenance field -> nothing to carry.
        out = tmp_path / "concept.md"
        out.write_text(_doc(body="OLD"), encoding="utf-8")  # no field at all
        regenerated = _doc(body="NEW")
        result = resolve_write_content(out, regenerated)
        assert result == regenerated
        assert "maintenance:" not in result

    def test_carry_noop_when_regenerated_has_no_frontmatter(self, tmp_path: Path) -> None:
        # Hybrid existing declares the field; regenerated body has fences
        # but no frontmatter -> merge succeeds, field can't be injected.
        out = tmp_path / "concept.md"
        out.write_text(_doc(maintenance="hybrid", body=_fenced("KEEPME")), encoding="utf-8")
        regenerated = "no-frontmatter " + _fenced("placeholder")
        result = resolve_write_content(out, regenerated)
        assert "KEEPME" in result  # region still preserved
        assert not result.startswith("---")  # no frontmatter was fabricated


class TestGeneratorIntegration:
    """The contract holds through the real generator, not just in unit tests."""

    def test_hybrid_region_survives_regeneration(self, help_dir: Path, project_root: Path) -> None:
        from attune.authoring.generator import generate_feature_templates
        from attune.authoring.manifest import Feature

        feature = Feature(
            name="auth",
            description="Authentication and authorization",
            files=["src/auth/**"],
            tags=["security"],
        )
        generate_feature_templates(
            feature=feature,
            help_dir=help_dir,
            project_root=project_root,
            use_rag=False,
        )
        concept = help_dir / "templates" / "auth" / "concept.md"
        original = concept.read_text(encoding="utf-8")

        # Author marks the page hybrid and adds a hand-written region.
        sentinel = "HAND-WRITTEN — must survive regeneration"
        edited = original.replace("---\n", "---\nmaintenance: hybrid\n", 1)
        edited += f"\n{MANUAL_FENCE_START}\n{sentinel}\n{MANUAL_FENCE_END}\n"
        concept.write_text(edited, encoding="utf-8")

        # Regenerate even with overwrite: the stock template emits no
        # fences, so the contract fails safe and preserves the region.
        generate_feature_templates(
            feature=feature,
            help_dir=help_dir,
            project_root=project_root,
            overwrite=True,
            use_rag=False,
        )
        assert sentinel in concept.read_text(encoding="utf-8")


class TestScanMaintenance:
    def test_classifies_pages_by_mode(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(_doc(maintenance="manual"), encoding="utf-8")
        (tmp_path / "b.md").write_text(_doc(maintenance="hybrid"), encoding="utf-8")
        (tmp_path / "c.md").write_text(_doc(), encoding="utf-8")  # auto
        (tmp_path / "d.md").write_text(_doc(status="manual"), encoding="utf-8")  # alias
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "e.md").write_text(_doc(maintenance="hybrid"), encoding="utf-8")

        pages = scan_maintenance([tmp_path])
        by_name = {p.path.name: p.mode for p in pages}
        assert by_name == {
            "a.md": MANUAL,
            "b.md": HYBRID,
            "c.md": AUTO,
            "d.md": MANUAL,
            "e.md": HYBRID,
        }

    def test_missing_root_skipped(self, tmp_path: Path) -> None:
        assert scan_maintenance([tmp_path / "does-not-exist"]) == []

    def test_unreadable_page_skipped(self, tmp_path: Path) -> None:
        # A directory named "*.md" matches rglob but can't be read_text'd
        # (IsADirectoryError is an OSError) -> it's skipped, not crashed.
        (tmp_path / "real.md").write_text(_doc(), encoding="utf-8")
        (tmp_path / "bogus.md").mkdir()
        names = [p.path.name for p in scan_maintenance([tmp_path])]
        assert names == ["real.md"]

    def test_sorted_and_deduplicated(self, tmp_path: Path) -> None:
        (tmp_path / "z.md").write_text(_doc(), encoding="utf-8")
        (tmp_path / "a.md").write_text(_doc(), encoding="utf-8")
        # Same root passed twice -> each page reported once.
        pages = scan_maintenance([tmp_path, tmp_path])
        names = [p.path.name for p in pages]
        assert names == ["a.md", "z.md"]


class TestFormatMaintenanceReport:
    def _pages(self, tmp_path: Path) -> list[PageMaintenance]:
        return [
            PageMaintenance(tmp_path / "auth" / "concept.md", AUTO),
            PageMaintenance(tmp_path / "auth" / "task.md", MANUAL),
            PageMaintenance(tmp_path / "cli" / "concept.md", HYBRID),
        ]

    def test_default_omits_auto_lists_curated(self, tmp_path: Path) -> None:
        out = format_maintenance_report(self._pages(tmp_path), base=tmp_path)
        assert "1 auto, 1 manual, 1 hybrid" in out
        assert "### manual (1)" in out
        assert "### hybrid (1)" in out
        assert "auth/task.md" in out  # base stripped
        assert "1 auto page(s) omitted" in out
        assert "### auto" not in out

    def test_show_auto_lists_everything(self, tmp_path: Path) -> None:
        out = format_maintenance_report(self._pages(tmp_path), base=tmp_path, show_auto=True)
        assert "### auto (1)" in out
        assert "omitted" not in out

    def test_no_base_shows_full_path(self, tmp_path: Path) -> None:
        pages = [PageMaintenance(tmp_path / "x.md", MANUAL)]
        out = format_maintenance_report(pages)
        assert (tmp_path / "x.md").as_posix() in out

    def test_path_outside_base_falls_back_to_full(self, tmp_path: Path) -> None:
        outside = PageMaintenance(Path("/elsewhere/y.md"), HYBRID)
        out = format_maintenance_report([outside], base=tmp_path)
        assert "/elsewhere/y.md" in out

    def test_empty_corpus(self, tmp_path: Path) -> None:
        out = format_maintenance_report([], base=tmp_path)
        assert "0 page(s)" in out
