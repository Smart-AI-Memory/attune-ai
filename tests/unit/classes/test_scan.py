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

    def test_parse_error_reported_as_hit_not_crash(self, tmp_path):
        _write(tmp_path, "bad.py", "def broken(:\n")
        result = scan_paths([tmp_path], repo_root=tmp_path)
        assert [h["rule_id"] for h in result["hits"]] == ["PARSE-ERROR"]
        assert result["scan_errors"] == []

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
