"""Behavioral tests for backend/api/analysis.py.

Tests the Pydantic request models and their validators.
Imports the module under a stub ``api`` package (bypassing the real
api/__init__.py) to avoid pulling in bcrypt, email-validator, and
other heavy backend deps. All sys.modules edits are reverted after
the load so other tests in the same worker see a clean module table.
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

# Add backend/ to sys.path so the module can be imported
_backend_dir = str(Path(__file__).resolve().parents[3] / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Stub parent packages: a fake "api" package with the real search path
# (so ``from .deps import ...`` resolves) and a mocked services package
# (so analysis.py's EmpathyService import stays lightweight).
_api_pkg = types.ModuleType("api")
_api_pkg.__path__ = [str(Path(_backend_dir) / "api")]
_STUBS = {
    "api": _api_pkg,
    "services": MagicMock(),
    "services.empathy_service": MagicMock(),
}
_saved = {name: sys.modules.get(name) for name in _STUBS}
_saved["api.deps"] = sys.modules.get("api.deps")
_saved["api.analysis"] = sys.modules.get("api.analysis")
sys.modules.update(_STUBS)
try:
    _mod = importlib.import_module("api.analysis")
finally:
    for _name, _val in _saved.items():
        if _val is None:
            sys.modules.pop(_name, None)
        else:
            sys.modules[_name] = _val

ProjectAnalysisRequest = _mod.ProjectAnalysisRequest
SessionConfig = _mod.SessionConfig


# ---------------------------------------------------------------------------
# ProjectAnalysisRequest — validate_project_path
# ---------------------------------------------------------------------------


class TestProjectAnalysisRequest:
    """Test ProjectAnalysisRequest model validation."""

    def test_valid_path_accepted(self):
        """Given a valid project path, model is created successfully."""
        req = ProjectAnalysisRequest(project_path="/home/user/project")
        assert req.project_path == "/home/user/project"

    def test_empty_path_rejected(self):
        """Given an empty string, validation raises ValueError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ProjectAnalysisRequest(project_path="")

    def test_whitespace_only_path_rejected(self):
        """Given whitespace-only string, validation raises ValueError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ProjectAnalysisRequest(project_path="   ")

    def test_path_exceeds_max_length_rejected(self):
        """Given a path longer than 1024 chars, validation fails."""
        long_path = "a" * 1025
        with pytest.raises(ValidationError, match="exceeds maximum"):
            ProjectAnalysisRequest(project_path=long_path)

    def test_path_at_max_length_accepted(self):
        """Given a path of exactly 1024 chars, validation passes."""
        path = "a" * 1024
        req = ProjectAnalysisRequest(project_path=path)
        assert len(req.project_path) == 1024

    def test_optional_fields_default_to_none(self):
        """Given only project_path, optional fields are None."""
        req = ProjectAnalysisRequest(project_path="/tmp/proj")
        assert req.file_patterns is None
        assert req.exclude_patterns is None
        assert req.wizards is None

    def test_file_patterns_accepted(self):
        """Given file_patterns, they are stored correctly."""
        req = ProjectAnalysisRequest(
            project_path="/proj",
            file_patterns=["*.py", "*.ts"],
        )
        assert req.file_patterns == ["*.py", "*.ts"]


# ---------------------------------------------------------------------------
# SessionConfig — validate_name / validate_wizards
# ---------------------------------------------------------------------------


class TestSessionConfig:
    """Test SessionConfig model validation."""

    def test_valid_session_config(self):
        """Given valid name and wizards, model is created."""
        config = SessionConfig(
            name="my-session",
            wizards=["security-audit"],
        )
        assert config.name == "my-session"
        assert config.wizards == ["security-audit"]

    def test_empty_name_rejected(self):
        """Given an empty name, validation raises ValueError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            SessionConfig(name="", wizards=["w1"])

    def test_whitespace_name_rejected(self):
        """Given whitespace-only name, validation raises ValueError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            SessionConfig(name="   ", wizards=["w1"])

    def test_name_exceeds_max_length_rejected(self):
        """Given a name longer than 255 chars, validation fails."""
        long_name = "x" * 256
        with pytest.raises(ValidationError, match="exceeds maximum"):
            SessionConfig(name=long_name, wizards=["w1"])

    def test_name_at_max_length_accepted(self):
        """Given a name of exactly 255 chars, validation passes."""
        name = "x" * 255
        config = SessionConfig(name=name, wizards=["w1"])
        assert len(config.name) == 255

    def test_empty_wizards_rejected(self):
        """Given an empty wizards list, validation fails."""
        with pytest.raises(
            ValidationError,
            match="At least one wizard",
        ):
            SessionConfig(name="test", wizards=[])

    def test_too_many_wizards_rejected(self):
        """Given more than 20 wizards, validation fails."""
        wizards = [f"wiz-{i}" for i in range(21)]
        with pytest.raises(
            ValidationError,
            match="Maximum 20 wizards",
        ):
            SessionConfig(name="test", wizards=wizards)

    def test_max_wizards_accepted(self):
        """Given exactly 20 wizards, validation passes."""
        wizards = [f"wiz-{i}" for i in range(20)]
        config = SessionConfig(name="test", wizards=wizards)
        assert len(config.wizards) == 20

    def test_description_optional(self):
        """Given no description, it defaults to None."""
        config = SessionConfig(name="test", wizards=["w1"])
        assert config.description is None

    def test_config_defaults_to_empty_dict(self):
        """Given no config, it defaults to empty dict."""
        config = SessionConfig(name="test", wizards=["w1"])
        assert config.config == {}

    def test_config_with_extra_data(self):
        """Given config dict, it is stored correctly."""
        config = SessionConfig(
            name="test",
            wizards=["w1"],
            config={"timeout": 30, "verbose": True},
        )
        assert config.config["timeout"] == 30
        assert config.config["verbose"] is True
