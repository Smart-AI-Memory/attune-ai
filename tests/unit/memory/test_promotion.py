"""Tests for the stash → curated promotion path (curated-memory R4).

Non-mocked throughout: a real FileStashBackend on tmp_path feeds
candidates, a real MemoryGraph on tmp_path receives promotions, and
the verdict form round-trips through the real elicitation pipeline.
"""

from __future__ import annotations

import pytest

from attune.elicitation import collect_form_response, form_from_dict, form_to_widget_html
from attune.memory.file_stash import FileStashBackend
from attune.memory.graph import MemoryGraph
from attune.memory.promotion import (
    CURATED_TYPES,
    promote,
    promotion_candidates,
    promotion_form_dict,
)
from attune.memory.session_stash import SessionStashEntry, stash_entry

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
    def test_writes_node_with_provenance(self, tmp_path) -> None:
        graph = MemoryGraph(path=tmp_path / "curated.json")
        node_id = promote(PROPOSAL, SOURCE, response_id="resp-1", graph=graph)
        node = graph.nodes[node_id]
        assert node.type.value == "project_context"
        assert node.name == PROPOSAL["name"]
        meta = node.metadata
        assert meta["promoted_from_stash_id"] == "stash-123"
        assert meta["promoted_from_session"] == "sess-abc"
        assert meta["review_verdict"] == "promote"
        assert meta["review_response_id"] == "resp-1"
        assert meta["promoted_at"]  # date stamped
        # Regression (caught live 2026-07-03): add_finding defaults status
        # to "open", which hydration/recall filter out — promotions must
        # land "active" or they are invisible to the digest.
        assert node.status == "active"

    def test_persists_across_reload(self, tmp_path) -> None:
        path = tmp_path / "curated.json"
        node_id = promote(PROPOSAL, SOURCE, graph=MemoryGraph(path=path))
        reloaded = MemoryGraph(path=path)
        assert node_id in reloaded.nodes
        assert reloaded.nodes[node_id].metadata["promoted_from_stash_id"] == "stash-123"

    def test_rejects_non_curated_type(self, tmp_path) -> None:
        graph = MemoryGraph(path=tmp_path / "curated.json")
        with pytest.raises(ValueError, match="curated node type"):
            promote({**PROPOSAL, "type": "bug"}, SOURCE, graph=graph)

    def test_curated_types_are_the_four(self) -> None:
        assert set(CURATED_TYPES) == {
            "user_context",
            "feedback",
            "project_context",
            "reference",
        }
