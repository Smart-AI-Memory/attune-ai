"""Corpus drift-guard: the REAL status parsers over the REAL spec corpus.

session-start-integrity R4 (roundtable ``q-context-mgmt-review-001``,
2026-08-18). The motivating bug: an orientation surface's status regex
expected ``**Status**:`` while 53/55 specs wrote ``**Status:**`` —
nearly every spec rendered "(unknown)" and nothing failed. The parser
had only ever been exercised against its author's imagined format,
never the corpus it serves. This guard makes the corpus the fixture:
every status-parsing surface in the repo must parse every tracked
spec's requirements.md, and the allowed-failure count is a shrink-only
ratchet seeded at the actual count (0 at introduction).

If this test fails, either fix the offending spec's status line to a
recognized convention or make the parser tolerant — never widen the
ratchet.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPECS_DIR = REPO_ROOT / "docs" / "specs"

#: Shrink-only ratchet — seeded 2026-08-18 at the true corpus count.
MAX_UNPARSEABLE = 0


def _load_script(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _corpus() -> list[Path]:
    files = sorted(SPECS_DIR.glob("*/requirements.md"))
    assert files, "spec corpus missing — did docs/specs/ move?"
    return files


def _offenders(matcher) -> list[str]:
    """Spec files whose requirements.md ``matcher`` cannot parse."""
    return [
        str(path.relative_to(REPO_ROOT))
        for path in _corpus()
        if not matcher(path.read_text(encoding="utf-8"))
    ]


class TestSpecStatusCorpus:
    """Each parser surface must parse the live corpus (ratchet 0)."""

    def test_canonical_specs_data_parses_corpus(self):
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from attune.ops import specs_data

        offenders = _offenders(
            lambda text: specs_data._STATUS_RE.search(text)
            or specs_data._STATUS_WRAPPED_RE.search(text)
        )
        assert len(offenders) <= MAX_UNPARSEABLE, (
            f"attune.ops.specs_data cannot parse {len(offenders)} spec status "
            f"line(s): {offenders} — fix the spec or the parser, never the ratchet"
        )

    def test_reconciler_status_re_parses_corpus(self):
        rec = _load_script(
            "_corpus_starter_reconciler",
            "src/attune/hooks/scripts/starter_reconciler.py",
        )
        offenders = _offenders(lambda text: rec.STATUS_RE.search(text))
        assert len(offenders) <= MAX_UNPARSEABLE, (
            f"starter_reconciler.STATUS_RE cannot parse {len(offenders)} spec "
            f"status line(s): {offenders}"
        )

    def test_plugin_state_status_line_parses_corpus(self):
        state = _load_script("_corpus_plugin_state", "plugin/hooks/_state.py")
        offenders = _offenders(lambda text: state._STATUS_LINE.search(text))
        assert len(offenders) <= MAX_UNPARSEABLE, (
            f"plugin/hooks/_state._STATUS_LINE cannot parse {len(offenders)} "
            f"spec status line(s): {offenders}"
        )

    def test_every_spec_has_a_status_line_at_all(self):
        """A spec with NO status line is invisible to every surface —
        the silent-degradation shape this spec exists to delete."""
        import re

        has_status = re.compile(r"(?im)^.{0,10}status.{0,4}:")
        offenders = [
            str(p.relative_to(REPO_ROOT))
            for p in _corpus()
            if not has_status.search(p.read_text(encoding="utf-8"))
        ]
        assert (
            len(offenders) <= MAX_UNPARSEABLE
        ), f"{len(offenders)} spec(s) carry no status line at all: {offenders}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
