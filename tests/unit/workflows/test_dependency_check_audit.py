"""Tests for attune.workflows.dependency_check_audit helpers."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# _get_cache_path
# ---------------------------------------------------------------------------


def test_get_cache_path_returns_path_inside_attune_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "attune.workflows.dependency_check_audit.CACHE_DIR", tmp_path / "advisory_cache"
    )
    from attune.workflows.dependency_check_audit import _get_cache_path

    p = _get_cache_path()
    assert p.name == "pip_audit_cache.json"
    assert p.parent.exists()


# ---------------------------------------------------------------------------
# _load_cached_advisories
# ---------------------------------------------------------------------------


def test_load_cached_advisories_returns_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("attune.workflows.dependency_check_audit.CACHE_DIR", tmp_path / "no_cache")
    from importlib import reload

    import attune.workflows.dependency_check_audit as mod

    reload(mod)
    with patch.object(Path, "exists", return_value=False):
        result = mod._load_cached_advisories()
    assert result == {}


def test_load_cached_advisories_returns_data_from_fresh_file(tmp_path, monkeypatch):
    cache_dir = tmp_path / "advisory_cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "pip_audit_cache.json"
    data = {"requests": [{"id": "CVE-2023-001", "description": "vuln"}]}
    cache_file.write_text(json.dumps(data))

    with (
        patch("attune.workflows.dependency_check_audit._get_cache_path", return_value=cache_file),
        patch.object(Path, "exists", return_value=True),
    ):
        from attune.workflows.dependency_check_audit import _load_cached_advisories

        result = _load_cached_advisories()

    assert result == data


def test_load_cached_advisories_warns_when_cache_old(tmp_path, caplog):
    cache_dir = tmp_path / "advisory_cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "pip_audit_cache.json"
    cache_file.write_text("{}")
    old_mtime = time.time() - (8 * 86400)  # 8 days old

    with (
        patch("attune.workflows.dependency_check_audit._get_cache_path", return_value=cache_file),
        patch.object(Path, "exists", return_value=True),
        patch("time.time", return_value=old_mtime + (8 * 86400)),
    ):
        mock_stat = MagicMock()
        mock_stat.st_mtime = old_mtime
        with patch.object(Path, "stat", return_value=mock_stat):
            import logging

            with caplog.at_level(logging.WARNING):
                from attune.workflows.dependency_check_audit import _load_cached_advisories

                _load_cached_advisories()
    assert any("old" in r.message.lower() or "day" in r.message.lower() for r in caplog.records)


def test_load_cached_advisories_returns_empty_on_bad_json(tmp_path):
    cache_file = tmp_path / "pip_audit_cache.json"
    cache_file.write_text("not valid json {{{")

    with patch("attune.workflows.dependency_check_audit._get_cache_path", return_value=cache_file):
        with patch.object(Path, "exists", return_value=True):
            mock_stat = MagicMock()
            mock_stat.st_mtime = time.time()
            with patch.object(Path, "stat", return_value=mock_stat):
                from attune.workflows.dependency_check_audit import _load_cached_advisories

                result = _load_cached_advisories()
    assert result == {}


# ---------------------------------------------------------------------------
# _save_advisory_cache
# ---------------------------------------------------------------------------


def test_save_advisory_cache_writes_file(tmp_path):
    cache_file = tmp_path / "pip_audit_cache.json"
    advisories = {"somelib": [{"id": "CVE-2023-999"}]}

    with patch("attune.workflows.dependency_check_audit._get_cache_path", return_value=cache_file):
        from attune.workflows.dependency_check_audit import _save_advisory_cache

        _save_advisory_cache(advisories)

    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == advisories


def test_save_advisory_cache_handles_write_error(tmp_path, caplog):
    with (
        patch(
            "attune.workflows.dependency_check_audit._get_cache_path",
            side_effect=OSError("disk full"),
        ),
    ):
        import logging

        with caplog.at_level(logging.WARNING):
            from attune.workflows.dependency_check_audit import _save_advisory_cache

            _save_advisory_cache({})
    assert any("Could not" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _run_pip_audit
# ---------------------------------------------------------------------------


def _make_pip_audit_output(vulns: list[dict]) -> str:
    return json.dumps({"dependencies": vulns})


def test_run_pip_audit_no_requirements_no_pyproject(tmp_path):
    from attune.workflows.dependency_check_audit import _run_pip_audit

    result = _run_pip_audit(tmp_path)
    assert result == []


def test_run_pip_audit_with_requirements_txt(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    vuln_data = [{"name": "requests", "version": "2.28.0", "vulns": [{"id": "CVE-2023-32681"}]}]
    mock_result = MagicMock()
    mock_result.stdout = _make_pip_audit_output(vuln_data)

    with (
        patch("subprocess.run", return_value=mock_result),
        patch("attune.workflows.dependency_check_audit._load_cached_advisories", return_value={}),
        patch("attune.workflows.dependency_check_audit._save_advisory_cache"),
    ):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == vuln_data


def test_run_pip_audit_with_pyproject_toml(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'test'\n")

    mock_result = MagicMock()
    mock_result.stdout = _make_pip_audit_output([])

    with patch("subprocess.run", return_value=mock_result):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == []


def test_run_pip_audit_not_installed(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    with patch("subprocess.run", side_effect=FileNotFoundError("pip-audit not found")):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == []


def test_run_pip_audit_timeout(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pip-audit", 120)):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == []


def test_run_pip_audit_invalid_json(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    mock_result = MagicMock()
    mock_result.stdout = "not json"

    with patch("subprocess.run", return_value=mock_result):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == []


def test_run_pip_audit_generic_exception(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        result = _run_pip_audit(tmp_path)

    assert result == []


def test_run_pip_audit_updates_cache_on_vulns(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")

    vuln_data = [{"name": "requests", "version": "2.28.0", "vulns": [{"id": "CVE-2023-32681"}]}]
    mock_result = MagicMock()
    mock_result.stdout = _make_pip_audit_output(vuln_data)

    saved = {}

    def fake_save(data):
        saved.update(data)

    with (
        patch("subprocess.run", return_value=mock_result),
        patch("attune.workflows.dependency_check_audit._load_cached_advisories", return_value={}),
        patch(
            "attune.workflows.dependency_check_audit._save_advisory_cache", side_effect=fake_save
        ),
    ):
        from attune.workflows.dependency_check_audit import _run_pip_audit

        _run_pip_audit(tmp_path)

    assert "requests" in saved


# ---------------------------------------------------------------------------
# _run_npm_audit
# ---------------------------------------------------------------------------


def _make_npm_audit_output(vulns: dict) -> str:
    return json.dumps({"vulnerabilities": vulns})


def test_run_npm_audit_no_package_json(tmp_path):
    from attune.workflows.dependency_check_audit import _run_npm_audit

    result = _run_npm_audit(tmp_path)
    assert result == []


def test_run_npm_audit_returns_parsed_vulns(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name":"test"}')

    vulns = {
        "lodash": {
            "name": "lodash",
            "severity": "high",
            "via": ["prototype-pollution"],
            "range": "<4.17.21",
            "fixAvailable": True,
        }
    }
    mock_result = MagicMock()
    mock_result.stdout = _make_npm_audit_output(vulns)

    with patch("subprocess.run", return_value=mock_result):
        from attune.workflows.dependency_check_audit import _run_npm_audit

        result = _run_npm_audit(tmp_path)

    assert len(result) == 1
    assert result[0]["name"] == "lodash"
    assert result[0]["severity"] == "high"


def test_run_npm_audit_not_installed(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name":"test"}')

    with patch("subprocess.run", side_effect=FileNotFoundError("npm not found")):
        from attune.workflows.dependency_check_audit import _run_npm_audit

        result = _run_npm_audit(tmp_path)

    assert result == []


def test_run_npm_audit_timeout(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name":"test"}')

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("npm", 120)):
        from attune.workflows.dependency_check_audit import _run_npm_audit

        result = _run_npm_audit(tmp_path)

    assert result == []


def test_run_npm_audit_generic_exception(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name":"test"}')

    with patch("subprocess.run", side_effect=RuntimeError("unexpected npm error")):
        from attune.workflows.dependency_check_audit import _run_npm_audit

        result = _run_npm_audit(tmp_path)

    assert result == []
