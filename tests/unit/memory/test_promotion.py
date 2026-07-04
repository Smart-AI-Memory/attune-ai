"""Tests for the stash → curated promotion path (curated-memory R4).

Non-mocked throughout: a real FileStashBackend on tmp_path feeds
candidates, promotions land as real curated ``.md`` files on tmp_path
(memory-unification D1 — files are the store), and the verdict form
round-trips through the real elicitation pipeline.
"""

from __future__ import annotations

import time

import pytest

from attune.elicitation import collect_form_response, form_from_dict, form_to_widget_html
from attune.memory.file_stash import FileStashBackend
from attune.memory.promotion import (
    CURATED_TYPES,
    TYPE_TO_META,
    promote,
    promotion_candidates,
    promotion_form_dict,
)
from attune.memory.session_stash import SessionStashEntry, stash_entry


def _frontmatter(path) -> dict[str, str]:
    """Flat first-wins parse of `k: v` frontmatter lines (matches hydrate)."""
    raw = path.read_text(encoding="utf-8")
    inner = raw[3 : raw.find("\n---", 3)]
    meta: dict[str, str] = {}
    for line in inner.splitlines():
        if ":" in line:
            k, v = line.strip().split(":", 1)
            meta.setdefault(k.strip(), v.strip())
    return meta


PROPOSAL = {
    "source_id": "stash-123",
    "type": "project_context",
    "name": "Recall digest ships as report-style progress",
    "description": "The digest render pulls from FCALL recall_digest.",
    "tags": ["memory", "r3"],
}

SOURCE = {
    "id": "stash-123",
    "text": "Redis's first real consumer: recall_digest.py pulls from FCALL",
    "stash_type": "pattern",
    "session_id": "sess-abc",
    "ts": 1783055837.0,
}


class TestPromotionCandidates:
    def test_reads_real_file_backend(self, tmp_path) -> None:
        backend = FileStashBackend(base_dir=tmp_path)
        entry = SessionStashEntry.create(
            session_id="sess-1",
            cwd=str(tmp_path),
            type="decision",
            content="A durable finding worth promoting",
        )
        assert stash_entry(entry, backend=backend)
        cands = promotion_candidates(backend=backend)
        assert len(cands) == 1
        c = cands[0]
        assert c["text"] == "A durable finding worth promoting"
        assert c["stash_type"] == "decision"
        assert c["session_id"] == "sess-1"
        assert c["id"]

    def test_empty_backend_yields_no_candidates(self, tmp_path) -> None:
        cands = promotion_candidates(backend=FileStashBackend(base_dir=tmp_path))
        assert cands == []

    def test_candidates_carry_ts_newest_first(self, tmp_path) -> None:
        """Regression for the 2026-07-04 R4 failure: every candidate came
        back with ``ts: None`` (the backends dropped the timestamp from the
        ``recent()`` record shape), so the docstring's "newest first" could
        not be working. Non-mocked round-trip: real backend writes, then
        promotion_candidates must return populated ``ts`` in strictly
        newest-first order."""
        backend = FileStashBackend(base_dir=tmp_path)
        for i, text in enumerate(
            ["an older stashed finding", "a middle stashed finding", "the newest finding"]
        ):
            entry = SessionStashEntry.create(
                session_id=f"sess-{i}",
                cwd=str(tmp_path),
                type="note",
                content=text,
            )
            assert stash_entry(entry, backend=backend)
            time.sleep(0.01)  # distinct write timestamps

        cands = promotion_candidates(top_k=10, backend=backend)
        assert [c["text"] for c in cands] == [
            "the newest finding",
            "a middle stashed finding",
            "an older stashed finding",
        ]
        ts_values = [c["ts"] for c in cands]
        assert all(isinstance(t, float) for t in ts_values), f"ts missing: {ts_values}"
        assert ts_values == sorted(ts_values, reverse=True)


class TestPromotionFormDict:
    def test_builds_per_candidate_decisions(self) -> None:
        form = form_from_dict(promotion_form_dict([PROPOSAL, {**PROPOSAL, "source_id": "s2"}]))
        assert len(form.questions) == 2
        q = form.questions[0]
        assert q.type.value == "decision"
        assert q.options == ["Promote", "Skip"]
        assert q.recommended == "Promote"
        assert "stash-123" in q.rationale  # provenance visible pre-verdict

    def test_no_bulk_path_answers_are_per_candidate(self) -> None:
        form = form_from_dict(promotion_form_dict([PROPOSAL, {**PROPOSAL, "source_id": "s2"}]))
        resp = collect_form_response(form, {"promote_0": "Promote", "promote_1": "Skip"})
        assert resp.responses == {"promote_0": "Promote", "promote_1": "Skip"}

    def test_renders_as_widget(self) -> None:
        html = form_to_widget_html(form_from_dict(promotion_form_dict([PROPOSAL])))
        assert "Stash → curated promotion" in html
        assert "Recommended" in html


class TestPromote:
    def test_writes_curated_file_with_provenance(self, tmp_path) -> None:
        node_id = promote(PROPOSAL, SOURCE, response_id="resp-1", curated_dir=tmp_path)
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        f = files[0]
        meta = _frontmatter(f)
        # Hydration contract (load_curated in the memory repo reads these).
        assert meta["node_id"] == node_id
        assert meta["node_type"] == "project_context"
        assert meta["type"] == TYPE_TO_META["project_context"]
        assert meta["curated"] == "true"
        assert meta["description"] == PROPOSAL["name"]
        assert meta["name"] == f.stem  # lint R1: name ≡ filename stem
        assert meta["updated_at"]
        # Provenance.
        assert meta["promoted_from_stash_id"] == "stash-123"
        assert meta["promoted_from_session"] == "sess-abc"
        assert meta["review_verdict"] == "promote"
        assert meta["review_response_id"] == "resp-1"
        assert meta["promoted_at"]  # date stamped
        # Regression (caught live 2026-07-03): non-active promotions are
        # invisible to hydration/recall — must land "active".
        assert meta["status"] == "active"
        # Body carries the drafted description.
        body = f.read_text().split("---", 2)[2]
        assert PROPOSAL["description"] in body

    def test_persists_and_reparses(self, tmp_path) -> None:
        node_id = promote(PROPOSAL, SOURCE, curated_dir=tmp_path)
        f = next(iter(tmp_path.glob("*.md")))
        meta = _frontmatter(f)  # fresh parse from disk — no warm state
        assert meta["node_id"] == node_id
        assert meta["promoted_from_stash_id"] == "stash-123"

    def test_stem_collision_gets_suffix(self, tmp_path) -> None:
        first = promote(PROPOSAL, SOURCE, curated_dir=tmp_path)
        second = promote(PROPOSAL, SOURCE, curated_dir=tmp_path)
        assert first != second
        stems = sorted(p.stem for p in tmp_path.glob("*.md"))
        assert len(stems) == 2
        assert stems[1] == stems[0] + "_x"
        # R1 holds for both: name ≡ stem.
        for p in tmp_path.glob("*.md"):
            assert _frontmatter(p)["name"] == p.stem

    def test_rejects_non_curated_type(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="curated node type"):
            promote({**PROPOSAL, "type": "bug"}, SOURCE, curated_dir=tmp_path)
        assert list(tmp_path.glob("*.md")) == []

    def test_curated_types_are_the_four(self) -> None:
        assert set(CURATED_TYPES) == {
            "user_context",
            "feedback",
            "project_context",
            "reference",
        }
