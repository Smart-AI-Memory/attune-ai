"""Regression guards for scripts/check_platform_compat.py's scan rules.

The checker gates `platform-compat`, a required check. Its first baseline
froze 22 "accepted warnings" of which 18 were false positives in three
classes — prose (comments/docstrings) matched as code, and portable
`~/…` + `expanduser()` literals matched as hardcoded paths. A ratchet
whose baseline is noise trains people to ignore it, so each class gets a
test that fails if the false positive returns, paired with a test that
the corresponding TRUE positive still fires.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def checker():
    """Load scripts/check_platform_compat.py as a module."""
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "check_platform_compat.py"
    spec = importlib.util.spec_from_file_location("_check_platform_compat", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_platform_compat"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("_check_platform_compat", None)


def scan_source(checker, tmp_path: Path, source: str):
    """Scan ``source`` as a file and return the ScanResult."""
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    result = checker.ScanResult()
    checker.scan_file(target, result)
    return result


def messages(result, severity: str) -> list[str]:
    return [i.message for i in result.issues if i.severity == severity]


# --- Class 1: prose is not code -------------------------------------


def test_comment_mentioning_unix_path_is_not_a_warning(checker, tmp_path: Path) -> None:
    """A comment EXPLAINING a path bug is not the bug."""
    result = scan_source(
        checker,
        tmp_path,
        '# On Windows, Path("/etc/passwd").is_absolute() is False.\nX = 1\n',
    )
    assert messages(result, "warning") == []


def test_docstring_example_is_not_a_warning(checker, tmp_path: Path) -> None:
    """A docstring usage example is documentation, not a hardcoded path."""
    result = scan_source(
        checker,
        tmp_path,
        'def f():\n    """Configure it.\n\n    >>> f(log_dir="/var/log/empathy")\n    """\n',
    )
    assert messages(result, "warning") == []


def test_trailing_comment_does_not_mask_real_code(checker, tmp_path: Path) -> None:
    """Blanking a trailing comment must leave the code on that line scanned."""
    result = scan_source(checker, tmp_path, 'P = "/tmp/real"  # a comment about /etc/\n')
    assert messages(result, "warning") == ["Hardcoded /tmp path"]


def test_real_hardcoded_path_still_warns(checker, tmp_path: Path) -> None:
    """The rule is narrowed, not neutered."""
    result = scan_source(checker, tmp_path, 'LOG = Path("/var/log/attune")\n')
    assert messages(result, "warning") == ["Hardcoded /var/log path"]


# --- Class 2: `~/` is portable when expanded ------------------------


def test_expanded_tilde_is_not_a_warning(checker, tmp_path: Path) -> None:
    """`Path("~/x").expanduser()` is the portable idiom, Windows included."""
    result = scan_source(
        checker,
        tmp_path,
        'F = Path("~/.attune/session.json").expanduser()\n',
    )
    assert messages(result, "warning") == []


def test_tilde_config_default_is_not_a_warning(checker, tmp_path: Path) -> None:
    """A bare `~/…` default is expanded at consumption, not here."""
    result = scan_source(checker, tmp_path, 'memory_path: str = "~/.attune/memory"\n')
    assert messages(result, "warning") == []


def test_unexpanded_tilde_in_filesystem_call_warns(checker, tmp_path: Path) -> None:
    """The true positive: `~` handed to a filesystem call fails everywhere."""
    result = scan_source(checker, tmp_path, 'data = open("~/.attune/x", "r").read()\n')
    assert "Unexpanded '~' passed to a filesystem call" in messages(result, "warning")


# --- The encoding gate must survive the masking ---------------------


def test_open_without_encoding_still_errors(checker, tmp_path: Path) -> None:
    """Masking prose must not blank real code and hide the error gate."""
    result = scan_source(checker, tmp_path, 'with open(p, "w") as fh:\n    fh.write("x")\n')
    assert messages(result, "error") == ["open() without encoding specified"]


def test_open_inside_docstring_is_not_an_error(checker, tmp_path: Path) -> None:
    """An `open()` in a usage example is prose."""
    result = scan_source(
        checker,
        tmp_path,
        'def f():\n    """Read it.\n\n    >>> open(p, "r")\n    """\n',
    )
    assert messages(result, "error") == []


def test_unparseable_file_falls_back_to_raw_lines(checker, tmp_path: Path) -> None:
    """A syntax error must not silently disable scanning of the file."""
    result = scan_source(checker, tmp_path, 'def broken(\nP = "/tmp/x"\n')
    assert messages(result, "warning") == ["Hardcoded /tmp path"]
