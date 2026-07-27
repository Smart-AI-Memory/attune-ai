"""Tests for the spec workflow contract/scratch/gates (todo items 3-5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from attune.authoring.spec_runner import WHOLE_SPEC, DocRequest
from attune.authoring.spec_workflow import (
    BLOCKED,
    HOST,
    ISOLATED,
    DraftContract,
    ScopeQuestion,
    SessionGrants,
    plan_gate_boundary,
    preselect_packets,
    resolve_scope,
    review_surface_extras,
    scratch_packets,
)

DOCS = [DocRequest(f"docs/specs/x/d{i}.md", f"doc {i}") for i in range(7)]
QUESTIONS = [
    ScopeQuestion("depth", "How deep?", "standard"),
    ScopeQuestion("audience", "Who reads it?", "developers"),
]


# ---------------------------------------------------------------- item 3


def test_resolve_scope_defaults_when_no_elicitation():
    answers, source = resolve_scope(QUESTIONS, elicit=None)
    assert answers == {"depth": "standard", "audience": "developers"}
    assert source == "defaults"


def test_resolve_scope_elicitation_failure_takes_one_fallback_path():
    calls = []

    def broken(questions):
        calls.append(1)
        raise RuntimeError("rich elicitation unavailable")

    answers, source = resolve_scope(QUESTIONS, elicit=broken)
    assert answers == {"depth": "standard", "audience": "developers"}
    assert source == "defaults"
    assert calls == [1]  # exactly one attempt, no retry loop


def test_resolve_scope_full_and_partial_elicitation():
    full, source = resolve_scope(QUESTIONS, elicit=lambda q: {"depth": "deep", "audience": "ops"})
    assert (full, source) == ({"depth": "deep", "audience": "ops"}, "elicited")
    partial, source = resolve_scope(QUESTIONS, elicit=lambda q: {"depth": "deep"})
    assert partial == {"depth": "deep", "audience": "developers"}
    assert source == "mixed"


def test_preselect_packets_matches_ratified_matrix():
    assert preselect_packets(DOCS[:5]) == [DOCS[:5]]  # <=5 rides whole
    assert preselect_packets(DOCS) == [DOCS[:5], DOCS[5:]]  # >5 splits


def test_contract_blocks_unauthorized_invocation():
    contract = DraftContract.assemble(
        packet_class="spec-draft:fable",
        grants=SessionGrants(),
        docs=DOCS[:2],
        questions=QUESTIONS,
    )
    assert not contract.authorized
    with pytest.raises(PermissionError, match="workflow todo item 3"):
        contract.require_authorized()


def test_contract_grant_is_session_durable_per_packet_class():
    grants = SessionGrants()
    grants.grant("spec-draft:fable", note="Patrick approved 4-file packet class")
    first = DraftContract.assemble(
        packet_class="spec-draft:fable", grants=grants, docs=DOCS[:4], questions=QUESTIONS
    )
    second = DraftContract.assemble(packet_class="spec-draft:fable", grants=grants, docs=DOCS[:2])
    for contract in (first, second):
        assert contract.authorized
        contract.require_authorized()  # no re-ask within the session
    assert first.strategy == WHOLE_SPEC
    assert not grants.is_authorized("other-class")


# ---------------------------------------------------------------- item 4


def test_scratch_packets_cleans_on_success_and_lives_outside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with scratch_packets() as scratch:
        (scratch / "prompt.txt").write_text("packet", encoding="utf-8")
        assert scratch.exists()
        assert not scratch.is_relative_to(tmp_path)  # never the working tree
    assert not scratch.exists()


@pytest.mark.parametrize("exc", [RuntimeError("boom"), KeyboardInterrupt()])
def test_scratch_packets_cleans_on_failure_and_interruption(exc):
    kept: list[Path] = []
    with pytest.raises(type(exc)):
        with scratch_packets() as scratch:
            kept.append(scratch)
            (scratch / "reply.txt").write_text("packet", encoding="utf-8")
            raise exc
    assert not kept[0].exists()


def _git_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_review_surface_extras_flags_only_unintended(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "docs").mkdir()
    (repo / "docs" / "intended.md").write_text("spec", encoding="utf-8")
    (repo / "stray-scratch.txt").write_text("leak", encoding="utf-8")
    extras = review_surface_extras(repo, intended=["docs/intended.md"])
    assert extras == ["stray-scratch.txt"]
    assert review_surface_extras(repo, intended=["docs/intended.md", "stray-scratch.txt"]) == []


def test_review_surface_extras_accepts_intended_directories(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "docs" / "specs" / "x").mkdir(parents=True)
    (repo / "docs" / "specs" / "x" / "a.md").write_text("a", encoding="utf-8")
    assert review_surface_extras(repo, intended=["docs/specs/x"]) == []


def test_review_surface_extras_rejects_non_repo(tmp_path):
    with pytest.raises(ValueError, match="not a git repository"):
        review_surface_extras(tmp_path, intended=[])


# ---------------------------------------------------------------- item 5


def test_gate_boundary_host_when_ledger_writable(tmp_path):
    plan = plan_gate_boundary(attune_home=tmp_path / "attune")
    assert plan.boundary == HOST
    assert plan.env() == {"ATTUNE_HOME": str(tmp_path / "attune")}
    assert not list((tmp_path / "attune" / "ops" / "gates").iterdir())  # probe left no residue


def test_gate_boundary_isolated_when_unwritable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "attune.authoring.spec_workflow._probe_writable",
        lambda directory: "EPERM: read-only sandbox",
    )
    plan = plan_gate_boundary(attune_home=tmp_path / "ro", isolated_root=tmp_path / "scratch")
    assert plan.boundary == ISOLATED
    assert plan.attune_home == tmp_path / "scratch" / "attune-home"
    assert plan.attune_home.is_dir()
    assert "EPERM" in plan.reason  # restriction reported, not rediscovered
    assert plan.env()["ATTUNE_HOME"] == str(plan.attune_home)


def test_gate_boundary_blocked_when_real_receipt_required(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "attune.authoring.spec_workflow._probe_writable",
        lambda directory: "EPERM: read-only sandbox",
    )
    plan = plan_gate_boundary(require_real_ledger=True, attune_home=tmp_path / "ro")
    assert plan.boundary == BLOCKED
    assert plan.attune_home is None
    assert "trusted host boundary" in plan.reason
    with pytest.raises(RuntimeError, match="blocked"):
        plan.env()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission semantics")
def test_gate_boundary_real_unwritable_directory(tmp_path):
    ro_home = tmp_path / "ro-home"
    (ro_home / "ops" / "gates").mkdir(parents=True)
    (ro_home / "ops" / "gates").chmod(0o500)
    try:
        plan = plan_gate_boundary(attune_home=ro_home, isolated_root=tmp_path / "scratch")
        assert plan.boundary == ISOLATED
    finally:
        (ro_home / "ops" / "gates").chmod(0o700)


def test_gate_boundary_respects_attune_home_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "env-home"))
    plan = plan_gate_boundary()
    assert plan.boundary == HOST
    assert plan.attune_home == tmp_path / "env-home"
