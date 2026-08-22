"""Rule pack (release-audit-stage R1, Phase 0)."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from attune.classes.rules import (
    RULES,
    Calibration,
    Rule,
    calibrated_here,
    canonical_repo_id,
    scan_source,
)


def _hits(source: str, rule_id: str | None = None):
    hits = scan_source(textwrap.dedent(source), "probe.py")
    return [h for h in hits if rule_id is None or h.rule_id == rule_id]


class TestV1Rules:
    def test_r1_json_loads_outside_try_flags(self):
        assert _hits("import json\ndata = json.loads(raw)\n", "R1-json-loads-unguarded")

    def test_r1_inside_try_clean(self):
        src = """
            import json
            try:
                data = json.loads(raw)
            except ValueError:
                data = {}
        """
        assert not _hits(src, "R1-json-loads-unguarded")

    def test_r2_kwargs_update_flags(self):
        src = """
            def f(**kwargs):
                d = {}
                d.update(kwargs)
        """
        assert _hits(src, "R2-update-kwargs")

    def test_r3_coalesce_before_isinstance_flags(self):
        src = """
            def f(x):
                y = x or {}
                if isinstance(y, dict):
                    return y
        """
        assert _hits(src, "R3-coalesce-before-check")

    def test_r4_subprocess_without_timeout_flags(self):
        assert _hits("import subprocess\nsubprocess.run(['ls'])\n", "R4-subprocess-no-timeout")

    def test_r4_with_timeout_clean(self):
        assert not _hits(
            "import subprocess\nsubprocess.run(['ls'], timeout=5)\n", "R4-subprocess-no-timeout"
        )

    def test_r5_jsondump_oserror_only_flags(self):
        src = """
            import json
            try:
                json.dump(data, fh)
            except OSError:
                pass
        """
        assert _hits(src, "R5-narrow-except-jsondump")

    def test_r6_redis_fstring_key_flags(self):
        src = """
            def f(client, uid):
                client.get(f"user:{uid}")
        """
        assert _hits(src, "R6-redis-fstring-key")


class TestR7Rules:
    def test_r7a_yaml_without_yamlerror_flags(self):
        src = """
            import yaml
            try:
                cfg = yaml.safe_load(text)
            except ValueError:
                cfg = None
        """
        hits = _hits(src, "R7a-parse-under-narrow-except")
        assert hits and "YAMLError" in hits[0].detail

    def test_r7a_with_yamlerror_clean(self):
        src = """
            import yaml
            try:
                cfg = yaml.safe_load(text)
            except yaml.YAMLError:
                cfg = None
        """
        assert not _hits(src, "R7a-parse-under-narrow-except")

    def test_r7b_parsed_then_get_flags(self):
        src = """
            import json
            def f(raw):
                data = json.loads(raw)
                return data.get("k")
        """
        assert _hits(src, "R7b-parse-then-unguarded-access")

    def test_r7b_isinstance_guard_clean(self):
        src = """
            import json
            def f(raw):
                data = json.loads(raw)
                if not isinstance(data, dict):
                    return None
                return data.get("k")
        """
        assert not _hits(src, "R7b-parse-then-unguarded-access")


class TestScanSource:
    def test_unparseable_source_yields_parse_error_hit(self):
        hits = scan_source("def broken(:\n", "bad.py")
        assert [h.rule_id for h in hits] == ["PARSE-ERROR"]

    def test_null_byte_source_yields_parse_error_hit(self):
        # C4a portability: <=3.11 raises ValueError, 3.12+ SyntaxError.
        hits = scan_source("x = 1\x00\n", "null.py")
        assert [h.rule_id for h in hits] == ["PARSE-ERROR"]


class TestCalibration:
    def test_only_r7_rules_calibrated_on_attune_ai(self):
        repo = "smart-ai-memory/attune-ai"
        calibrated = {r.id for r in RULES if calibrated_here(r, repo)}
        assert calibrated == {
            "R7a-parse-under-narrow-except",
            "R7b-parse-then-unguarded-access",
        }

    def test_foreign_repo_has_no_calibrated_rules(self):
        assert not [r for r in RULES if calibrated_here(r, "acme/other")]

    def test_uncalibrated_rule_is_ineligible(self):
        rule = Rule("X", "inv", (), lambda t, p: [], None)
        assert not calibrated_here(rule, "smart-ai-memory/attune-ai")

    def test_r7_receipt_is_the_recorded_review_figure(self):
        r7a = next(r for r in RULES if r.id == "R7a-parse-under-narrow-except")
        assert isinstance(r7a.calibration, Calibration)
        assert abs(r7a.calibration.recall - 8 / 11) < 1e-9
        assert r7a.calibration.precision == 1.0

    def test_every_rule_has_invariant_and_check(self):
        for r in RULES:
            assert r.invariant
            assert callable(r.check)


class TestCanonicalRepoId:
    """Real-git round trips — the boundary is git, so exercise git."""

    def test_origin_slug_normalized(self, tmp_path: Path):
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "git@github.com:Acme/Widgets.git",
            ],
            check=True,
            timeout=30,
        )
        assert canonical_repo_id(tmp_path) == "acme/widgets"

    def test_https_url_normalized(self, tmp_path: Path):
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "https://github.com/Acme/Widgets",
            ],
            check=True,
            timeout=30,
        )
        assert canonical_repo_id(tmp_path) == "acme/widgets"

    def test_no_remote_falls_back_to_dir_name(self, tmp_path: Path):
        repo = tmp_path / "MyRepo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=30)
        assert canonical_repo_id(repo) == "myrepo"

    def test_not_a_repo_falls_back_to_dir_name(self, tmp_path: Path):
        d = tmp_path / "Plain"
        d.mkdir()
        assert canonical_repo_id(d) == "plain"
