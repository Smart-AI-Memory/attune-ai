"""Guard: no NEW ``patch.dict("sys.modules", ...)`` in the test suite.

``patch.dict("sys.modules", {...})`` is convenient for mocking an import,
but its teardown does ``sys.modules.clear()`` followed by a rebuild from a
snapshot — a non-atomic global clear+rebuild. Under xdist, a background
thread or a GC finalizer touching ``sys.modules`` during that window races
and surfaces as a transient ``KeyError: <object-id>`` (the signature of a
concurrent dict mutation). This bit ``test_real_tools.py`` on CI; see the
fix in that file and the ``.claude/lessons.md`` entry.

Safer alternatives (both surgical — they restore only the touched key):

- Installed package, one symbol → ``patch("pkg.Attr", mock)``.
- Fake or absent whole module → the ``fake_module`` fixture in
  ``tests/conftest.py`` (wraps ``monkeypatch.setitem(sys.modules, ...)``).

This guard does NOT force the existing 219 sites to be converted — it
freezes them as a per-file baseline so the debt cannot GROW. As files are
converted (opportunistically, when they flake), ratchet their entry DOWN
(or delete it). A new/raised usage anywhere fails this test.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "tests"

# Matches ``patch.dict("sys.modules"`` / ``patch.dict('sys.modules'`` with
# any whitespace (including newlines) after the opening paren.
_PATTERN = re.compile(r"""patch\.dict\(\s*["']sys\.modules["']""")

# Per-file frozen baseline (relative to tests/). Ratchet DOWN as files are
# converted; never add an entry. Captured 2026-06-22.
_BASELINE: dict[str, int] = {
    "agent_factory/test_llm_toolkit_langgraph_adapter.py": 4,
    "agent_factory/test_native_adapter.py": 2,
    "llm/test_anthropic_cache_ttl.py": 6,
    "llm/test_anthropic_provider_coverage.py": 9,
    "llm/test_llm_toolkit_providers.py": 1,
    "llm/test_providers.py": 17,
    "memory/test_claude_memory.py": 1,
    "models/test_token_estimator.py": 1,
    "unit/agent_factory/test_langgraph_adapter.py": 8,
    "unit/cli_commands/test_provider_commands.py": 33,
    "unit/cli_commands/test_telemetry_commands.py": 19,
    "unit/cli_commands/test_utility_commands.py": 24,
    "unit/help/test_polish.py": 4,
    "unit/help/test_usage_weights.py": 7,
    "unit/hooks/test_help_hooks.py": 1,
    "unit/mcp/handlers/test_telemetry_handlers.py": 2,
    "unit/mcp/test_version_check.py": 5,
    "unit/memory/test_control_panel_display.py": 3,
    "unit/meta_workflows/test_llm_execution.py": 3,
    "unit/meta_workflows/test_plan_generator.py": 1,
    "unit/models/test_empathy_executor_new.py": 6,
    "unit/orchestration/test_tools_test_generation.py": 4,
    "unit/routing/test_classifier.py": 1,
    "unit/telemetry/test_cli_automation.py": 1,
    "unit/test_batch_provider.py": 3,
    "unit/test_coverage_batch1.py": 2,
    "unit/test_coverage_batch10.py": 1,
    "unit/test_coverage_batch17.py": 2,
    "unit/test_coverage_batch9.py": 2,
    "unit/test_event_streaming.py": 3,
    "unit/test_main_entries.py": 9,
    "unit/wizards/test_builtin_refactor_wizard.py": 1,
    "unit/wizards/test_builtin_security_wizard.py": 1,
    "unit/wizards/test_wizard_coverage_boost.py": 2,
    "unit/workflows/test_coordination_mixin_coverage.py": 3,
    "unit/workflows/test_document_gen_outline_stage.py": 1,
    "unit/workflows/test_execution_mixin_branches.py": 1,
    "unit/workflows/test_workflow_coordination.py": 6,
    "unit/workflows/test_workflow_services.py": 3,
}

_HINT = (
    "Use the `fake_module` fixture (tests/conftest.py) for a fake/absent "
    "module, or `patch('pkg.Attr', mock)` for an installed package. "
    'patch.dict("sys.modules", ...) clears+rebuilds all of sys.modules on '
    "teardown and races under xdist (KeyError: <id>)."
)


# Files that legitimately contain the literal pattern in prose/regex (this
# guard documents it; conftest documents the safe alternative) — never code.
_SELF_EXCLUDE: frozenset[str] = frozenset(
    {
        "unit/ci/test_no_new_sys_modules_patch.py",
    }
)


def _current_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in TESTS_DIR.rglob("*.py"):
        rel = path.relative_to(TESTS_DIR).as_posix()
        if rel in _SELF_EXCLUDE:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        n = len(_PATTERN.findall(text))
        if n:
            counts[rel] = n
    return counts


def test_no_new_sys_modules_patch_dict():
    """Fail if any test file introduces or increases sys.modules patching."""
    current = _current_counts()

    new_files = sorted(set(current) - set(_BASELINE))
    assert not new_files, (
        'New file(s) use patch.dict("sys.modules", ...):\n  '
        + "\n  ".join(new_files)
        + f"\n\n{_HINT}"
    )

    grew = sorted(
        f"{f}: {current[f]} > baseline {_BASELINE[f]}"
        for f in current
        if f in _BASELINE and current[f] > _BASELINE[f]
    )
    assert not grew, (
        'patch.dict("sys.modules", ...) usage increased:\n  ' + "\n  ".join(grew) + f"\n\n{_HINT}"
    )


def test_sys_modules_patch_baseline_is_not_stale():
    """If a baseline file was converted, ratchet its entry DOWN.

    Keeps the baseline honest: an entry whose real count dropped (or which
    no longer matches) must be lowered/removed so the guard stays tight.
    """
    current = _current_counts()
    stale = sorted(
        f"{f}: baseline {count} but now {current.get(f, 0)} — lower it"
        for f, count in _BASELINE.items()
        if current.get(f, 0) < count
    )
    assert (
        not stale
    ), "Baseline is looser than reality; ratchet these DOWN in " "_BASELINE:\n  " + "\n  ".join(
        stale
    )
