"""Tests for the session-hook fleet projector (session-start-integrity R6).

Covers registry validation, drift detection, idempotent projection,
settings-entry merging, and the home-escape guard.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "sync_session_hooks.py"


@pytest.fixture(scope="module")
def projector():
    spec = importlib.util.spec_from_file_location("_sync_session_hooks", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_sync_session_hooks"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fleet(tmp_path, projector, monkeypatch):
    """A canonical source + one sibling, registry pointed at both."""
    canonical = tmp_path / "canon"
    canonical.mkdir()
    (canonical / "spec_orient.py").write_text("print('orient v1')\n", encoding="utf-8")
    (canonical / "_state.py").write_text("STATE = 1\n", encoding="utf-8")
    sibling = tmp_path / "sib"
    sibling.mkdir()
    registry = {
        "canonical_dir": "canon",
        "files": ["spec_orient.py", "_state.py"],
        "settings_command": "python .claude/hooks/spec_orient.py",
        "settings_timeout": 4000,
        "siblings": ["~/sib"],
    }
    monkeypatch.setattr(projector, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(projector.Path, "home", classmethod(lambda cls: tmp_path))
    return registry, sibling


class TestRegistry:
    def test_load_validates_required_keys(self, projector, tmp_path):
        bad = tmp_path / "reg.json"
        bad.write_text(json.dumps({"canonical_dir": "x"}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing required key"):
            projector.load_registry(bad)

    def test_empty_siblings_rejected(self, projector, tmp_path):
        bad = tmp_path / "reg.json"
        bad.write_text(
            json.dumps(
                {
                    "canonical_dir": "x",
                    "files": ["a"],
                    "siblings": [],
                    "settings_command": "c",
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="non-empty"):
            projector.load_registry(bad)

    def test_real_registry_loads_and_names_canonical_files(self, projector):
        registry = projector.load_registry()
        canonical = projector.REPO_ROOT / registry["canonical_dir"]
        for name in registry["files"]:
            assert (canonical / name).is_file(), f"canonical {name} missing"

    def test_sibling_escape_rejected(self, projector, monkeypatch, tmp_path):
        monkeypatch.setattr(projector.Path, "home", classmethod(lambda cls: tmp_path / "home"))
        (tmp_path / "home").mkdir()
        with pytest.raises(ValueError, match="escapes home"):
            projector._resolve_sibling("~/../outside")


class TestCheckAndWrite:
    def test_missing_files_detected(self, projector, fleet):
        registry, sibling = fleet
        findings = projector.check_sibling(sibling, registry)
        assert any("missing spec_orient.py" in f or "missing" in f for f in findings)

    def test_write_then_check_clean(self, projector, fleet):
        registry, sibling = fleet
        actions = projector.write_sibling(sibling, registry)
        assert any("wrote" in a for a in actions)
        assert any("settings entry" in a for a in actions)
        assert projector.check_sibling(sibling, registry) == []

    def test_write_is_idempotent(self, projector, fleet):
        registry, sibling = fleet
        projector.write_sibling(sibling, registry)
        assert projector.write_sibling(sibling, registry) == []

    def test_divergence_detected_and_healed(self, projector, fleet):
        registry, sibling = fleet
        projector.write_sibling(sibling, registry)
        drifted = sibling / ".claude" / "hooks" / "spec_orient.py"
        drifted.write_text("print('hand-edited twin')\n", encoding="utf-8")
        findings = projector.check_sibling(sibling, registry)
        assert any("divergent" in f and "spec_orient.py" in f for f in findings)
        projector.write_sibling(sibling, registry)
        assert projector.check_sibling(sibling, registry) == []

    def test_existing_settings_preserved(self, projector, fleet):
        registry, sibling = fleet
        settings_path = sibling / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]}}),
            encoding="utf-8",
        )
        projector.write_sibling(sibling, registry)
        merged = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "Stop" in merged["hooks"], "unrelated hooks clobbered"
        assert projector._settings_has_entry(merged, "spec_orient.py")


class TestMalformedSettingsRefused:
    """Cross-review F2 (codex, 2026-08-18): a malformed settings.json
    must be REFUSED, never treated as empty and overwritten."""

    def test_malformed_settings_left_untouched(self, projector, fleet):
        registry, sibling = fleet
        settings_path = sibling / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text("{not valid json", encoding="utf-8")
        actions = projector.write_sibling(sibling, registry)
        assert any("REFUSED settings edit" in a for a in actions)
        assert settings_path.read_text(encoding="utf-8") == "{not valid json"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
