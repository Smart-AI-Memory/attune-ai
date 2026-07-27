"""RAG grounding hook for the attune-author polish pass.

Integrates the optional ``attune-rag`` package (installed
via ``pip install 'attune-author[rag]'``) so the LLM polish
step can consult existing attune-help templates for related
patterns before rewriting.

Design notes
------------

- **Off by default for the CLI, on by default for the Python
  API.** ``rag_enabled()`` returns True when attune_rag is
  importable AND ``ATTUNE_AUTHOR_RAG`` is not set to ``0``.
  The CLI's ``--no-rag`` flag overrides to off; the env var
  lets users flip the default in shared environments.
- **Lazy imports throughout.** ``import attune_rag`` only
  fires inside the hook functions, so attune-author loads
  cleanly without the ``[rag]`` extra.
- **Graceful degradation.** If retrieval fails for any
  reason (attune_rag absent, corpus unavailable, network
  down for hosted corpora, etc.), the hook returns None and
  the polish pass proceeds without grounding context.
  Never raises — RAG is always opt-in augmentation.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_DISABLE_ENV = "ATTUNE_AUTHOR_RAG"

# Module-level singleton so the corpus is loaded once per process rather than
# once per template kind. Thread-safe: _PIPELINE_LOCK guards first-time
# construction; subsequent reads need no lock (pipeline is immutable after init).
_PIPELINE = None  # type: ignore[assignment]  # RagPipeline | None
_PIPELINE_LOCK = threading.Lock()


def _get_pipeline():  # type: ignore[return]
    """Return the process-level RagPipeline, constructing it on first call."""
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE
    with _PIPELINE_LOCK:
        if _PIPELINE is None:
            from attune_rag import RagPipeline

            _PIPELINE = RagPipeline()
    return _PIPELINE


def rag_enabled() -> bool:
    """Return True when RAG grounding should be used.

    Rules, in order:

    1. If ``ATTUNE_AUTHOR_RAG=0`` (exact string ``"0"``),
       return False — lets users flip the default off in
       shared CI or when they want deterministic output.
    2. If the ``attune_rag`` package can't be imported,
       return False — the [rag] extra isn't installed.
    3. Otherwise, return True.
    """
    if os.environ.get(_DISABLE_ENV) == "0":
        return False
    try:
        import attune_rag  # noqa: F401
    except ImportError:
        return False
    return True


def ground_polish_context(
    feature_name: str,
    template_type: str,
    k: int = 3,
) -> str | None:
    """Build a grounding context block for the polish pass.

    Queries the default attune-rag corpus (attune-help) for
    templates similar to the one being polished and returns
    a markdown block of related content that the polish LLM
    call can use to cross-reference conventions, naming, and
    section structure.

    Returns None when:

    - ``rag_enabled()`` is False
    - attune_rag raises during pipeline construction or run
    - The query resolves to the fallback (no-match) prompt,
      meaning the corpus doesn't have anything relevant

    Args:
        feature_name: The feature being polished (e.g.
            ``"security-audit"``).
        template_type: Template kind — ``"concept"``,
            ``"reference"``, ``"quickstart"``, etc. Shapes
            the retrieval query so the hits are same-shape
            examples.
        k: Max hits to include in the context block.

    Returns:
        A markdown context string ready to prepend to the
        polish user_message, or None when grounding is
        unavailable / uninformative.
    """
    if not rag_enabled():
        return None

    query = f"{template_type} template for {feature_name}"

    try:
        pipeline = _get_pipeline()
        result = pipeline.run(query, k=k)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: grounding is best-effort. Any
        # pipeline failure (missing corpus, schema drift,
        # transient I/O) should degrade to non-grounded
        # polish rather than breaking generation.
        logger.warning(
            "RAG grounding failed for feature=%s type=%s; proceeding without context",
            feature_name,
            template_type,
            exc_info=True,
        )
        return None

    if result.fallback_used or not result.citation.hits:
        return None

    # attune-rag 0.1.3+ exposes the joined context directly on
    # RagResult; previously we rebuilt it from citation hits via
    # pipeline.corpus.get + join_context. Slice to an 8 KB
    # budget so polish prompts stay bounded (join_context itself
    # truncates at 20 KB by default, which is larger than polish
    # calls need).
    context_body = result.context[:_POLISH_CONTEXT_MAX_CHARS]

    source_paths = ", ".join(h.template_path for h in result.citation.hits)
    header = (
        "## Related existing templates (for reference)\n\n"
        f"The following attune-help entries match this "
        f"feature/type ({source_paths}). Use them as style "
        "and naming references — do NOT copy content or "
        "invent anything they don't attest.\n\n"
    )
    return header + context_body + "\n\n"


_POLISH_CONTEXT_MAX_CHARS = 8_000
