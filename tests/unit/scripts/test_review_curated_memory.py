"""Tests for the P2 verdict-loop CLI (memory-status-integrity task 5).

Loads the script via importlib (the scripts-test idiom). Everything is
hermetic under ``tmp_path`` — the interactive path is driven by a
monkeypatched ``input``, and Redis propagation is monkeypatched to a
no-op recorder (the real function is covered in test_verdict_log.py).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "review_curated_memory.py"

sys.path.insert(0, str(REPO_ROOT / "src"))

from attune.memory.curated_audit import load_memory, sweep  # noqa: E402
from attune.memory.verdict_log import VerdictRecord, append_verdict, load_verdicts  # noqa: E402


def _load_script():
    spec = importlib.util.spec_from_file_location("_review_curated_memory", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_mem(root: Path, stem: str, mem_type: str = "project") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{stem}.md"
    path.write_text(
        "---\n"
        f"name: {stem}\n"
        "description: a claim\n"
        "metadata:\n"
        f"  type: {mem_type}\n"
        "---\n\nThe body.\n",
        encoding="utf-8",
    )
    return path


class TestBuildQueue:
    def test_caps_the_queue_and_excludes_tombstoned(self, tmp_path: Path) -> None:
        mod = _load_script()
        for i in range(5):
            _write_mem(tmp_path, f"project_{i}")
        dead = load_memory(_write_mem(tmp_path, "project_dead"))
        append_verdict(tmp_path, VerdictRecord.create(dead.stem, "wrong", dead.digest, "t"))

        report = sweep([tmp_path])
        queue = mod.build_queue(report, limit=3)
        assert len(queue) == 3
        assert all(mem.stem != "project_dead" for mem, _, _, _ in queue)
        assert all(reasons == [] for _, _, _, reasons in queue)

    def test_empty_report_yields_empty_queue(self, tmp_path: Path) -> None:
        mod = _load_script()
        report = sweep([tmp_path])
        assert mod.build_queue(report, limit=3) == []

    def test_ref_triggered_memory_floats_to_front(self, tmp_path: Path) -> None:
        """P2 task 7 (D7): a triggered project memory queue-jumps ABOVE the
        age-ranked rows — promote-only, and reasons ride with the row."""
        mod = _load_script()
        for i in range(3):
            _write_mem(tmp_path, f"project_old_{i}")
        _write_mem(tmp_path, "project_fresh")

        def _stub_reasons(mem):
            return ["pr:99 is MERGED"] if mem.stem == "project_fresh" else []

        report = sweep([tmp_path])
        queue = mod.build_queue(report, limit=2, ref_reasons=_stub_reasons)
        assert queue[0][0].stem == "project_fresh"
        assert queue[0][3] == ["pr:99 is MERGED"]
        assert all(r == [] for _, _, _, r in queue[1:])

    def test_ref_checks_only_project_type(self, tmp_path: Path) -> None:
        """Non-project memories never spend ref probes (D6#4 scope)."""
        mod = _load_script()
        _write_mem(tmp_path, "feedback_rule", mem_type="feedback")
        asked = []

        def _recorder(mem):
            asked.append(mem.stem)
            return []

        report = sweep([tmp_path])
        mod.build_queue(report, limit=3, ref_reasons=_recorder)
        assert asked == []


class TestVerdictActions:
    def _run_one(self, tmp_path: Path, keystroke: str, monkeypatch):
        mod = _load_script()
        path = _write_mem(tmp_path, "project_v")
        mem = load_memory(path)
        propagated = []
        import attune.memory.verdict_log as vlog

        monkeypatch.setattr(
            vlog, "propagate_verdict", lambda stem, client=None: propagated.append(stem) or True
        )
        monkeypatch.setattr("builtins.input", lambda *_: keystroke)
        action = mod._review_one(mem, "mtime", 5, tmp_path, who="tester")
        return action, path, propagated

    def test_keep_sets_verified_and_appends_bound_record(self, tmp_path, monkeypatch) -> None:
        action, path, propagated = self._run_one(tmp_path, "k", monkeypatch)
        assert action == "keep"
        text = path.read_text(encoding="utf-8")
        assert "verified: " in text
        records = load_verdicts(tmp_path)
        assert [r.verdict for r in records] == ["keep"]
        assert records[0].digest == load_memory(path).digest
        assert propagated == ["project_v"]

    def test_wrong_tombstones_without_touching_the_file(self, tmp_path, monkeypatch) -> None:
        action, path, propagated = self._run_one(tmp_path, "w", monkeypatch)
        assert action == "wrong"
        text = path.read_text(encoding="utf-8")
        assert "verified:" not in text, "wrong must not stamp a verification"
        assert path.exists(), "tombstone never deletes"
        assert [r.verdict for r in load_verdicts(tmp_path)] == ["wrong"]
        assert propagated == ["project_v"]

    def test_skip_and_quit_write_nothing(self, tmp_path, monkeypatch) -> None:
        for keystroke, expected in [("", "skip"), ("q", "quit")]:
            action, path, propagated = self._run_one(tmp_path, keystroke, monkeypatch)
            assert action == expected
            assert "verified:" not in path.read_text(encoding="utf-8")
            assert load_verdicts(tmp_path) == []
            assert propagated == []
            path.unlink()

    def test_sharper_records_post_edit_digest(self, tmp_path, monkeypatch) -> None:
        mod = _load_script()
        path = _write_mem(tmp_path, "project_s")
        mem = load_memory(path)

        class _Done:
            returncode = 0

        def _fake_editor(argv, check=False):
            edit_path = Path(argv[-1])
            edit_path.write_text(
                edit_path.read_text(encoding="utf-8").replace("The body.", "The SHARPER body."),
                encoding="utf-8",
            )
            return _Done()

        import attune.memory.verdict_log as vlog

        monkeypatch.setattr(vlog, "propagate_verdict", lambda stem, client=None: True)
        monkeypatch.setattr(mod.subprocess, "run", _fake_editor)
        monkeypatch.setattr("builtins.input", lambda *_: "s")

        action = mod._review_one(mem, "mtime", 5, tmp_path, who="tester")
        assert action == "sharper"
        records = load_verdicts(tmp_path)
        assert [r.verdict for r in records] == ["sharper"]
        post_edit = load_memory(path)
        assert records[0].digest == post_edit.digest != mem.digest
        assert "verified: " in path.read_text(encoding="utf-8")


class TestD11Regressions:
    """Pins for the codex D11 lane findings on this diff."""

    def test_keep_append_failure_leaves_file_unstamped(self, tmp_path, monkeypatch) -> None:
        """Record-first ordering: an append failure must never leave a
        `verified:` stamp with no audit record behind it."""
        import pytest

        mod = _load_script()
        path = _write_mem(tmp_path, "project_k")
        mem = load_memory(path)
        import attune.memory.verdict_log as vlog

        def _boom(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(vlog, "append_verdict", _boom)
        monkeypatch.setattr("builtins.input", lambda *_: "k")
        with pytest.raises(OSError, match="disk full"):
            mod._review_one(mem, "mtime", 5, tmp_path, who="tester")
        assert "verified:" not in path.read_text(encoding="utf-8")

    def test_sharper_editor_launch_failure_skips(self, tmp_path, monkeypatch) -> None:
        mod = _load_script()
        path = _write_mem(tmp_path, "project_e1")
        mem = load_memory(path)

        def _missing_editor(argv, check=False):
            raise OSError("no such editor")

        monkeypatch.setattr(mod.subprocess, "run", _missing_editor)
        monkeypatch.setattr("builtins.input", lambda *_: "s")
        assert mod._review_one(mem, "mtime", 5, tmp_path, who="t") == "skip"
        assert "verified:" not in path.read_text(encoding="utf-8")
        assert load_verdicts(tmp_path) == []

    def test_sharper_editor_nonzero_exit_skips(self, tmp_path, monkeypatch) -> None:
        """An aborted edit (editor rc != 0) must not verify anything."""
        mod = _load_script()
        path = _write_mem(tmp_path, "project_e2")
        mem = load_memory(path)

        class _Aborted:
            returncode = 1

        monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _Aborted())
        monkeypatch.setattr("builtins.input", lambda *_: "s")
        assert mod._review_one(mem, "mtime", 5, tmp_path, who="t") == "skip"
        assert "verified:" not in path.read_text(encoding="utf-8")
        assert load_verdicts(tmp_path) == []

    def test_main_survives_per_item_write_failure(self, tmp_path, monkeypatch, capsys) -> None:
        """One unwritable item records an error and the triage continues
        to exit 0 (the always-exit-zero contract)."""
        mod = _load_script()
        _write_mem(tmp_path, "project_a")
        import attune.memory.verdict_log as vlog

        def _boom(*a, **k):
            raise OSError("read-only corpus")

        monkeypatch.setattr(vlog, "append_verdict", _boom)
        monkeypatch.setattr(mod.sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda *_: "w")
        rc = mod.main(["--root", str(tmp_path), "--limit", "1", "--who", "t"])
        assert rc == 0
        assert "ERROR on project_a" in capsys.readouterr().out


class TestMainNonInteractive:
    def test_dry_run_prints_queue_and_writes_nothing(self, tmp_path, monkeypatch, capsys) -> None:
        mod = _load_script()
        _write_mem(tmp_path, "project_a")
        rc = mod.main(["--root", str(tmp_path), "--dry-run", "--limit", "2"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "project_a" in out
        assert not (tmp_path / ".verdicts.jsonl").exists()

    def test_no_corpora_exits_zero(self, monkeypatch, capsys) -> None:
        mod = _load_script()
        monkeypatch.setattr(mod, "default_roots", lambda: [])
        assert mod.main([]) == 0
        assert "No curated memory corpora" in capsys.readouterr().out
