"""Trap failure listener for Attune AI.

Deterministic, zero-LLM extraction of structured failure events from
Bash tool output. Two signature families (spec: self-healing-traps,
R2/non-goals): pre-commit hook rejections and pytest failures.
"""

import hashlib
import re
from dataclasses import dataclass

#: Upper bound on the detail excerpt carried into the stash.
MAX_DETAIL_CHARS = 600

# A pre-commit failure block renders as
#   black....................Failed
#   - hook id: black
#   - exit code: 1
# Passing hooks may also print "- hook id:" lines (duration output),
# so the id only counts when the preceding status line says Failed.
_PRECOMMIT_FAILED_HOOK = re.compile(r"Failed\s*\n- hook id:\s+(\S+)")

_GIT_COMMIT_COMMAND = re.compile(r"\bgit\b[^\n;|&]*\bcommit\b")

# pytest short-summary lines: "FAILED tests/x.py::test_y - Assertion…"
# and collection errors: "ERROR tests/x.py - ImportError…".
_PYTEST_FAILED_NODE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)", re.MULTILINE)
_PYTEST_COUNTS_LINE = re.compile(r"^=+.*\b(?:failed|error)\b.*=+\s*$", re.MULTILINE)


@dataclass
class TrapEvent:
    """A single deterministic failure capture.

    Attributes:
        family: Signature family (``precommit_rejection`` or
            ``pytest_failure``).
        signature: Stable per-failure dedupe key (same failure in the
            same session must produce the same signature).
        detail: Bounded factual excerpt of the failure evidence.
        command: The command line that produced the failure.
    """

    family: str
    signature: str
    detail: str
    command: str


def extract_trap(command: str, output: str) -> TrapEvent | None:
    """Extract a trap event from a Bash command's output, if any.

    Args:
        command: The command line that ran.
        output: Combined tool output text.

    Returns:
        A TrapEvent for the first matching signature family, or None
        when the output shows no recognized failure.
    """
    if not command or not output:
        return None

    trap = _extract_precommit(command, output)
    if trap is not None:
        return trap
    return _extract_pytest(command, output)


def _extract_precommit(command: str, output: str) -> TrapEvent | None:
    if not _GIT_COMMIT_COMMAND.search(command):
        return None
    failed_hooks = sorted(set(_PRECOMMIT_FAILED_HOOK.findall(output)))
    if not failed_hooks:
        return None

    first = output.find("Failed")
    excerpt = output[max(0, first - 80) : first + 300].strip()
    return TrapEvent(
        family="precommit_rejection",
        signature="precommit:" + ",".join(failed_hooks),
        detail=_bound(f"failed hooks: {', '.join(failed_hooks)}\n{excerpt}"),
        command=command,
    )


def _extract_pytest(command: str, output: str) -> TrapEvent | None:
    nodes = _PYTEST_FAILED_NODE.findall(output)
    if not nodes:
        return None
    counts = _PYTEST_COUNTS_LINE.findall(output)
    if not counts and "short test summary info" not in output:
        # "FAILED ..." lines without any pytest tail — not a test run.
        return None

    unique_nodes = sorted(set(nodes))
    digest = hashlib.sha256("\n".join(unique_nodes).encode("utf-8")).hexdigest()[:12]
    shown = unique_nodes[:5]
    lines = [f"failing: {', '.join(shown)}"]
    if len(unique_nodes) > len(shown):
        lines.append(f"(+{len(unique_nodes) - len(shown)} more)")
    if counts:
        lines.append(counts[-1].strip().strip("= "))
    return TrapEvent(
        family="pytest_failure",
        signature=f"pytest:{digest}",
        detail=_bound("\n".join(lines)),
        command=command,
    )


def _bound(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_DETAIL_CHARS:
        return text
    return text[: MAX_DETAIL_CHARS - 1] + "…"
