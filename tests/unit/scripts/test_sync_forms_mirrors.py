"""The mirror-sync transform: import-block swap + isort normalization."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sync_forms_mirrors import MIRROR_DIR, MIRRORED_FILES, transform  # noqa: E402


def test_swaps_every_import_form_and_sorts() -> None:
    src = (
        '"""Doc."""\n\n'
        "from attune_forms import form_from_dict\n"
        "from attune_forms.models import QuestionType\n"
        "from attune_forms.widget import _CSS_FAMILIES\n\n"
        "X = 1\n"
    )
    got = transform(src)
    assert "attune_forms" not in got
    assert "from attune.elicitation import form_from_dict" in got
    assert "from attune.meta_workflows.models import QuestionType" in got
    # isort-normalized: elicitation.widget sorts before meta_workflows.
    widget_at = got.index("attune.elicitation.widget")
    models_at = got.index("attune.meta_workflows.models")
    assert widget_at < models_at


def test_mirrored_files_exist_in_the_mirror_dir() -> None:
    for name in MIRRORED_FILES:
        assert (MIRROR_DIR / name).is_file(), name
