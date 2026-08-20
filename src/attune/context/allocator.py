"""Token Budget Allocator for Attune AI.

Manages dynamic allocation of full source code vs. AST skeletal context
based on token budget constraints and target file prioritization.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .skeleton import ASTSkeletonGenerator

logger = logging.getLogger(__name__)

_FALSEY = {"0", "false", "no", "off"}


def _fit_events_path() -> Path:
    """Resolve the local fit-telemetry stream (sibling of usage.jsonl).

    Resolution mirrors the repo's other telemetry sinks
    (``memory.serve_telemetry._events_path``,
    ``gates.lifecycle.ledger.ledger_path``): ``ATTUNE_HOME`` env
    override, expanded, else ``~/.attune``.
    """
    home = os.environ.get("ATTUNE_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".attune"
    return base / "telemetry" / "context_fit.jsonl"


def _append_fit_event(payload: dict[str, int | str]) -> None:
    """Append one fit outcome to the local telemetry stream.

    Best-effort, never raises — telemetry must not block a fit. Disable
    with ``ATTUNE_CONTEXT_FIT_TELEMETRY=0``. The record is serialized to
    one string and written in a single call so concurrent appenders
    cannot interleave partial records.
    """
    if os.environ.get("ATTUNE_CONTEXT_FIT_TELEMETRY", "1").strip().lower() in _FALSEY:
        return
    try:
        path = _fit_events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        record = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            **payload,
        }
        line = json.dumps(record, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: the docstring promises never-raises — a TypeError
        # from an unserializable payload must not block a fit any more
        # than an OSError from the filesystem (library-review R5).
        logger.debug("context_fit telemetry append failed: %s", e)


class TokenBudgetAllocator:
    """Balances full source inclusion vs. AST skeletal compression."""

    def __init__(self, default_token_limit: int = 4000) -> None:
        """Initialize TokenBudgetAllocator.

        Args:
            default_token_limit: Maximum estimated token budget for context.
        """
        self.default_token_limit = default_token_limit
        self.generator = ASTSkeletonGenerator()
        #: Outcome of the most recent :meth:`fit_source` call, or None
        #: before the first call. Keys: ``rung`` (``full`` /
        #: ``skeleton`` / ``truncated_skeleton`` / ``plain_truncation``),
        #: ``token_limit``, ``source_tokens`` (estimate), and
        #: ``result_tokens`` (estimate of what was returned).
        self.last_fit: dict[str, int | str] | None = None

    def allocate_context(
        self,
        files: dict[str, str],
        primary_target: str | None = None,
        token_limit: int | None = None,
    ) -> dict[str, str]:
        """Allocates context format (full vs skeleton) across files.

        The primary target always retains full source, even when it
        alone exceeds the budget (a warning is logged in that case).
        Remaining files receive skeletons while budget lasts, then an
        omission stub.

        Args:
            files: Dictionary mapping file paths to full source code.
            primary_target: Target path that should retain full source.
            token_limit: Custom token limit override.

        Returns:
            Dictionary mapping file paths to allocated context string
            (full source, skeleton, or omission stub).
        """
        limit = token_limit or self.default_token_limit
        allocated: dict[str, str] = {}
        current_tokens = 0

        if primary_target and primary_target in files:
            full_code = files[primary_target]
            allocated[primary_target] = full_code
            current_tokens += self._estimate_tokens(full_code)
            if current_tokens > limit:
                logger.warning(
                    "allocator: primary target %s alone exceeds token limit "
                    "(%d > %d); all other files will be stubbed",
                    primary_target,
                    current_tokens,
                    limit,
                )

        for path, code in files.items():
            if path == primary_target:
                continue

            skeleton = self.generator.generate_skeleton(code)
            skel_tokens = self._estimate_tokens(skeleton)

            if current_tokens + skel_tokens <= limit:
                allocated[path] = skeleton
                current_tokens += skel_tokens
            else:
                allocated[path] = f"# AST skeleton omitted (token limit {limit} reached)\n"

        return allocated

    def fit_source(self, source: str, token_limit: int | None = None) -> str:
        """Fit a single source string into the token budget.

        The ladder: full source when it fits; the AST skeleton when
        that fits (preserving every signature and docstring while
        dropping bodies); otherwise the skeleton head-truncated to
        the budget with an omission marker. Non-Python source passes
        through the skeleton step unchanged, so it degrades to plain
        truncation.

        This is the single-string counterpart to
        :meth:`allocate_context` — use it where a prompt embeds one
        file's source under a budget, in place of a bare character
        slice that chops the tail of the module off mid-function.

        Args:
            source: Source code (or arbitrary text) to fit.
            token_limit: Custom token limit override.

        Returns:
            The source, its skeleton, or a truncated skeleton,
            whichever is the richest representation within budget.
        """
        limit = token_limit or self.default_token_limit
        source_tokens = self._estimate_tokens(source)
        if source_tokens <= limit:
            self._record_fit("full", limit, source_tokens, source_tokens)
            return source
        skeleton = self.generator.generate_skeleton(source)
        skeleton_tokens = self._estimate_tokens(skeleton)
        if skeleton_tokens <= limit:
            self._record_fit("skeleton", limit, source_tokens, skeleton_tokens)
            return skeleton
        # A skeleton identical to the source means the AST step could
        # not help (non-Python or unparseable) — the truncation below
        # is then plain truncation, not a truncated skeleton.
        rung = "plain_truncation" if skeleton == source else "truncated_skeleton"
        self._record_fit(rung, limit, source_tokens, limit)
        return skeleton[: limit * 4] + f"\n# ... truncated at token limit {limit}\n"

    def _record_fit(self, rung: str, limit: int, source_tokens: int, result_tokens: int) -> None:
        """Record a fit_source outcome on the instance and the log.

        The log line is the durable measurement surface (grep
        ``context_fit`` across run logs to see rung frequency and
        truncation rates); ``last_fit`` is the programmatic one.
        """
        self.last_fit = {
            "rung": rung,
            "token_limit": limit,
            "source_tokens": source_tokens,
            "result_tokens": result_tokens,
        }
        _append_fit_event(self.last_fit)
        logger.info(
            "context_fit rung=%s token_limit=%d source_tokens=%d result_tokens=%d",
            rung,
            limit,
            source_tokens,
            result_tokens,
        )

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation (approx 4 chars per token)."""
        return len(text) // 4
