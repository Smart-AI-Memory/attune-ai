"""Tests for the rich-rendering parsing in `runner.js`.

The JS itself is tested by-eye in the browser. These tests guard
against drift between the JS regex/lists and what the Python side
expects:

- Every canonical workflow name from `attune.ops.data.list_workflows()`
  must appear in the JS `WORKFLOW_NAMES` array. Otherwise a workflow
  mentioned in another workflow's output wouldn't render as a pill.
- The JS file should parse cleanly (no obvious syntax errors).
- Representative log-line patterns we expect to render correctly:
  match the same Python-equivalent regex (so the logic is sanity-checked
  outside the browser).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_RUNNER_JS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js" / "runner.js"
)


@pytest.fixture(scope="module")
def runner_js_text() -> str:
    return _RUNNER_JS.read_text(encoding="utf-8")


def test_runner_js_exists():
    """The file is checked in and reachable."""
    assert _RUNNER_JS.is_file(), f"missing {_RUNNER_JS}"


def test_workflow_names_array_is_generated_and_in_sync():
    """runner.js WORKFLOW_NAMES must equal a fresh generation from
    `attune.ops.data.list_workflows()`.

    The array is a GENERATED artifact (drift-guards-to-generators
    Conversion 2): `scripts/sync_runner_workflow_names.py` writes it from
    the canonical list. This inverts the old drift guard — instead of
    asserting "no canonical name is missing" and leaving a human to
    hand-edit, it asserts the whole artifact matches what the generator
    would produce and the failure message names the command to run.
    """
    pytest.importorskip("fastapi")  # generator imports attune.ops.data
    import importlib.util

    script = Path(__file__).resolve().parents[3] / "scripts" / "sync_runner_workflow_names.py"
    spec = importlib.util.spec_from_file_location("_sync_runner_wf", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rc = mod.apply(_RUNNER_JS, check=True)
    assert rc == 0, (
        "runner.js WORKFLOW_NAMES is out of sync with "
        "attune.ops.data.list_workflows(). "
        "Run: python scripts/sync_runner_workflow_names.py"
    )


def test_section_headers_includes_recommendations(runner_js_text):
    """Common workflow-output headers must be recognized."""
    must_have = ["Recommendations", "Next steps", "Issues", "Summary"]
    m = re.search(r"SECTION_HEADERS\s*=\s*\[(.*?)\]", runner_js_text, re.DOTALL)
    assert m, "SECTION_HEADERS array not found in runner.js"
    js_headers = set(re.findall(r'"([^"]+)"', m.group(1)))
    for required in must_have:
        assert required in js_headers, f"missing section header: {required}"


def test_appendline_uses_dom_nodes_not_innerhtml(runner_js_text):
    """Tier-1 security guarantee: no innerHTML usage in the line-rendering
    path. Each segment becomes a real DOM node so file paths / URLs /
    error messages from workflows can never inject script."""
    # Strip comments before searching so doc strings can mention innerHTML
    # in a "no innerHTML" context without false-flagging.
    without_block = re.sub(r"/\*[\s\S]*?\*/", "", runner_js_text)
    without_comments = re.sub(r"//[^\n]*", "", without_block)
    assert "innerHTML" not in without_comments, (
        "innerHTML used in runner.js — Tier 1 spec requires DOM-node "
        "construction only. Use createElement + textContent instead."
    )


# Python equivalent of the JS regex — kept in sync by hand. If you
# update either, update both.
_FILE_EXTS = "py|pyi|js|jsx|ts|tsx|md|rst|txt|yml|yaml|json|toml|cfg|ini" "|html|css|sh|bash|zsh"
_WORKFLOW_NAMES_PY = [
    "bug-predict",
    "code-review",
    "deep-review",
    "dependency-check",
    "doc-audit",
    "doc-gen",
    "doc-orchestrator",
    "health-check",
    "orchestrated-health-check",
    "perf-audit",
    "rag-code-gen",
    "refactor-plan",
    "release-prep",
    "research-synthesis",
    "secure-release",
    "security-audit",
    "simplify-code",
    "test-audit",
    "test-gen",
]
# Order: URL → file → workflow (same as JS)
_TOKEN_RE = re.compile(
    r"(https?://[^\s<>\"']+)"
    r"|"
    r"((?:[\w][\w./\-]*/)?[\w][\w.\-]*\.(?:" + _FILE_EXTS + r")(?::\d+(?::\d+)?)?)"
    r"|"
    r"\b(" + "|".join(_WORKFLOW_NAMES_PY) + r")\b"
)


def _classify(text: str) -> list[tuple[str, str]]:
    """Return [(kind, value), ...] segments for `text`."""
    out: list[tuple[str, str]] = []
    last = 0
    for m in _TOKEN_RE.finditer(text):
        if m.start() > last:
            out.append(("text", text[last : m.start()]))
        if m.group(1):
            out.append(("url", m.group(1)))
        elif m.group(2):
            out.append(("file", m.group(2)))
        elif m.group(3):
            out.append(("workflow", m.group(3)))
        last = m.end()
    if last < len(text):
        out.append(("text", text[last:]))
    return out


def test_classify_url():
    segs = _classify("see https://github.com/foo/bar/pull/1 for details")
    kinds = [k for k, _ in segs]
    assert "url" in kinds
    url = next(v for k, v in segs if k == "url")
    assert url == "https://github.com/foo/bar/pull/1"


def test_classify_file_path():
    segs = _classify("issue in src/attune/foo.py:42 inside main()")
    files = [v for k, v in segs if k == "file"]
    assert "src/attune/foo.py:42" in files


def test_classify_workflow_name():
    segs = _classify("recommended next: code-review then bug-predict")
    wfs = [v for k, v in segs if k == "workflow"]
    assert "code-review" in wfs
    assert "bug-predict" in wfs


def test_classify_preserves_surrounding_text():
    segs = _classify("Run code-review on src/foo.py to check.")
    assert segs[0] == ("text", "Run ")
    assert ("workflow", "code-review") in segs
    assert ("file", "src/foo.py") in segs
    # Trailing punctuation stays in the text segment, not the file
    last = segs[-1]
    assert last[0] == "text"
    assert last[1].endswith(".")


def test_classify_no_false_positive_on_plain_text():
    segs = _classify("Everything looks fine here.")
    assert all(k == "text" for k, _ in segs)
    assert len(segs) == 1
    assert segs[0][1] == "Everything looks fine here."


def test_classify_url_with_query_string():
    segs = _classify("docs at https://docs.example.com/api?q=foo&bar=baz")
    urls = [v for k, v in segs if k == "url"]
    assert urls == ["https://docs.example.com/api?q=foo&bar=baz"]


def test_classify_file_path_with_line_and_column():
    segs = _classify("trace: src/foo/bar.py:123:45 here")
    files = [v for k, v in segs if k == "file"]
    assert "src/foo/bar.py:123:45" in files
