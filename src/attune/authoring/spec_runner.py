"""Bounded, observable Fable spec-drafting runner.

FABLE_SPEC_WORKFLOW_TODO item 2: stream progress instead of waiting on
one final block, enforce separate time-to-first-event / inter-event /
total-run limits, switch to per-document generation after ONE failed
whole-spec attempt (the same strategy is never retried in a run),
capture provider failures without exposing secrets, and validate file
markers and output-size limits before any caller materializes files.

Budgets default to the ratified numbers in
``docs/process/fable-spec-benchmark/DECISION_MATRIX.md`` (Patrick,
2026-07-22, PR #1590): 30s first event, 90s inter-event, 180s
single-document total, 480s multi-document total.

The runner never writes files — it returns validated document text and
a per-attempt audit trail; materialization (and its path validation)
stays with the caller.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import queue
import re
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from attune.model_tiers import fable_extras

FILE_MARKER = re.compile(r"^=== FILE: (\S+) ===$", re.MULTILINE)
_SECRET_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]+")

WHOLE_SPEC = "whole-spec"
PER_DOCUMENT = "per-document"

_SINGLE_DOC_MAX_TOKENS = 32_000
_MULTI_DOC_MAX_TOKENS = 64_000


@dataclass(frozen=True)
class DocRequest:
    """One document the caller wants drafted."""

    path: str
    instructions: str


@dataclass(frozen=True)
class Budgets:
    """Run bounds — defaults are the ratified decision-matrix numbers."""

    first_event_s: float = 30.0
    inter_event_s: float = 90.0
    total_single_s: float = 180.0
    total_multi_s: float = 480.0
    max_chars_per_doc: int = 150_000

    def total_for(self, doc_count: int) -> float:
        """Total-run bound for a packet of ``doc_count`` documents."""
        return self.total_single_s if doc_count <= 1 else self.total_multi_s


@dataclass
class Attempt:
    """Audit record for one generation call."""

    strategy: str
    doc_paths: list[str]
    ttfe_s: float | None = None
    total_s: float | None = None
    output_chars: int = 0
    stop_reason: str | None = None
    failure: str | None = None


@dataclass
class DraftResult:
    """Outcome of one :meth:`SpecDraftRunner.draft` run."""

    documents: dict[str, str] = field(default_factory=dict)
    attempts: list[Attempt] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when every requested document validated."""
        return not self.failures


def _sanitize(message: str) -> str:
    """Strip anything shaped like an Anthropic key from an error string."""
    return _SECRET_PATTERN.sub("sk-ant-***", message)


def _describe_error(exc: BaseException) -> str:
    """Provider failure as ``Type(status): message`` — secrets redacted."""
    status = getattr(exc, "status_code", None)
    suffix = f"({status})" if status is not None else ""
    return _sanitize(f"{type(exc).__name__}{suffix}: {exc}")


def parse_documents(text: str) -> dict[str, str]:
    """Split marker-delimited output into ``{path: content}``."""
    parts = FILE_MARKER.split(text)
    # split() yields [preamble, path1, body1, path2, body2, ...]
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def build_prompt(brief: str, docs: Sequence[DocRequest]) -> str:
    """Assemble the drafting prompt for one packet (whole or partial)."""
    doc_lines = "\n".join(f"- {d.path} — {d.instructions}" for d in docs)
    return (
        f"{brief}\n\n"
        f"Write the following {len(docs)} document(s) in full:\n{doc_lines}\n\n"
        "Output format (mandatory): precede EVERY document with a line of "
        "exactly `=== FILE: <path> ===` on its own line, then the complete "
        "markdown content. No prose outside the documents."
    )


