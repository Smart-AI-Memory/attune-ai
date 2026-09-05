"""Import-weight guard: ``import attune.config`` must never load ``attune_rag``.

``attune.config`` imports ``attune.model_tiers``, which is a LAZY
re-export of ``attune_rag.model_tiers`` (PEP 562 ``__getattr__`` plus
thin wrappers that import on first call). The point of the laziness is
that ``attune_rag/__init__`` eagerly loads the pipeline, corpus, and
providers (~350 modules), and ``attune.config`` is on every CLI and hook
startup path. #2406 established the premise; this test turns it into a
gate so a future "simplification" back to an eager import fails CI
instead of silently taxing every startup.

Each probe runs in a subprocess so the assertion sees a fresh
``sys.modules`` — in-process, the suite has long since imported
attune_rag through heavier paths, which would make the check vacuous.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap

_PROBE = """
import importlib.util, json, sys
import {module}
print(json.dumps({{
    "rag_loaded": any(m == "attune_rag" or m.startswith("attune_rag.") for m in sys.modules),
    "rag_available": importlib.util.find_spec("attune_rag") is not None,
    "model_tiers_loaded": "attune.model_tiers" in sys.modules,
}}))
"""


def _probe(module: str) -> dict[str, bool]:
    code = textwrap.dedent(_PROBE).format(module=module)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_import_attune_config_does_not_load_attune_rag() -> None:
    """The headline guard: config import stays clear of the rag package init."""
    facts = _probe("attune.config")
    # Positive control — attune-rag is a core dependency, so an absent
    # package would make the guard vacuous rather than passing.
    assert facts["rag_available"], "attune_rag not installed; guard would be vacuous"
    assert facts["model_tiers_loaded"], "attune.config should still import attune.model_tiers"
    assert not facts["rag_loaded"], (
        "import attune.config pulled in attune_rag — the attune.model_tiers "
        "re-export must stay lazy (see its module docstring)"
    )


def test_import_model_tiers_alone_does_not_load_attune_rag() -> None:
    """The re-export module itself is import-free until a name is used."""
    facts = _probe("attune.model_tiers")
    assert facts["rag_available"]
    assert not facts["rag_loaded"]


def test_resolve_model_call_is_what_pays_for_attune_rag() -> None:
    """Sanity check on the laziness boundary: the first USE loads the package.

    Without this, the two guards above could pass because attune_rag is
    unreachable for some unrelated reason (broken install) rather than
    because the re-export is lazy.
    """
    code = textwrap.dedent(
        """
        import json, sys
        from attune.model_tiers import resolve_model
        before = "attune_rag" in sys.modules
        resolve_model("cheap")
        after = "attune_rag" in sys.modules
        print(json.dumps({"before": before, "after": after}))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout.strip().splitlines()[-1])
    assert facts == {"before": False, "after": True}
