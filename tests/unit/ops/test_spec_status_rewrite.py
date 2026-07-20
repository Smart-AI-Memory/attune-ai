"""Regression tests for the spec status-flip writer.

Postmortem: on 2026-07-19 the ops dashboard's
``PUT /api/specs/{slug}/{phase}/status`` endpoint corrupted
``docs/specs/usage-signals/requirements.md`` and ``decisions.md``
(pending-writes journal entries at 20:44 UTC, dashboard pid 1134):

1. requirements.md used the ``**Status: value**`` convention (colon
   fully inside the bold), which ``_STATUS_RE`` did not match — the
   rewriter fell to the insert path and stamped a DUPLICATE
   ``**Status:** approved`` line above the real header.
2. decisions.md's descriptive value ``R6 spend alarm shipped
   (2026-06-20) · …`` had its leading words replaced wholesale with
   ``approved``, destroying the R6 record.
3. ``_STATUS_RE`` used ``\\s*`` under ``re.MULTILINE``, so the
   ``re.sub`` swallowed the blank lines around the status line
   (the deleted blank line after the H1).

The contract now: a status stamp is additive and idempotent, or it
does not happen at all (``UnsafeStatusRewrite`` → HTTP 409).
"""

from __future__ import annotations

import pytest

from attune.ops.routes.specs import UnsafeStatusRewrite, _rewrite_status_line
from attune.ops.specs_data import _extract_status

# The two files as observed in the incident (abridged bodies).
USAGE_SIGNALS_REQUIREMENTS = """\
# Usage signals — requirements

**Status: requirements chair-ruled per item** — authored by the round table

## R1

Body text.
"""

USAGE_SIGNALS_DECISIONS = """\
# Usage signals — decisions

**Status:** R6 spend alarm shipped (2026-06-20) · Phase 2b live (D8) ·

## D1

Body text.
"""


class TestIncidentShapes:
    """The exact 2026-07-19 corruption shapes must now refuse to write."""

    def test_wrapped_bold_status_is_never_duplicated(self):
        # Shape 1: ``**Status: …**`` previously fell through to the
        # insert path and stamped a second status line above the real one.
        with pytest.raises(UnsafeStatusRewrite):
            _rewrite_status_line(USAGE_SIGNALS_REQUIREMENTS, "approved")

    def test_descriptive_status_value_is_never_rewritten(self):
        # Shape 2: ``R6 spend alarm shipped (…)`` previously became
        # ``approved (…)`` — the R6 record destroyed.
        with pytest.raises(UnsafeStatusRewrite):
            _rewrite_status_line(USAGE_SIGNALS_DECISIONS, "approved")

    def test_wrapped_bold_status_still_parses_for_listing(self):
        # The listing side should read the real status, not None.
        assert _extract_status(USAGE_SIGNALS_REQUIREMENTS) == "requirements chair-ruled per item"


class TestLegitimateFlip:
    """Recognized status tokens still flip, annotation preserved."""

    DOC = "# Title\n\n**Status:** approved (2026-05-09) — Phase A\n\nBody.\n"

    def test_flip_preserves_annotation(self):
        out = _rewrite_status_line(self.DOC, "in-review")
        assert "**Status:** in-review (2026-05-09) — Phase A" in out

    def test_flip_preserves_surrounding_blank_lines(self):
        # Bug 3: the MULTILINE ``\s*`` sub ate the blank lines around
        # the status line (observed as the deleted blank line after H1).
        out = _rewrite_status_line(self.DOC, "in-review")
        assert out == "# Title\n\n**Status:** in-review (2026-05-09) — Phase A\n\nBody.\n"

    def test_flip_is_byte_idempotent(self):
        once = _rewrite_status_line(self.DOC, "in-review")
        twice = _rewrite_status_line(once, "in-review")
        assert twice == once

    def test_colon_outside_bold_convention_flips(self):
        doc = "# T\n\n**Status**: draft\n\nBody.\n"
        out = _rewrite_status_line(doc, "approved")
        assert out == "# T\n\n**Status:** approved\n\nBody.\n"


class TestInsertPath:
    """Stamping a file with no status line at all stays additive."""

    def test_insert_after_heading_is_idempotent(self):
        doc = "# Title\n\nBody only.\n"
        once = _rewrite_status_line(doc, "approved")
        assert "**Status:** approved" in once
        assert "Body only." in once
        assert _rewrite_status_line(once, "approved") == once

    def test_insert_without_heading_is_idempotent(self):
        doc = "Plain text file.\n"
        once = _rewrite_status_line(doc, "draft")
        assert once.startswith("**Status:** draft\n")
        assert "Plain text file." in once
        assert _rewrite_status_line(once, "draft") == once

    def test_never_inserts_above_unrecognized_status_variant(self):
        # Any status-looking line — even one the strict pattern can't
        # parse — must block the insert path (no duplicate stamps).
        doc = "# T\n\nstatus: chair-ruled, see decisions\n\nBody.\n"
        with pytest.raises(UnsafeStatusRewrite):
            _rewrite_status_line(doc, "approved")

    def test_unparseable_line_before_strict_match_blocks(self):
        # The document's REAL header is the earlier wrapped line; the
        # later strict-shaped line is body prose. Refuse.
        doc = (
            "# T\n\n"
            "**Status: chair-ruled per item**\n\n"
            "Quoting the old header: **Status:** draft\n"
        )
        with pytest.raises(UnsafeStatusRewrite):
            _rewrite_status_line(doc, "approved")


class TestEndpointRoundTrip:
    """Live-fire through the PUT route: refusals 409, repeats byte-stable."""

    @pytest.fixture()
    def env(self, tmp_path, monkeypatch):
        pytest.importorskip("fastapi")
        pytest.importorskip("jinja2")
        from fastapi.testclient import TestClient

        from attune.ops.config import build_config
        from attune.ops.server import create_app

        monkeypatch.chdir(tmp_path)
        root = tmp_path / "specs"
        spec_dir = root / "usage-signals"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text(USAGE_SIGNALS_REQUIREMENTS, encoding="utf-8")
        (spec_dir / "decisions.md").write_text(USAGE_SIGNALS_DECISIONS, encoding="utf-8")
        (spec_dir / "tasks.md").write_text(
            "# Tasks\n\n**Status:** draft\n\nBody.\n", encoding="utf-8"
        )
        config = build_config(
            project_root=tmp_path,
            specs_roots=(root,),
            allow_run=True,
            trusted_hosts=("testserver", "test"),
        )
        return TestClient(create_app(config)), spec_dir

    def test_descriptive_files_get_409_and_stay_byte_identical(self, env):
        client, spec_dir = env
        for phase, original in (
            ("requirements", USAGE_SIGNALS_REQUIREMENTS),
            ("decisions", USAGE_SIGNALS_DECISIONS),
        ):
            r = client.put(f"/api/specs/usage-signals/{phase}/status", json={"status": "approved"})
            assert r.status_code == 409, r.text
            on_disk = (spec_dir / f"{phase}.md").read_text(encoding="utf-8")
            assert on_disk == original

    def test_double_put_is_byte_identical(self, env):
        client, spec_dir = env
        r1 = client.put("/api/specs/usage-signals/tasks/status", json={"status": "approved"})
        assert r1.status_code == 200, r1.text
        first = (spec_dir / "tasks.md").read_bytes()
        r2 = client.put("/api/specs/usage-signals/tasks/status", json={"status": "approved"})
        assert r2.status_code == 200, r2.text
        assert (spec_dir / "tasks.md").read_bytes() == first
        assert first.decode() == "# Tasks\n\n**Status:** approved\n\nBody.\n"
