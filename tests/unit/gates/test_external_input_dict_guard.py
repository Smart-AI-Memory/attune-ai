"""C3 group A: external bytes must be dict-guarded before a ``.get``.

Library-review class C3 is "a parsed non-dict reaches a ``.get``/``[]``
chain". The reachability triage
(``~/.attune/reports/attune-ai-review/C3-triage-2026-08-20.md``) cut 60
sweep hits to the 7 where the parsed bytes are genuinely **external** —
LLM output, external-tool stdout, ecosystem manifests, user-authored
config — and where nothing catches the resulting exception.

Each test drives the site's own entry point with a valid-JSON/YAML
payload of the wrong top-level type and asserts the site's OWN declared
behaviour, which differs per site by design:

- degrade quietly (evaluator, security agent, npm parsers)
- raise the DOCUMENTED ``ValueError`` (coverage parser, workflow config)

A uniform assertion here would have been wrong; the point of the triage
was that these contracts are not the same.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0

Register-Class: C3
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

NON_OBJECT_JSON = ["[1,2,3]", '"a string"', "42", "null"]


# ---------------------------------------------------------------------------
# Degrade-quietly contracts
# ---------------------------------------------------------------------------


def test_evaluator_does_not_block_the_chain_on_a_non_object_answer() -> None:
    """The highest-value site: the LLM answer is untrusted by definition.

    ``result.get("passed")`` sits OUTSIDE the try that wraps the parse,
    so before the fix a JSON array from the evaluator raised
    ``AttributeError`` past a handler whose own comment says
    "Don't block on evaluator failure".
    """
    from attune.workflows.escalation.evaluator import SemanticEvaluator

    evaluator = SemanticEvaluator.__new__(SemanticEvaluator)
    evaluator.evaluator_model = "test-model"
    evaluator.max_tokens = 16

    class _Executor:
        async def run(self, **_kwargs):
            return SimpleNamespace(content="[1, 2, 3]")

    evaluator._get_executor = lambda: _Executor()

    params = list(inspect.signature(SemanticEvaluator.evaluate).parameters)[1:]
    passed, feedback = asyncio.run(
        SemanticEvaluator.evaluate(evaluator, **dict.fromkeys(params, "x"))
    )

    assert passed is True
    assert feedback is None


@pytest.mark.parametrize("payload", NON_OBJECT_JSON)
def test_bandit_output_that_is_not_an_object_degrades(payload: str) -> None:
    """An external tool emitting an array takes the unparseable path."""
    from attune.agents.release import security_agent as module

    agent_cls = next(
        value
        for value in vars(module).values()
        if isinstance(value, type) and hasattr(value, "_parse_bandit_output")
    )
    result = agent_cls.__new__(agent_cls)._parse_bandit_output(payload, 1)

    assert result["note"] == "Could not parse bandit output"


@pytest.mark.parametrize("payload", NON_OBJECT_JSON)
def test_npm_manifests_that_are_not_objects_yield_no_deps(payload: str, tmp_path: Path) -> None:
    """package.json / package-lock.json come from another ecosystem."""
    from attune.workflows import dependency_check_parsers as module

    parser_cls = next(
        value
        for value in vars(module).values()
        if isinstance(value, type) and hasattr(value, "_parse_package_json")
    )
    parser = parser_cls.__new__(parser_cls)

    manifest = tmp_path / "package.json"
    manifest.write_text(payload, encoding="utf-8")
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text(payload, encoding="utf-8")

    assert parser._parse_package_json(manifest) == []
    assert parser._parse_package_lock_json(lockfile) == []


def test_scalar_bug_predict_config_is_ignored(tmp_path: Path, monkeypatch) -> None:
    """`"key" in config` raises TypeError on a scalar, so guard the type."""
    from attune.workflows.bug_predict_patterns import _load_bug_predict_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / "attune.config.yml").write_text("42\n", encoding="utf-8")

    # Falls back to defaults rather than raising TypeError.
    assert isinstance(_load_bug_predict_config(), dict)


# ---------------------------------------------------------------------------
# Documented-ValueError contracts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", NON_OBJECT_JSON)
def test_coverage_json_that_is_not_an_object_raises_value_error(
    payload: str, tmp_path: Path
) -> None:
    """The docstring promises ValueError for invalid coverage JSON."""
    from attune.workflows.test_audit.coverage_parser import parse_coverage_json

    path = tmp_path / "coverage.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError):
        parse_coverage_json(str(path))


def test_non_mapping_workflow_config_raises_value_error(tmp_path: Path) -> None:
    """Matches the YAML branch, which already reports ValueError."""
    from attune.workflows.config import WorkflowConfig

    config = tmp_path / "attune.config.yaml"
    config.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ValueError):
        WorkflowConfig._load_file(config)
