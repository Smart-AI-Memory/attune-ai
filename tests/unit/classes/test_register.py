"""Derived register (release-audit-stage R2, Phase 0).

Register-Class drift guard lives here: every GATES mapping must
resolve against THIS repo — file present, test present, identity tag
matching — so a renamed or reassigned gate fails CI loudly.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from attune.classes.register import (
    GATES,
    GateRef,
    derive_register,
    load_defers,
    load_dispositions,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _git(repo: Path, *args: str, **kw) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, timeout=30, **kw)


def _fixture_repo(tmp_path: Path) -> Path:
    """A real git repo whose origin slug matches the R7 calibration."""
    _git(tmp_path.parent, "init", "-q", str(tmp_path)) if False else None
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(tmp_path, "config", k, v)
    _git(tmp_path, "remote", "add", "origin", "git@github.com:Smart-AI-Memory/attune-ai.git")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(
        textwrap.dedent(
            """
            import json
            def f(raw):
                data = json.loads(raw)
                return data.get("k")
            """
        )
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


class TestDriftGuard:
    def test_every_gate_mapping_resolves_in_this_repo(self):
        problems = [g.resolution_problem(REPO_ROOT) for g in GATES]
        assert problems == [None] * len(GATES), problems

    def test_missing_file_is_a_problem(self, tmp_path):
        g = GateRef("C3", "tests/nope.py", "test_x")
        assert "missing" in g.resolution_problem(tmp_path)

    def test_renamed_test_is_a_problem(self, tmp_path):
        f = tmp_path / "gate.py"
        f.write_text('"""Register-Class: C3\n"""\ndef test_other():\n    pass\n')
        g = GateRef("C3", "gate.py", "test_x")
        assert "renamed away" in g.resolution_problem(tmp_path)

    def test_missing_identity_tag_is_a_problem(self, tmp_path):
        f = tmp_path / "gate.py"
        f.write_text("def test_x():\n    pass\n")
        g = GateRef("C3", "gate.py", "test_x")
        assert "identity tag missing" in g.resolution_problem(tmp_path)

    def test_reassigned_tag_is_a_problem(self, tmp_path):
        # Gate file claims a DIFFERENT class than the mapping asserts.
        f = tmp_path / "gate.py"
        f.write_text('"""Register-Class: G1\n"""\ndef test_x():\n    pass\n')
        g = GateRef("C3", "gate.py", "test_x")
        assert "identity tag missing" in g.resolution_problem(tmp_path)


class TestDeriveRegister:
    def test_open_when_calibrated_hits_and_no_gate(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        # fixture mod.py is an R7b (C3) site; no gate file in fixture repo
        assert rows["C3"]["status"] == "OPEN"
        assert rows["C3"]["calibrated_hits"] == 1

    def test_fixed_but_ungated_when_no_hits(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        (repo / "src" / "mod.py").write_text("x = 1\n")
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        assert rows["C3"]["status"] == "FIXED-BUT-UNGATED"

    def test_closed_and_broken_gate_quadrants(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        gate = repo / "tests_gate.py"
        gate.write_text('"""Register-Class: C3\n"""\ndef test_c3_gate():\n    pass\n')
        import attune.classes.register as reg

        ref = GateRef("C3", "tests_gate.py", "test_c3_gate")
        orig = reg.GATES
        reg.GATES = (ref,)
        try:
            broken = derive_register(repo_root=repo)
            rows = {r["class_id"]: r for r in broken["rows"]}
            assert rows["C3"]["status"] == "BROKEN-GATE"  # gate + hits>0 = loud
            (repo / "src" / "mod.py").write_text("x = 1\n")
            closed = derive_register(repo_root=repo)
            rows = {r["class_id"]: r for r in closed["rows"]}
            assert rows["C3"]["status"] == "CLOSED"
        finally:
            reg.GATES = orig

    def test_unmechanized_when_no_calibrated_rule_and_no_gate(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        # C1 maps only to an uncalibrated v1 rule
        assert rows["C1"]["status"] == "UNMECHANIZED"

    def test_dispositions_subtract_dismissed_hits(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        (repo / ".attune").mkdir(exist_ok=True)
        (repo / ".attune" / "class-dispositions.yaml").write_text(
            "- rule_id: R7b-parse-then-unguarded-access\n"
            "  path: src/mod.py\n"
            "  reason: internal data, dismissed after inspection\n"
        )
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        assert rows["C3"]["status"] == "FIXED-BUT-UNGATED"
        assert result["dispositions_applied"] == 1

    def test_deferred_overrides_open(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        defers = repo / ".attune" / "defers"
        defers.mkdir(parents=True)
        (defers / "C3.yaml").write_text(
            f"class_id: C3\nfinding_identity: 'R7b:src/mod.py'\nowner: patrick\n"
            f"reason: gate lands next release\napproved_at: '2026-08-22'\n"
            f"created_sha: {sha}\nexpires_after_releases: 1\nchair_receipt: 'ruled 2026-08-22'\n"
        )
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        assert rows["C3"]["status"] == "DEFERRED"
        assert rows["C3"]["defer"] == "ruled 2026-08-22"

    def test_defer_expires_after_release_tag(self, tmp_path):
        repo = _fixture_repo(tmp_path)
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        defers = repo / ".attune" / "defers"
        defers.mkdir(parents=True)
        (defers / "C3.yaml").write_text(
            f"class_id: C3\nfinding_identity: x\nowner: p\nreason: r\n"
            f"approved_at: '2026-08-22'\ncreated_sha: {sha}\n"
            f"expires_after_releases: 1\nchair_receipt: c\n"
        )
        _git(repo, "tag", "v99.0.0")  # one release since the record
        result = derive_register(repo_root=repo)
        rows = {r["class_id"]: r for r in result["rows"]}
        assert rows["C3"]["status"] == "OPEN"  # block resumed


class TestLoaders:
    def test_invalid_defer_is_a_problem_never_active(self, tmp_path):
        d = tmp_path / ".attune" / "defers"
        d.mkdir(parents=True)
        (d / "bad.yaml").write_text("class_id: C3\n")  # missing keys
        records, problems = load_defers(tmp_path)
        assert records == []
        assert "missing keys" in problems[0]

    def test_unparseable_defer_is_a_problem(self, tmp_path):
        d = tmp_path / ".attune" / "defers"
        d.mkdir(parents=True)
        (d / "bad.yaml").write_text(":\n  - ][\n")
        records, problems = load_defers(tmp_path)
        assert records == [] and problems

    def test_absent_defer_dir_is_clean(self, tmp_path):
        assert load_defers(tmp_path) == ([], [])

    def test_dispositions_not_a_list_is_a_problem(self, tmp_path):
        (tmp_path / ".attune").mkdir()
        (tmp_path / ".attune" / "class-dispositions.yaml").write_text("a: b\n")
        valid, problems = load_dispositions(tmp_path)
        assert valid == [] and "not a list" in problems[0]

    def test_dispositions_missing_keys_is_a_problem(self, tmp_path):
        (tmp_path / ".attune").mkdir()
        (tmp_path / ".attune" / "class-dispositions.yaml").write_text("- rule_id: R1\n")
        valid, problems = load_dispositions(tmp_path)
        assert valid == [] and problems

    def test_absent_dispositions_is_clean(self, tmp_path):
        assert load_dispositions(tmp_path) == ([], [])


class TestDispositionPathSeparators:
    """Disposition matching must not depend on the host's path separator.

    ``_rel`` used ``str(Path(...))``, which renders the NATIVE separator:
    on Windows a hit became ``src\\mod.py`` while a disposition file —
    authored by hand and compared verbatim — says ``src/mod.py``, so the
    tuple never matched and EVERY disposition was silently ignored there.

    The behaviour itself CANNOT be simulated off-Windows: on POSIX a
    backslash is an ordinary filename character, so ``Path`` will not
    treat it as a separator and ``as_posix()`` leaves it alone. The
    behavioural coverage is therefore
    ``test_dispositions_subtract_dismissed_hits`` running on the Windows
    lanes; what runs everywhere is this source guard, so a revert fails
    fast instead of waiting on a lane that is not required to merge.
    """

    def test_both_sides_are_normalised_with_as_posix(self):
        """A revert to str(Path(...)) reintroduces the Windows bug."""
        import ast
        import inspect

        from attune.classes.register import _subtract_dispositions

        source = textwrap.dedent(inspect.getsource(_subtract_dispositions))
        tree = ast.parse(source)

        posix_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "as_posix"
        ]
        assert len(posix_calls) >= 3, (
            "_subtract_dispositions must normalise BOTH the disposition side "
            "and both _rel return paths with .as_posix(); found "
            f"{len(posix_calls)} call(s). str(Path(...)) renders the native "
            "separator and silently drops every disposition on Windows."
        )

    def test_unrelated_path_is_still_kept(self):
        """Normalisation must not make everything match."""
        from attune.classes.register import _subtract_dispositions

        hits = [{"rule_id": "R7b", "path": "src/other.py"}]
        dispositions = [{"rule_id": "R7b", "path": "src/mod.py", "reason": "dismissed"}]

        assert _subtract_dispositions(hits, dispositions, Path.cwd()) == hits

    def test_matching_path_is_still_subtracted(self):
        """The ordinary same-separator case keeps working."""
        from attune.classes.register import _subtract_dispositions

        hits = [{"rule_id": "R7b", "path": "src/mod.py"}]
        dispositions = [{"rule_id": "R7b", "path": "src/mod.py", "reason": "dismissed"}]

        assert _subtract_dispositions(hits, dispositions, Path.cwd()) == []


class TestShippedDispositions:
    def test_shipped_dispositions_file_is_schema_valid(self):
        valid, problems = load_dispositions(REPO_ROOT)
        assert problems == []
        assert len(valid) >= 45  # populated 2026-08-22 from the review ledgers

    def test_shipped_dispositions_reasons_are_never_empty(self):
        valid, _ = load_dispositions(REPO_ROOT)
        assert all(d["reason"].strip() for d in valid)
