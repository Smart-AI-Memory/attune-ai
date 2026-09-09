"""Repository identity must survive extraction, capping, and reconciliation."""

import pytest

from attune.hooks.scripts import starter_reconciler as hook


@pytest.mark.parametrize(
    "reference",
    [
        "Smart-AI-Memory/attune#9000",
        "[#9000](https://github.com/Smart-AI-Memory/attune/pull/9000)",
        "https://github.com/Smart-AI-Memory/attune/issues/9000",
        "[#9000](https://GitHub.com/Smart-AI-Memory/attune/pull/9000)",
        "https://www.github.com/Smart-AI-Memory/attune/issues/9000",
    ],
)
def test_foreign_reference_never_queried_as_local(reference, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(hook, "check_pr", lambda num, cwd: calls.append(num) or "MERGED")
    monkeypatch.setattr(hook, "merged_prs_on_main", lambda cwd: [2495, 2494])
    results = hook.reconcile(f"Local #2494; follow {reference}", None, tmp_path)

    assert calls == [2494]
    assert results["pr_ceiling"] == 2494
    assert results["newer_merges"] == [2495]
    banner = hook.format_banner(results, "project", tmp_path / "starter.md")
    assert "smart-ai-memory/attune#9000 unverified" in banner
    assert "#9000 MERGED" not in banner


def test_qualified_refs_cannot_consume_the_local_check_budget(monkeypatch):
    calls = []
    monkeypatch.setattr(hook, "check_pr", lambda num, cwd: calls.append(num) or "OPEN")
    monkeypatch.setattr(hook, "merged_prs_on_main", lambda cwd: [43])
    text = " ".join(f"foreign/repo#{n}" for n in range(100, 110)) + " local #42"

    results = hook.reconcile(text, None, None)

    assert calls == [42]
    assert results["pr_ceiling"] == 42
    assert results["newer_merges"] == [43]


@pytest.mark.parametrize("suffix", ["", ".", "/", ",", ")."])
def test_codex_branch_is_checked(monkeypatch, suffix):
    calls = []
    monkeypatch.setattr(hook, "check_branch", lambda branch, cwd: calls.append(branch) or "exists")

    results = hook.reconcile("Resume codex/starter-fixes" + suffix, None, None)

    assert calls == ["codex/starter-fixes"]
    assert results["branches"] == {"codex/starter-fixes": "exists"}


@pytest.mark.parametrize("identity", [None, "attune-ai"])
def test_unknown_identity_cannot_be_a_proven_repo_mismatch(tmp_path, monkeypatch, capsys, identity):
    starter = tmp_path / "starter.md"
    starter.write_text(
        "---\nrepo: smart-ai-memory/attune-ai\n---\nMerge PR #49\n", encoding="utf-8"
    )
    checked = []
    monkeypatch.setattr(hook, "repo_slug", lambda root: identity)
    monkeypatch.setattr(hook, "reconcile", lambda *args: checked.append(args))

    assert hook._reconcile_and_emit(starter, "project", tmp_path)

    output = capsys.readouterr().out
    assert "Repository identity unverified" in output
    assert "cross-repo" not in output
    assert checked == []


def test_expired_budget_does_not_fabricate_directory_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "_DEADLINE", hook.time.monotonic() - 1)
    assert hook.repo_slug(tmp_path) is None


@pytest.mark.parametrize(
    "reference",
    [
        "Smart-AI-Memory/attune-ai#42",
        "[PR](https://github.com/Smart-AI-Memory/attune-ai/pull/42)",
    ],
)
def test_matching_repo_is_checked_and_deduplicated(reference, monkeypatch):
    calls = []
    monkeypatch.setattr(hook, "check_pr", lambda num, cwd: calls.append(num) or "OPEN")
    monkeypatch.setattr(hook, "merged_prs_on_main", lambda cwd: [43])

    results = hook.reconcile(
        f"{reference} #42 foreign/repo#42", None, None, "smart-ai-memory/attune-ai"
    )

    assert calls == [42]
    assert results["pr_ceiling"] == 42
    assert results["newer_merges"] == [43]
    assert results["unverified_refs"] == ["foreign/repo#42"]


def test_matching_repo_uses_uncapped_ceiling(monkeypatch):
    monkeypatch.setattr(hook, "check_pr", lambda num, cwd: "OPEN")
    monkeypatch.setattr(hook, "merged_prs_on_main", lambda cwd: [901, 800])
    text = " ".join(f"#{n}" for n in range(10, 20)) + " local/repo#900"

    results = hook.reconcile(text, None, None, "local/repo")

    assert len(results["prs"]) == hook.MAX_PRS
    assert results["pr_ceiling"] == 900
    assert results["newer_merges"] == [901]


def test_known_issue_link_does_not_query_pr_even_in_matching_repo(monkeypatch):
    def unexpected(*args):
        pytest.fail("an issue link must not invoke the PR checker")

    monkeypatch.setattr(hook, "check_pr", unexpected)
    results = hook.reconcile(
        "[#42](https://github.com/local/repo/issues/42)", None, None, "local/repo"
    )
    assert results["prs"] == {}
    assert results["unverified_refs"] == ["local/repo#42"]


@pytest.mark.parametrize(
    "reference",
    [
        "codex/other#49",
        "https://github.com/claude/other/pull/49",
        "[#49](https://github.com/fix/other/issues/49)",
    ],
)
def test_repository_names_are_not_checked_as_local_branches(reference, monkeypatch):
    calls = []
    monkeypatch.setattr(hook, "check_branch", lambda branch, cwd: calls.append(branch) or "gone")

    results = hook.reconcile(reference + " on codex/actual-branch", None, None)

    assert calls == ["codex/actual-branch"]
    assert results["branches"] == {"codex/actual-branch": "gone"}
