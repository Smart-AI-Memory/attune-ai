"""PDF export refuses unsupported Python without limiting normal docs."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import yaml
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def builder(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "pdf_build_control", ROOT / "scripts/build_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "DIST_DIR", tmp_path / "dist")
    return module


def test_pdf_refuses_python_310_before_any_build_output(builder, monkeypatch, capsys):
    monkeypatch.setattr(builder, "sys", SimpleNamespace(version_info=(3, 10)))

    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported PDF export must not start a build")

    monkeypatch.setattr(builder, "run_command", forbidden)
    assert builder.build_ebook() is False
    assert not builder.DIST_DIR.exists()
    output = capsys.readouterr().out
    assert "Python 3.11 or later" in output
    assert "python -m pip install -e '.[docs]'" in output


@pytest.mark.parametrize("version", [(3, 11), (3, 12), (3, 14)])
@pytest.mark.parametrize("success", [True, False])
def test_pdf_supported_python_preserves_build_command(
    builder, monkeypatch, version, success, capsys
):
    monkeypatch.setattr(builder, "sys", SimpleNamespace(version_info=version))
    calls = []

    def run(cmd, env=None):
        calls.append((cmd, env))
        return success

    monkeypatch.setattr(builder, "run_command", run)
    assert builder.build_ebook() is success
    if success:
        assert (
            "Install with Python 3.11+: python -m pip install -e '.[docs]'"
            in capsys.readouterr().out
        )
    output = builder.DIST_DIR / "docs-ebook"
    assert output.is_dir()
    assert calls == [
        (
            ["mkdocs", "build", "-f", "mkdocs-ebook.yml", "-d", str(output)],
            {"ENABLE_PDF_EXPORT": "1"},
        )
    ]


def test_website_remains_available_on_python_310(builder, monkeypatch):
    monkeypatch.setattr(builder, "sys", SimpleNamespace(version_info=(3, 10)))
    calls = []
    monkeypatch.setattr(builder, "run_command", lambda cmd: calls.append(cmd) or True)
    assert builder.build_website() is True
    assert calls == [
        ["mkdocs", "build", "-f", "mkdocs.yml", "-d", str(builder.DIST_DIR / "docs-website")]
    ]


def test_all_on_python_310_builds_web_outputs_but_fails_pdf(builder, monkeypatch):
    monkeypatch.setattr(builder, "sys", SimpleNamespace(version_info=(3, 10)))
    calls = []
    monkeypatch.setattr(builder, "run_command", lambda cmd: calls.append(cmd) or True)
    assert builder.build_all() is False
    assert [call[3] for call in calls] == ["mkdocs-pypi.yml", "mkdocs.yml"]
    assert (builder.DIST_DIR / "docs-pypi").is_dir()
    assert (builder.DIST_DIR / "docs-website").is_dir()
    assert not (builder.DIST_DIR / "docs-ebook").exists()


@pytest.mark.parametrize("extra", ["docs", "all"])
@pytest.mark.parametrize("version", ["3.10", "3.11", "3.12", "3.14"])
def test_metadata_pdf_boundary_and_security_floors(extra, version):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "3.10" in SpecifierSet(project["requires-python"])
    environment = default_environment()
    environment.update(python_version=version, python_full_version=version + ".0", extra=extra)
    active = {
        requirement.name.lower(): requirement
        for value in project["optional-dependencies"][extra]
        if (requirement := Requirement(value)).marker is None
        or requirement.marker.evaluate(environment)
    }
    assert "mkdocs" in active
    if version == "3.10":
        assert "mkdocs-with-pdf" not in active
        assert "pillow" not in active
    else:
        assert "mkdocs-with-pdf" in active
        assert "13.0.0" in active["pillow"].specifier
        assert "12.3.0" not in active["pillow"].specifier
    core = {
        Requirement(value).name.lower(): Requirement(value) for value in project["dependencies"]
    }
    assert "2026.10.18" in core["certifi"].specifier
    assert "2026.6.17" not in core["certifi"].specifier


def test_ebook_javascript_excludes_retired_polyfill_host():
    config = yaml.load(
        (ROOT / "mkdocs-ebook.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    hosts = [urlsplit(value).hostname or "" for value in config["extra_javascript"]]
    assert all(host != "polyfill.io" and not host.endswith(".polyfill.io") for host in hosts)


def test_ebook_pdf_output_matches_builder_destination(builder):
    config = yaml.load(
        (ROOT / "mkdocs-ebook.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    pdf_options = next(
        plugin["with-pdf"]
        for plugin in config["plugins"]
        if isinstance(plugin, dict) and "with-pdf" in plugin
    )
    site_dir = builder.DIST_DIR / "docs-ebook"
    actual_pdf = (site_dir / pdf_options["output_path"]).resolve()
    assert actual_pdf == (builder.DIST_DIR / "empathy-book.pdf").resolve()