class SpecDraftRunner:
    """Drive bounded, streaming spec generation with one strategy switch.

    ``client`` is an ``anthropic.Anthropic``-compatible object; only
    ``client.beta.messages.create(..., stream=True)`` is used. Pass
    ``on_progress`` to receive ``(stage, elapsed_s)`` progress ticks —
    the observable heartbeat the workflow todo demands.
    """

    def __init__(
        self,
        client: Any,
        *,
        model: str = "claude-fable-5",
        budgets: Budgets | None = None,
        on_progress: Callable[[str, float], None] | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._budgets = budgets or Budgets()
        self._on_progress = on_progress or (lambda stage, elapsed: None)

    def draft(self, brief: str, docs: Sequence[DocRequest]) -> DraftResult:
        """Draft ``docs``, whole-spec first, per-document on failure.

        The whole-spec strategy is attempted at most once per run; any
        failure (first-event timeout, stall, provider error, refusal)
        switches to per-document for the outstanding work. Documents
        that fail marker or size validation are re-requested
        individually, once each.
        """
        result = DraftResult()
        by_path = {d.path: d for d in docs}

        text, attempt = self._run_attempt(WHOLE_SPEC, brief, list(docs))
        result.attempts.append(attempt)
        if attempt.failure is None:
            self._collect_valid(parse_documents(text), by_path, result)
        pending = [d for d in docs if d.path not in result.documents]

        for doc in pending:  # per-document fallback — once per doc
            text, attempt = self._run_attempt(PER_DOCUMENT, brief, [doc])
            result.attempts.append(attempt)
            if attempt.failure is not None:
                result.failures[doc.path] = attempt.failure
                continue
            self._collect_valid(parse_documents(text), {doc.path: doc}, result)
            if doc.path not in result.documents:
                result.failures[doc.path] = result.failures.get(
                    doc.path, "document missing from per-document output"
                )
        return result

    def _collect_valid(
        self,
        parsed: dict[str, str],
        wanted: dict[str, DocRequest],
        result: DraftResult,
    ) -> None:
        """Move size-valid, non-empty wanted documents into the result."""
        limit = self._budgets.max_chars_per_doc
        for path in wanted:
            content = parsed.get(path)
            if content is None or not content.strip():
                continue  # missing → stays pending for per-document pass
            if len(content) > limit:
                result.failures[path] = f"document exceeds size limit ({len(content)} > {limit})"
                continue
            result.documents[path] = content
            result.failures.pop(path, None)

    def _run_attempt(
        self, strategy: str, brief: str, docs: list[DocRequest]
    ) -> tuple[str, Attempt]:
        """Stream one generation call under the budget bounds."""
        budgets = self._budgets
        attempt = Attempt(strategy=strategy, doc_paths=[d.path for d in docs])
        total_budget = budgets.total_for(len(docs))
        max_tokens = _SINGLE_DOC_MAX_TOKENS if len(docs) <= 1 else _MULTI_DOC_MAX_TOKENS
        events: queue.Queue[tuple[str, Any]] = queue.Queue()
        abandoned = threading.Event()

        def _produce() -> None:
            try:
                stream = self._client.beta.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": build_prompt(brief, docs)}],
                    stream=True,
                    **fable_extras(self._model),
                )
                for event in stream:
                    if abandoned.is_set():
                        return
                    events.put(("event", event))
                events.put(("end", None))
            except BaseException as exc:  # noqa: BLE001 — relayed, never swallowed
                events.put(("error", exc))

        threading.Thread(target=_produce, daemon=True).start()

        parts: list[str] = []
        start = time.monotonic()
        wait_s = budgets.first_event_s
        while True:
            try:
                kind, payload = events.get(timeout=wait_s)
            except queue.Empty:
                if time.monotonic() - start >= total_budget:
                    attempt.failure = "total_timeout"
                elif attempt.ttfe_s is None:
                    attempt.failure = "first_event_timeout"
                else:
                    attempt.failure = "inter_event_timeout"
                break
            elapsed = time.monotonic() - start
            if attempt.ttfe_s is None:
                attempt.ttfe_s = round(elapsed, 2)
                self._on_progress(f"{strategy}: first event", elapsed)
            if kind == "end":
                break
            if kind == "error":
                attempt.failure = _describe_error(payload)
                break
            if elapsed > total_budget:
                attempt.failure = "total_timeout"
                break
            etype = getattr(payload, "type", "")
            if etype == "content_block_delta":
                delta_text = getattr(payload.delta, "text", None)
                if delta_text:
                    parts.append(delta_text)
            elif etype == "message_delta":
                attempt.stop_reason = getattr(payload.delta, "stop_reason", None)
                if attempt.stop_reason == "refusal":
                    attempt.failure = "refusal"
            wait_s = min(budgets.inter_event_s, max(total_budget - elapsed, 0.001))

        abandoned.set()
        attempt.total_s = round(time.monotonic() - start, 2)
        text = "".join(parts)
        attempt.output_chars = len(text)
        self._on_progress(f"{strategy}: done ({attempt.failure or 'ok'})", time.monotonic() - start)
        return text, attempt
