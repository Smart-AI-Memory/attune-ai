"""Scan CLI plumbing (release-audit-stage R1, Phase 0)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from attune.classes.scan import main, scan_paths


def _write(tmp_path: Path, name: str, body: str) -> Path:
    f = tmp_path / name
    f.write_text(textwrap.dedent(body))
    return f


class TestScanPaths:
    def test_hits_carry_advisory_flag_by_calibration(self, tmp_path):
        _write(
            tmp_path,
            "mod.py",
            """
            import json
            import subprocess
            def f(raw):
                data = json.loads(raw)
                return data.get("k")
            subprocess.run(["ls"])
        """,
        )
        result = scan_paths([tmp_path], repo_root=tmp_path)
        by_rule = {h["rule_id"]: h for h in result["hits"]}
        # tmp repo identity != attune-ai: EVERYTHING is advisory here
        assert by_rule["R7b-parse-then-unguarded-access"]["advisory"] is True
        assert by_rule["R4-subprocess-no-timeout"]["advisory"] is True

    def test_parse_error_preserves_hit_and_marks_scan_incomplete(self, tmp_path):
        _write(tmp_path, "bad.py", "def broken(:\n")
        result = scan_paths([tmp_path], repo_root=tmp_path)
        assert [h["rule_id"] for h in result["hits"]] == ["PARSE-ERROR"]
        assert result["scan_errors"][0]["path"] == str(tmp_path / "bad.py")
        assert "invalid syntax" in result["scan_errors"][0]["error"]

    def test_pycache_excluded(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        _write(cache, "junk.py", "import json\njson.loads('x')\n")
        result = scan_paths([tmp_path], repo_root=tmp_path)
        assert result["files_scanned"] == 0

    def test_single_file_path(self, tmp_path):
        f = _write(tmp_path, "one.py", "import subprocess\nsubprocess.call(['x'])\n")
        result = scan_paths([f], repo_root=tmp_path)
        assert result["files_scanned"] == 1
        assert result["hits"][0]["rule_id"] == "R4-subprocess-no-timeout"

    def test_rules_metadata_carries_calibration(self, tmp_path):
        result = scan_paths([tmp_path], repo_root=tmp_path)
        meta = result["rules"]["R7a-parse-under-narrow-except"]
        assert meta["calibration"]["ground_truth"].startswith("11 confirmed")
        assert meta["class_ids"] == ["C4a", "C4b"]


class TestCli:
    def test_main_clean_exit_and_json(self, tmp_path, capsys):
        _write(tmp_path, "ok.py", "x = 1\n")
        rc = main(["--paths", str(tmp_path), "--repo-root", str(tmp_path)])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["files_scanned"] == 1

    def test_main_parse_error_fails_but_still_reports_other_files(self, tmp_path, capsys):
        _write(tmp_path, "bad.py", "def broken(:\n")
        _write(tmp_path, "ok.py", "import subprocess\nsubprocess.run(['ls'])\n")
        assert main(["--paths", str(tmp_path), "--repo-root", str(tmp_path)]) == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["files_scanned"] == 2
        assert {hit["rule_id"] for hit in payload["hits"]} >= {
            "PARSE-ERROR",
            "R4-subprocess-no-timeout",
        }
        assert len(payload["scan_errors"]) == 1


def test_custom_parse_error_named_rule_does_not_mark_valid_source_incomplete(tmp_path):
    from attune.classes.rules import Hit, Rule

    path = _write(tmp_path, "valid.py", "x = 1\n")
    rule = Rule(
        "PARSE-ERROR",
        "custom advisory label",
        (),
        lambda tree, name: [Hit("PARSE-ERROR", name, 1, "custom finding")],
    )
    result = scan_paths([path], repo_root=tmp_path, rules=(rule,))
    assert result["scan_errors"] == []
    assert result["hits"][0]["detail"] == "custom finding"
