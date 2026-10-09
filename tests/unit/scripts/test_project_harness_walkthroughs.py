"""Editorial comments must not become visible walkthrough instructions."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "website/scripts/project-harness-walkthroughs.py"
SPEC = importlib.util.spec_from_file_location("harness_walkthrough_projector", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PROJECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROJECTOR)


@pytest.mark.parametrize(
    "comment",
    ["<!-- Hidden editorial instruction. -->", "<!--\nHidden editorial instruction.\n-->"],
)
def test_editorial_comments_do_not_change_visible_walkthroughs(comment: str) -> None:
    """Single-line and multiline notes leave every canonical projection unchanged."""
    source = PROJECTOR.SNAPSHOT.read_text(encoding="utf-8")
    annotated = source.replace("Title:", f"{comment}\nTitle:")
    assert annotated != source
    assert PROJECTOR.project(annotated) == PROJECTOR.project(source)


def test_projection_cli_checks_utf8_source_with_utf8_mode_disabled() -> None:
    """Check the actual CLI without relying on the process's default encoding."""
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0", "LC_ALL": "C"})
    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", str(SCRIPT), "--check"],
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
