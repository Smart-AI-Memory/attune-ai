"""G5 gate logic tests (claim-drift-gates) — hard-fail detection, the
shrink-only ratchet, and tier accounting, against scratch git trees.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from check_brand_drift import (  # noqa: E402
    hard_failures,
    load_allowlist,
    ratchet_check,
    tracked_files,
)


def _repo(tmp_path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


class TestHardFail:
    def test_detects_all_three_tokens(self, tmp_path):
        repo = _repo(
            tmp_path,
            {
                "a.py": "install empathy-framework now",
                "b.sh": "curl Deep-Study-AI/thing && empathy-scan all",
                "clean.py": "print('attune')",
            },
        )
        hits = hard_failures(tracked_files(repo), repo)
        assert hits == {
            "a.py": ["empathy-framework"],
            "b.sh": ["Deep-Study-AI", "empathy-scan"],
        }

    def test_historical_surfaces_excluded(self, tmp_path):
        repo = _repo(
            tmp_path,
            {
                "CHANGELOG.md": "renamed from empathy-framework",
                "docs/specs/x/notes.md": "empathy-scan history",
                "docs/history/report.md": "empathy-framework era",
            },
        )
        assert hard_failures(tracked_files(repo), repo) == {}


class TestRatchet:
    def test_new_file_fails_allowlisted_passes(self, tmp_path):
        repo = _repo(
            tmp_path,
            {
                "src/old.py": "EMPATHY_LEVEL = 1",
                "src/new.py": "empathy_mode = True",
                "src/clean.py": "x = 1",
            },
        )
        allow = {"src/old.py": "internal"}
        new_debt, stale, counts = ratchet_check(tracked_files(repo), allow, repo)
        assert new_debt == ["src/new.py"]
        assert stale == []
        assert counts == {"user-facing": 0, "internal": 1}

    def test_shrink_on_fix_enforced(self, tmp_path):
        repo = _repo(tmp_path, {"src/fixed.py": "no legacy words here"})
        allow = {"src/fixed.py": "internal"}
        _new, stale, _counts = ratchet_check(tracked_files(repo), allow, repo)
        assert stale == ["src/fixed.py"]  # must leave the list in the fix commit

    def test_scope_limited_to_three_roots(self, tmp_path):
        repo = _repo(tmp_path, {"docs/guides/deep.md": "empathy everywhere"})
        new_debt, _stale, _counts = ratchet_check(tracked_files(repo), {}, repo)
        assert new_debt == []  # docs/guides is outside the ratchet scope


class TestAllowlistFormat:
    def test_two_tier_parse(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text(
            "# comment\n# user-facing\nplugin/a.md\n# internal\nsrc/b.py\n",
            encoding="utf-8",
        )
        assert load_allowlist(f) == {
            "plugin/a.md": "user-facing",
            "src/b.py": "internal",
        }

    def test_repo_allowlist_exists_with_both_tiers(self):
        entries = load_allowlist()
        tiers = set(entries.values())
        assert tiers == {"user-facing", "internal"}
        assert len(entries) > 100  # the seeded burn-down baseline
