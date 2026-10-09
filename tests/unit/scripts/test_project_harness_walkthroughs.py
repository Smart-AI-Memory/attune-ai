"""Editorial comments must not become visible walkthrough instructions."""

import importlib.util
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
    source = PROJECTOR.SNAPSHOT.read_text()
    annotated = source.replace("Title:", f"{comment}\nTitle:")
    assert annotated != source
    assert PROJECTOR.project(annotated) == PROJECTOR.project(source)
