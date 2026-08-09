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
        assert all(mem.stem != "project_dead" for mem, _, _ in queue)

    def test_empty_report_yields_empty_queue(self, tmp_path: Path) -> None:
        mod = _load_script()
        report = sweep([tmp_path])
        assert mod.build_queue(report, limit=3) == []


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

        def _fake_editor(argv, check=False):
            edit_path = Path(argv[-1])
            edit_path.write_text(
                edit_path.read_text(encoding="utf-8").replace("The body.", "The SHARPER body."),
                encoding="utf-8",
            )

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
