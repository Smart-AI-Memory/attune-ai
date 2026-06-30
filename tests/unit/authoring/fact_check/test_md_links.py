"""Tests for the md-links check."""

from __future__ import annotations

from pathlib import Path

from attune.authoring.fact_check import md_links
from attune.authoring.fact_check.report import CHECK_MD_LINKS


def _write(tmp_path: Path, body: str, name: str = "polished.md") -> Path:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return f


def test_catches_missing_relative_target(tmp_path: Path) -> None:
    """Missing-target regression — the ``See also`` class of bug."""
    body = "See [Concept](concepts/template-patterns.md) for context.\n"
    findings = md_links.check(_write(tmp_path, body))
    assert any(
        f.check == CHECK_MD_LINKS and f.severity == "error" and "template-patterns.md" in f.message
        for f in findings
    )


def test_accepts_existing_relative_target(tmp_path: Path) -> None:
    """A link whose target exists on disk produces no finding."""
    (tmp_path / "sibling.md").write_text("# sibling\n", encoding="utf-8")
    body = "See [sibling](sibling.md).\n"
    assert md_links.check(_write(tmp_path, body)) == []


def test_skips_external_urls(tmp_path: Path) -> None:
    """``http://`` and ``mailto:`` are out of scope for Phase 1."""
    body = "Check [Anthropic](https://anthropic.com) " "or email [me](mailto:dev@example.com).\n"
    assert md_links.check(_write(tmp_path, body)) == []


def test_skips_pure_anchor_links(tmp_path: Path) -> None:
    """``[See above](#section)`` doesn't reference another file."""
    body = "[Jump](#somewhere)\n"
    assert md_links.check(_write(tmp_path, body)) == []


def test_anchor_in_relative_target_strips_for_existence_check(
    tmp_path: Path,
) -> None:
    """``path.md#anchor`` checks only that ``path.md`` exists."""
    (tmp_path / "real.md").write_text("# real\n", encoding="utf-8")
    body = "[See real](real.md#section-2)\n"
    assert md_links.check(_write(tmp_path, body)) == []


def test_deduplicates_repeated_missing_target(tmp_path: Path) -> None:
    body = "[a](missing.md)\n" "[b](missing.md)\n"
    findings = md_links.check(_write(tmp_path, body))
    assert len([f for f in findings if "missing.md" in f.message]) == 1
