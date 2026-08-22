"""Teeth mechanism (release-audit-stage R5, Phase 2 — UNARMED).

The R5 acceptance fixtures: a deliberately re-exposed ungated class
blocks; an active DEFER rides; an expired DEFER re-blocks. All
through real git repos — the boundary is git and the register.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from attune.classes.teeth import FindingIdentity, decide, finding_identities, re_exposed

R7A_SITE = """
import yaml
def load_cfg(text):
    try:
        cfg = yaml.safe_load(text)
    except ValueError:
        cfg = None
    return cfg
"""


def _git(repo: Path, *args: str, **kw) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, timeout=30, **kw)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(tmp_path, "config", k, v)
    _git(tmp_path, "remote", "add", "origin", "git@github.com:Smart-AI-Memory/attune-ai.git")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text("x = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _sha(repo: Path, ref: str = "HEAD") -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ref],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.strip()


class TestFindingIdentity:
    def test_anchor_is_symbol_not_line(self):
        a = finding_identities(textwrap.dedent(R7A_SITE), "src/mod.py")
        b = finding_identities("\n\n\n" + textwrap.dedent(R7A_SITE), "src/mod.py")
        assert a == b  # moved lines, same identity
        assert a == {FindingIdentity("R7a-parse-under-narrow-except", "src/mod.py", "load_cfg")}

    def test_module_level_anchor(self):
        ids = finding_identities("import json\nd = json.loads(x)\nd['k']\n", "m.py")
        assert any(i.anchor == "<module>" for i in ids)


class TestReExposed:
    def test_new_finding_detected(self, repo):
        base_sha = _sha(repo)
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE))
        _git(repo, "commit", "-qam", "introduce")
        new = re_exposed(repo, base_sha, ["src/mod.py"])
        assert [n.rule_id for n in new] == ["R7a-parse-under-narrow-except"]

    def test_preexisting_finding_is_register_debt_not_reexposure(self, repo):
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE))
        _git(repo, "commit", "-qam", "introduce")
        base_sha = _sha(repo)
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE) + "\ny = 2\n")
        _git(repo, "commit", "-qam", "unrelated edit")
        assert re_exposed(repo, base_sha, ["src/mod.py"]) == []

    def test_rename_tracked_not_reexposed(self, repo):
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE))
        _git(repo, "commit", "-qam", "introduce")
        base_sha = _sha(repo)
        _git(repo, "mv", "src/mod.py", "src/renamed.py")
        _git(repo, "commit", "-qm", "rename only")
        assert re_exposed(repo, base_sha, ["src/renamed.py"]) == []


class TestDecide:
    def test_reexposed_ungated_class_blocks(self, repo):
        base_sha = _sha(repo)
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE))
        _git(repo, "commit", "-qam", "introduce")
        result = decide(repo_root=repo, baseline_sha=base_sha, changed_files=["src/mod.py"])
        assert len(result["blocks"]) == 1
        assert "gate-first" in result["blocks"][0]["reason"]

    def test_active_defer_rides_block_resumes_at_expiry(self, repo):
        base_sha = _sha(repo)
        (repo / "src" / "mod.py").write_text(textwrap.dedent(R7A_SITE))
        _git(repo, "commit", "-qam", "introduce")
        created = _sha(repo)
        defers = repo / ".attune" / "defers"
        defers.mkdir(parents=True)
        for cid in ("C4a", "C4b"):
            (defers / f"{cid}.yaml").write_text(
                f"class_id: {cid}\nfinding_identity: 'R7a:src/mod.py'\nowner: p\n"
                f"reason: gate next release\napproved_at: '2026-08-22'\n"
                f"created_sha: {created}\nexpires_after_releases: 1\nchair_receipt: ruled\n"
            )
        active = decide(repo_root=repo, baseline_sha=base_sha, changed_files=["src/mod.py"])
        assert active["blocks"] == []
        assert len(active["deferred"]) == 1

        _git(repo, "tag", "v1.0.1")  # one release since -> DEFER expires
        resumed = decide(repo_root=repo, baseline_sha=base_sha, changed_files=["src/mod.py"])
        assert len(resumed["blocks"]) == 1  # the block RESUMED (D6)

    def test_advisory_rule_warns_never_blocks(self, repo):
        base_sha = _sha(repo)
        (repo / "src" / "mod.py").write_text(
            "import subprocess\ndef go():\n    subprocess.run(['ls'])\n"
        )
        _git(repo, "commit", "-qam", "advisory only")
        result = decide(repo_root=repo, baseline_sha=base_sha, changed_files=["src/mod.py"])
        assert result["blocks"] == []
        assert any("never blocks" in w["reason"] for w in result["warns"])
