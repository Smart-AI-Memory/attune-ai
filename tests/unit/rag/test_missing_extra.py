"""Coverage for the 'attune-rag not installed' error paths.

These tests run regardless of whether the [rag] extra is
installed — they use a sys.modules sentinel to force
attune_rag imports to raise ImportError, then assert that
the workflow and MCP handler both surface a helpful
"reinstall attune-rag" error rather than crashing
(attune-rag is a core dep; the legacy [rag] extra is empty).

Complements tests/integration/rag/test_rag_workflow.py and
tests/unit/rag/test_mcp_tool.py which exercise the happy
paths when attune_rag IS installed.
"""

from __future__ import annotations

import asyncio
import sys


def _block_attune_rag() -> dict[str, object]:
    """Force `import attune_rag` to raise ImportError.

    Uses the `sys.modules[name] = None` sentinel (stable
    across Python 3.10-3.13; the deprecated
    MetaPathFinder/find_module API no longer fires in 3.12+).

    Returns a dict of original modules to restore afterward.
    """
    saved: dict[str, object] = {}
    for key in list(sys.modules):
        if key == "attune_rag" or key.startswith("attune_rag."):
            saved[key] = sys.modules.pop(key)
    sys.modules["attune_rag"] = None  # type: ignore[assignment]
    return saved


def _unblock_attune_rag(saved: dict[str, object]) -> None:
    sys.modules.pop("attune_rag", None)
    sys.modules.update(saved)


def test_workflow_raises_helpful_error_when_attune_rag_missing() -> None:
    """RagCodeGenWorkflow._get_pipeline raises RuntimeError
    naming the attune-rag core dep when it can't import."""
    from attune.workflows.rag_code_gen import RagCodeGenWorkflow

    saved = _block_attune_rag()
    try:
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(query="anything"))
        assert result.success is False
        assert result.error is not None
        assert "attune-rag" in result.error
        assert "pip install attune-rag" in result.error
    finally:
        _unblock_attune_rag(saved)


def test_workflow_empty_query_rejected_without_attune_rag() -> None:
    """Empty-query validation fires before the attune_rag
    import attempt, so it returns the right error even when
    attune_rag is missing."""
    from attune.workflows.rag_code_gen import RagCodeGenWorkflow

    saved = _block_attune_rag()
    try:
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(query=""))
        assert result.success is False
        assert "query" in result.error.lower()
    finally:
        _unblock_attune_rag(saved)


def test_mcp_handler_returns_structured_error_when_attune_rag_missing() -> None:
    """_run_rag_knowledge_query returns a structured dict
    naming the attune-rag core dep when it can't import.
    No exception escapes to the MCP dispatcher."""
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()

    saved = _block_attune_rag()
    try:
        result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit"}))
        assert result["success"] is False
        assert "attune-rag" in result["error"]
        assert "pip install attune-rag" in result["error"]
        assert "cause" in result  # original ImportError message
    finally:
        _unblock_attune_rag(saved)


def _fake_attune_rag_with_failing_pipeline(message: str) -> object:
    """A stand-in attune_rag whose RagPipeline raises at construction."""
    import types

    fake = types.ModuleType("attune_rag")

    class _BoomPipeline:
        def __init__(self) -> None:
            raise RuntimeError(message)

    fake.RagPipeline = _BoomPipeline  # type: ignore[attr-defined]
    return fake


def test_mcp_handler_names_attune_help_package_on_help_corpus_error() -> None:
    """A RuntimeError mentioning attune-help gets the direct-install
    hint appended — the [author] extra that used to ship it was
    retired (author-consolidation T4), so the hint names the package
    itself and the fix is one command."""
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()

    saved = _block_attune_rag()
    sys.modules["attune_rag"] = _fake_attune_rag_with_failing_pipeline(  # type: ignore[assignment]
        "attune-help corpus unavailable"
    )
    try:
        result = asyncio.run(server._run_rag_knowledge_query({"query": "q"}))
        assert result["success"] is False
        assert "RAG setup error" in result["error"]
        assert "pip install attune-help" in result["error"]
        assert "[author]" not in result["error"]
    finally:
        _unblock_attune_rag(saved)


def test_mcp_handler_omits_author_hint_for_unrelated_setup_errors() -> None:
    """RuntimeErrors that don't mention attune-help stay un-hinted."""
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()

    saved = _block_attune_rag()
    sys.modules["attune_rag"] = _fake_attune_rag_with_failing_pipeline(  # type: ignore[assignment]
        "corpus directory is empty"
    )
    try:
        result = asyncio.run(server._run_rag_knowledge_query({"query": "q"}))
        assert result["success"] is False
        assert "RAG setup error" in result["error"]
        assert "[author]" not in result["error"]
    finally:
        _unblock_attune_rag(saved)


def test_mcp_handler_rejects_empty_query_without_attune_rag() -> None:
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()

    saved = _block_attune_rag()
    try:
        result = asyncio.run(server._run_rag_knowledge_query({}))
        assert result["success"] is False
        assert "query" in result["error"].lower()
    finally:
        _unblock_attune_rag(saved)


def test_mcp_handler_rejects_invalid_k_without_attune_rag() -> None:
    """k-bounds validation runs before the attune_rag import,
    so it still functions when the extra is missing."""
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()

    saved = _block_attune_rag()
    try:
        result = asyncio.run(server._run_rag_knowledge_query({"query": "q", "k": 0}))
        assert result["success"] is False
        assert "between 1 and 10" in result["error"]

        result = asyncio.run(server._run_rag_knowledge_query({"query": "q", "k": "bogus"}))
        assert result["success"] is False
        assert "integer" in result["error"]
    finally:
        _unblock_attune_rag(saved)


def test_workflow_class_has_expected_attributes() -> None:
    """Class-level attrs load even without attune_rag (module
    import doesn't touch attune_rag)."""
    from attune.workflows.rag_code_gen import RagCodeGenWorkflow

    assert RagCodeGenWorkflow.name == "rag-code-gen"
    assert "retrieve" in RagCodeGenWorkflow.stages
    assert "generate" in RagCodeGenWorkflow.stages
    assert RagCodeGenWorkflow.description


def test_workflow_registered_in_default_map() -> None:
    """The workflow class is importable and registered in
    _DEFAULT_WORKFLOW_NAMES regardless of attune_rag install
    state. Catches registry drift."""
    from attune.workflows import _DEFAULT_WORKFLOW_NAMES

    assert "rag-code-gen" in _DEFAULT_WORKFLOW_NAMES
    assert _DEFAULT_WORKFLOW_NAMES["rag-code-gen"] == "RagCodeGenWorkflow"


def test_mcp_tool_schema_registered_without_attune_rag() -> None:
    """The rag_knowledge_query schema is always registered;
    only the handler lazy-imports attune_rag."""
    from attune.mcp.server import AttuneMCPServer

    server = AttuneMCPServer()
    saved = _block_attune_rag()
    try:
        tool_names = {t["name"] for t in server.get_tool_list()}
        assert "rag_knowledge_query" in tool_names
    finally:
        _unblock_attune_rag(saved)
