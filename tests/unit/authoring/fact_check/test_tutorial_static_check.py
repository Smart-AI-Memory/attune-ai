"""Tests for the Phase 4 tutorial code-fence static check."""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

from attune.authoring.fact_check.tutorial_static_check import (
    CHECK_TUTORIAL_STATIC,
    check,
    is_tutorial_path,
    strip_skip_directives_in_file,
)

# ---------------------------------------------------------------------------
# is_tutorial_path
# ---------------------------------------------------------------------------


def test_is_tutorial_path_true_for_tutorials_dir() -> None:
    assert is_tutorial_path(Path("docs/tutorials/ops.md")) is True


def test_is_tutorial_path_false_for_other_kinds() -> None:
    assert is_tutorial_path(Path("docs/how-to/ops.md")) is False
    assert is_tutorial_path(Path("docs/architecture/ops.md")) is False
    assert is_tutorial_path(Path("README.md")) is False


# ---------------------------------------------------------------------------
# strip_skip_directives_in_file
# ---------------------------------------------------------------------------


def test_strip_skip_directive_first_line() -> None:
    src = dedent(
        """\
        Prose.

        ```python
        # attune-author: skip-mypy
        do_thing()
        ```

        More prose.
        """
    )
    out = strip_skip_directives_in_file(src)
    assert "# attune-author: skip-mypy" not in out
    assert "do_thing()" in out


def test_strip_skip_directive_only_strips_when_first_line() -> None:
    """A trailing directive in a later position is NOT stripped."""
    src = dedent(
        """\
        ```python
        thing()
        # attune-author: skip-mypy
        ```
        """
    )
    out = strip_skip_directives_in_file(src)
    assert "# attune-author: skip-mypy" in out


def test_strip_skip_directive_no_op_when_absent() -> None:
    src = "```python\nprint('hi')\n```\n"
    assert strip_skip_directives_in_file(src) == src


# ---------------------------------------------------------------------------
# check — syntax-error path
# ---------------------------------------------------------------------------


def test_check_flags_syntax_error_in_fence(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        dedent(
            """\
            Body text.

            ```python
            def broken(
            ```
            """
        ),
        encoding="utf-8",
    )

    # Patch mypy out so the syntax-error branch is the only thing exercised.
    with patch("attune.authoring.fact_check.tutorial_static_check._run_mypy", return_value=[]):
        findings = check(p)

    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert "SyntaxError" in findings[0].message
    assert findings[0].check == CHECK_TUTORIAL_STATIC


def test_check_clean_when_no_python_fences(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/empty.md"
    p.parent.mkdir(parents=True)
    p.write_text("# Just prose.\n", encoding="utf-8")

    assert check(p) == []


def test_check_unreadable_file_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "missing.md"
    assert check(p) == []


# ---------------------------------------------------------------------------
# check — mypy path (subprocess mocked)
# ---------------------------------------------------------------------------


def _completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["mypy"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_check_calls_mypy_for_valid_fence(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        dedent(
            """\
            Intro.

            ```python
            x: int = "wrong type"
            ```
            """
        ),
        encoding="utf-8",
    )
    mypy_output = "/tmp/x.py:1: error: Incompatible types in assignment  [assignment]\n"
    with patch(
        "attune.authoring.fact_check.tutorial_static_check.subprocess.run",
        return_value=_completed(1, mypy_output),
    ):
        findings = check(p)

    assert len(findings) == 1
    assert findings[0].check == CHECK_TUTORIAL_STATIC
    assert findings[0].severity == "error"
    assert "Incompatible types" in findings[0].message
    # mypy reported "line 1" inside the fence, fence body starts on line 4
    # of the markdown (intro + blank + ``` ).
    assert "Line 4" in findings[0].location


def test_check_skips_fence_with_directive(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        dedent(
            """\
            ```python
            # attune-author: skip-mypy
            illustrative_pseudocode()
            ```
            """
        ),
        encoding="utf-8",
    )

    with patch("attune.authoring.fact_check.tutorial_static_check.subprocess.run") as mock_run:
        findings = check(p)

    assert findings == []
    mock_run.assert_not_called()


def test_check_handles_mypy_missing(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text("```python\nx = 1\n```\n", encoding="utf-8")
    with patch(
        "attune.authoring.fact_check.tutorial_static_check.subprocess.run",
        side_effect=FileNotFoundError("mypy not installed"),
    ):
        findings = check(p)
    assert findings == []


def test_check_handles_mypy_timeout(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text("```python\nx = 1\n```\n", encoding="utf-8")
    with patch(
        "attune.authoring.fact_check.tutorial_static_check.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["mypy"], timeout=10),
    ):
        findings = check(p)
    assert findings == []


def test_check_handles_unexpected_mypy_exit(tmp_path: Path) -> None:
    """mypy exit codes other than 0/1 should drop findings silently."""
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text("```python\nx = 1\n```\n", encoding="utf-8")
    with patch(
        "attune.authoring.fact_check.tutorial_static_check.subprocess.run",
        return_value=_completed(2, stderr="usage error"),
    ):
        findings = check(p)
    assert findings == []


def test_check_clean_when_mypy_returns_zero(tmp_path: Path) -> None:
    p = tmp_path / "docs/tutorials/feat.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        dedent(
            """\
            ```python
            x: int = 1
            ```
            """
        ),
        encoding="utf-8",
    )
    with patch(
        "attune.authoring.fact_check.tutorial_static_check.subprocess.run",
        return_value=_completed(0),
    ):
        findings = check(p)
    assert findings == []


# ---------------------------------------------------------------------------
# Integration: check_polished_file routes to the static check only for
# tutorial paths
# ---------------------------------------------------------------------------


def test_check_polished_file_routes_to_tutorial_static_only_for_tutorials(
    tmp_path: Path,
) -> None:
    from attune.authoring.fact_check import FactCheckConfig, check_polished_file

    tutorial = tmp_path / "docs/tutorials/feat.md"
    tutorial.parent.mkdir(parents=True)
    tutorial.write_text("```python\ndef broken(\n```\n", encoding="utf-8")

    how_to = tmp_path / "docs/how-to/feat.md"
    how_to.parent.mkdir(parents=True)
    how_to.write_text("```python\ndef broken(\n```\n", encoding="utf-8")

    cfg = FactCheckConfig(
        enabled=True,
        check_python_refs=False,
        check_cli_refs=False,
        check_md_links=False,
        check_numeric_refs=False,
        check_doc_examples=False,
        check_tutorial_static=True,
    )

    with patch("attune.authoring.fact_check.tutorial_static_check._run_mypy", return_value=[]):
        tutorial_report = check_polished_file(tutorial, project_root=tmp_path, config=cfg)
        how_to_report = check_polished_file(how_to, project_root=tmp_path, config=cfg)

    assert len(tutorial_report.findings) == 1
    assert tutorial_report.findings[0].check == CHECK_TUTORIAL_STATIC
    assert how_to_report.findings == []


def test_check_polished_file_disabled_when_toggle_off(tmp_path: Path) -> None:
    from attune.authoring.fact_check import FactCheckConfig, check_polished_file

    tutorial = tmp_path / "docs/tutorials/feat.md"
    tutorial.parent.mkdir(parents=True)
    tutorial.write_text("```python\ndef broken(\n```\n", encoding="utf-8")

    cfg = FactCheckConfig(
        enabled=True,
        check_python_refs=False,
        check_cli_refs=False,
        check_md_links=False,
        check_numeric_refs=False,
        check_doc_examples=False,
        check_tutorial_static=False,
    )

    report = check_polished_file(tutorial, project_root=tmp_path, config=cfg)
    assert report.findings == []
