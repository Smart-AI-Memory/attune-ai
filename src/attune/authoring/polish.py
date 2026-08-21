"""LLM polish pass for generated help templates.

After Jinja2 renders the structural skeleton, this module
sends the content through an LLM to improve writing quality:
replace formulaic filler, sharpen descriptions, verify
accuracy against the source info provided.

Per-type system prompts live in :mod:`polish_prompts`. This
module owns the polish call orchestration, strict/lenient
mode handling, and the source-summary builder that feeds
context to the prompt. The underlying SDK call is routed
through :mod:`attune.models.single_turn` so that credential
redaction, subscription-first auth routing, and error wrapping
are shared with the rest of attune-ai.

Strict mode
-----------

Polish is strict by default: a missing ``ANTHROPIC_API_KEY``
or any LLM-call failure raises :class:`PolishError`. Polish
exists because the raw Jinja2 output is not acceptable on
its own; treating the LLM pass as best-effort would quietly
ship lower-quality templates.

Opting out of strict mode is explicit and deliberate:

1. Pass ``strict=False`` to :func:`polish_template` directly.
2. Set the ``ATTUNE_AUTHOR_STRICT_POLISH`` environment
   variable to a falsy value (``0``, ``false``, ``no``,
   ``off``) — useful for CI that runs the generator without
   credentials. The explicit ``strict`` argument always
   overrides the environment variable.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from attune.authoring.polish_prompts import get_system_prompt
from attune.models import single_turn
from attune.models.editing import resolve_editing_model
from attune.models.single_turn import AnthropicCallError


def _polish_model() -> str:
    """Anthropic model for the polish pass: the editing model.

    Sonnet drafts; polish is an editing pass and runs on the editing
    model (``ATTUNE_MODEL_EDITING`` env pin respected, default
    claude-opus-5 — ruled 2026-07-29). Resolved per call and fed into
    the cache key, so a model change — via env pin or a default bump
    — invalidates cache entries automatically.
    """
    return resolve_editing_model()


#: Env var that overrides the default polish cache directory.
_CACHE_DIR_ENV = "ATTUNE_AUTHOR_POLISH_CACHE"
_CACHE_DIR_DEFAULT = Path.home() / ".attune" / "polish_cache"

#: Env var (in seconds) that overrides the default cache-entry
#: TTL. ``0`` disables pruning entirely; negatives and unparseable
#: values fall back to the default. Tracked via mtime, which we
#: bump on every cache hit so heat is observed reliably even on
#: filesystems mounted ``noatime``.
_CACHE_TTL_ENV = "ATTUNE_AUTHOR_POLISH_CACHE_TTL_SECONDS"
_CACHE_TTL_DEFAULT_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _cache_dir() -> Path:
    env = os.environ.get(_CACHE_DIR_ENV, "").strip()
    return Path(env) if env else _CACHE_DIR_DEFAULT


def _cache_ttl_seconds() -> int:
    """Read the cache TTL from the environment.

    Returns the default (30 days) when the env var is unset,
    blank, negative, or unparseable. ``0`` is honored as
    "disable pruning" and returned verbatim.
    """
    raw = os.environ.get(_CACHE_TTL_ENV, "").strip()
    if not raw:
        return _CACHE_TTL_DEFAULT_SECONDS
    try:
        val = int(raw)
    except ValueError:
        return _CACHE_TTL_DEFAULT_SECONDS
    return val if val >= 0 else _CACHE_TTL_DEFAULT_SECONDS


#: Volatile YAML frontmatter fields that change on every render
#: but do not affect the polish output. Stripped from ``content``
#: before hashing the cache key so the cache actually hits when
#: the same source is regenerated. The LLM still sees the real
#: ``content`` (with the live timestamp) — only the *key* is
#: normalized. Without this, every render embeds a fresh
#: ``generated_at: <iso-8601>`` and the cache never hits.
_VOLATILE_FRONTMATTER_FIELDS = ("generated_at",)
_VOLATILE_FRONTMATTER_RE = re.compile(
    r"^(" + "|".join(re.escape(f) for f in _VOLATILE_FRONTMATTER_FIELDS) + r"):.*$",
    re.MULTILINE,
)


def _normalize_for_key(content: str) -> str:
    """Strip volatile frontmatter fields so the cache key is stable.

    Replaces every line beginning with a known volatile field
    (currently just ``generated_at:``) with a placeholder. The
    real content fed to the LLM is unchanged — this transform
    only feeds the hash.
    """
    return _VOLATILE_FRONTMATTER_RE.sub(r"\1: <stable>", content)


def _cache_key(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\x00")
    return h.hexdigest()


def _cache_get(key: str) -> str | None:
    path = _cache_dir() / f"{key}.md"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Bump mtime so the prune sweeper treats this entry as hot.
    # Best-effort: a permission error here just means the entry
    # may age out sooner than its actual access pattern warrants,
    # which is acceptable degradation.
    try:
        os.utime(path, None)
    except OSError:
        pass
    return content


def _cache_put(key: str, content: str) -> None:
    cache = _cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    # mkstemp names the temp file uniquely per call: deriving it from the
    # key lets two processes pick the same path, so one truncates the
    # other's partial write before the rename publishes it (class G1).
    # replace() rather than rename() — rename fails on Windows when the
    # destination already exists, which is the common case for a re-put.
    fd, tmp_name = tempfile.mkstemp(prefix=f".{key}.", suffix=".tmp", dir=str(cache))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        tmp.replace(cache / f"{key}.md")
    finally:
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()
    # Lazy disk-space hygiene: piggyback the prune onto write
    # operations so we don't need a separate scheduler. Cost is
    # one stat per entry in the cache dir, which is negligible
    # for the entry counts a single project produces.
    try:
        _cache_prune(cache)
    except OSError:
        # INTENTIONAL: prune failure must not break a successful
        # write — the cache stays usable, it just doesn't shrink.
        pass


def _cache_prune(cache: Path | None = None) -> int:
    """Delete cache entries whose mtime is older than the TTL.

    Args:
        cache: Cache directory to sweep. Defaults to
            :func:`_cache_dir`. Accepting an explicit path keeps
            the function trivially testable without monkey-patching
            the env.

    Returns:
        Count of files deleted. ``0`` when the cache directory
        does not exist or the TTL is set to ``0`` (disabled).
    """
    cache = cache if cache is not None else _cache_dir()
    ttl = _cache_ttl_seconds()
    if ttl <= 0 or not cache.exists():
        return 0
    cutoff = time.time() - ttl
    deleted = 0
    for entry in cache.iterdir():
        if entry.suffix != ".md":
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
                deleted += 1
        except OSError:
            # Swallow per-entry failures so a single locked or
            # vanished file doesn't block the rest of the sweep.
            continue
    return deleted


def clear_cache() -> int:
    """Delete every entry in the polish cache directory.

    Removes both finalized ``.md`` entries and any leftover
    ``.tmp`` files from interrupted writes. Best-effort: per-entry
    failures are swallowed so a single locked file does not block
    the remaining deletions.

    Returns:
        Count of files deleted. ``0`` when the cache directory
        does not exist.
    """
    cache = _cache_dir()
    if not cache.exists():
        return 0
    deleted = 0
    for entry in cache.iterdir():
        if entry.suffix not in {".md", ".tmp"}:
            continue
        try:
            entry.unlink()
            deleted += 1
        except OSError:
            continue
    return deleted


logger = logging.getLogger(__name__)

#: Environment variable that flips polish out of strict mode.
#: Strict is the default — this variable exists only as an
#: explicit opt-out for environments that genuinely cannot
#: run the LLM pass (e.g. CI without credentials).
STRICT_ENV_VAR = "ATTUNE_AUTHOR_STRICT_POLISH"

#: Values of ``STRICT_ENV_VAR`` that disable strict mode.
#: Anything else — unset, truthy, or unrecognized — keeps
#: strict behavior, which is the whole point of the flip.
_FALSY = frozenset({"0", "false", "no", "off"})


def _env_strict_default() -> bool:
    """Read the strict-mode default from the environment.

    Strict is the default. The environment variable exists
    only to let callers opt out by setting it to a falsy
    value.

    Returns:
        False if ``STRICT_ENV_VAR`` is explicitly set to a
        falsy value; True otherwise.
    """
    val = os.environ.get(STRICT_ENV_VAR, "").strip().lower()
    return val not in _FALSY


class PolishError(RuntimeError):
    """Raised when the polish pass fails in strict mode.

    Lenient mode never raises — it logs a warning and
    returns the original content.
    """


def polish_template(
    content: str,
    feature_name: str,
    source_summary: str,
    template_type: str = "generic",
    strict: bool | None = None,
    augmented_context: str | None = None,
    include_ground_truth_anchor: bool = False,
) -> str:
    """Polish a generated template using an LLM.

    Args:
        content: The Jinja2-rendered markdown, including
            YAML frontmatter.
        feature_name: Name of the feature being documented.
            Used in the user-message context.
        source_summary: Summary of source info (classes,
            functions, signatures, docstrings) built by
            :func:`build_source_summary`. Serves as the
            accuracy anchor for the LLM rewrite.
        template_type: Template kind being polished —
            concept, task, reference, error, warning,
            troubleshooting, faq, or ``"generic"`` as a
            fallback. Controls which system prompt the LLM
            sees.
        strict: If True (the default when ``None``), any
            failure in the polish pass (missing API key,
            network error, SDK error) raises
            :class:`PolishError`. If False, failures fall
            back to returning the original content. When
            ``None``, the value is read from the
            ``ATTUNE_AUTHOR_STRICT_POLISH`` environment
            variable, which defaults to strict.

    Returns:
        Polished markdown string, or the original content
        if polish failed and strict mode is off.

    Raises:
        PolishError: If the polish pass fails and strict
            mode is enabled.
    """
    effective_strict = _env_strict_default() if strict is None else strict

    system_prompt = get_system_prompt(template_type)
    if include_ground_truth_anchor:
        from attune.authoring.ground_truth import ANCHORING_CLAUSE

        system_prompt = system_prompt + ANCHORING_CLAUSE
    key = _cache_key(
        _normalize_for_key(content),
        source_summary,
        template_type,
        system_prompt,
        augmented_context or "",
        _polish_model(),
    )
    cached = _cache_get(key)
    if cached is not None:
        logger.debug("Polish cache hit for %s/%s", feature_name, template_type)
        # Re-sanitize on read: entries written before the
        # fence-stripping fix (2026-06-11) may carry a wrapping
        # ```markdown fence that breaks the downstream frontmatter
        # merge. Sanitizing here heals poisoned entries without a
        # cache purge; it's a no-op for clean entries.
        return _sanitize_output(cached)

    try:
        polished = _call_llm(
            content,
            feature_name,
            source_summary,
            template_type,
            augmented_context=augmented_context,
            include_ground_truth_anchor=include_ground_truth_anchor,
        )
        result = _sanitize_output(polished)
        try:
            _cache_put(key, result)
        except OSError as cache_exc:
            logger.debug("Polish cache write failed (non-fatal): %s", cache_exc)
        return result
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: lenient mode swallows any LLM failure
        # so that `attune-author` can still run without an
        # API key when the caller has explicitly opted out.
        # Strict mode (the default) rewraps everything in
        # PolishError so callers have a single exception
        # type to catch.
        if effective_strict:
            raise PolishError(
                f"Polish pass failed for {feature_name!r} (type={template_type!r}): {exc}"
            ) from exc
        # Lenient mode is the explicit opt-out from strict, so a
        # failure here is the user-visible degradation we promised
        # in the docs — log at error level so it shows up in
        # default log filters, not just verbose runs.
        logger.error(
            "Polish pass failed for %s (type=%s), using raw template: %s",
            feature_name,
            template_type,
            exc,
        )
        return _mark_polish_skipped(content)


def _mark_polish_skipped(content: str) -> str:
    # Surface a polish bypass in the rendered YAML frontmatter so
    # the regression shows up in PR diffs. Without this marker,
    # raw-Jinja output looks indistinguishable from a normal
    # generation (same headings, same frontmatter shape) and slips
    # past review — see attune-author#30 and attune-rag d39e39d.
    #
    # Only YAML frontmatter is supported. Non-YAML output (e.g.
    # project-doc templates with an HTML comment footer) passes
    # through unchanged; surfacing bypass there would need a
    # different mechanism.
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    frontmatter = content[4:end]
    rest = content[end + 5 :]
    if "\npolish:" in "\n" + frontmatter:
        # Idempotent: don't double-write if a previous run already
        # marked the file.
        return content
    new_frontmatter = frontmatter.rstrip("\n") + "\npolish: skipped\n"
    return f"---\n{new_frontmatter}---\n{rest}"


def _strip_wrapping_fence(content: str) -> str:
    r"""Strip a code fence wrapping the ENTIRE response, if present.

    The polish LLM occasionally returns the whole template wrapped
    in a fenced block (```` ```markdown ... ``` ````) — observed
    live 2026-06-11 on the subscription route. Unstripped, the
    fence defeats :func:`attune.authoring.generator.
    _replace_polished_frontmatter`'s ``\A---`` anchor, which then
    prepends a second frontmatter block and ships the fenced
    duplicate as the body.

    Conservative: only strips when the FIRST line is an opening
    fence (``` or ```<lang>) AND the LAST non-blank line is a bare
    closing ```. Interior fences (real code blocks in the body)
    are untouched because the wrapping pair is removed only from
    the extremes.

    Args:
        content: Raw text returned by the LLM.

    Returns:
        Content without the wrapping fence, or unchanged when no
        full wrap is detected.
    """
    stripped = content.strip()
    if not stripped.startswith("```"):
        return content
    lines = stripped.splitlines()
    if len(lines) < 2 or lines[-1].strip() != "```":
        return content
    return "\n".join(lines[1:-1])


def _sanitize_output(content: str) -> str:
    """Apply fence, trailing-whitespace, and newline hygiene.

    The Anthropic API does not guarantee a trailing newline
    and occasionally leaves trailing whitespace on
    individual lines (most often from markdown ``  `` line
    breaks the model emits in tables and lists). Both of
    these break the no-trailing-whitespace and
    single-trailing-newline invariants the rest of the
    pipeline enforces, so we normalize them here. A response
    wrapped whole in a code fence is unwrapped first (see
    :func:`_strip_wrapping_fence`).

    Args:
        content: Raw text returned by the LLM.

    Returns:
        Content with any wrapping fence removed, each line
        right-stripped, and exactly one trailing newline.
    """
    if not content:
        return content
    content = _strip_wrapping_fence(content)
    body = "\n".join(line.rstrip() for line in content.splitlines())
    if not body.endswith("\n"):
        body += "\n"
    return body


def build_polish_prompt(
    content: str,
    feature_name: str,
    source_summary: str,
    template_type: str,
    augmented_context: str | None = None,
    include_ground_truth_anchor: bool = False,
) -> tuple[str, str]:
    """Build the (system_prompt, user_message) pair for a polish call.

    Extracted so alternative call paths (historically the
    attune-author batch API) can build byte-identical prompts to
    the synchronous path. Pure: no side effects, no I/O.

    Args:
        content: Rendered template content to polish.
        feature_name: Feature identifier (e.g., ``"ops-dashboard"``).
        source_summary: Source-info text passed to the model as an
            accuracy anchor.
        template_type: Template kind — selects the system prompt.
        augmented_context: Optional grounding text injected into the
            user message above the source summary. Supplied by the
            RAG hook and/or :mod:`attune.authoring.ground_truth`.
        include_ground_truth_anchor: When ``True`` (only set by
            callers that injected ground-truth context), append a
            short anchoring clause to the system prompt instructing
            the model to use only names that appear verbatim in the
            ``<cli_help>`` / ``<public_api>`` / ``<dataclasses>``
            blocks. See polish-fact-check Phase 2.

    Returns:
        ``(system_prompt, user_message)`` ready to pass to
        either :func:`call_anthropic` (synchronous) or
        :class:`BatchPolishRequest` construction (batch).
    """
    system_prompt = get_system_prompt(template_type)
    if include_ground_truth_anchor:
        from attune.authoring.ground_truth import ANCHORING_CLAUSE

        system_prompt = system_prompt + ANCHORING_CLAUSE
    grounding = augmented_context or ""
    user_message = (
        f"Polish this auto-generated {template_type} template "
        f"for the '{feature_name}' feature.\n\n"
        f"{grounding}"
        f"## Source info (for accuracy checking)\n\n"
        f"{source_summary}\n\n"
        f"## Template to polish\n\n"
        f"{content}"
    )
    return system_prompt, user_message


#: Polish-call defaults. Exposed as constants so the batch path
#: can build identical ``BatchPolishRequest`` envelopes without
#: hard-coding values that the synchronous path might drift away
#: from. ``cache_system=True`` because the polish system prompt is
#: ~6000 tokens — well over the 1024-token sonnet caching threshold;
#: cache hits cut input cost ~90% on repeated polish passes.
#: 6144, not the pre-tier 4096: sonnet-5/fable-5 tokenize ~30% heavier
#: than sonnet-4-6, and a truncated polish silently drops template tail
#: content (specs/fable-model-tiers design, data-model notes). Billing
#: is per emitted token, so the extra headroom is free insurance.
POLISH_MAX_TOKENS = 6144
POLISH_CACHE_SYSTEM = True

#: Rolling hit rate below which the end-of-run summary appends a
#: warning. A healthy polish run that re-touches templates should
#: sit well above this once the system prompt is cached; sustained
#: lows usually mean the cache boundary broke (prompt edit, model
#: alias drift) — see the README "Cache hit rate" section.
_CACHE_HIT_WARN_THRESHOLD = 0.5


@dataclass(frozen=True)
class PolishCacheStats:
    """Aggregate prompt-cache token usage across polish calls.

    ``creation_tokens`` are input tokens written into Anthropic's
    prompt cache; ``read_tokens`` are input tokens served from it.
    The hit rate is ``read / (read + creation)`` — the fraction of
    cacheable input that came from cache rather than being re-billed.
    """

    calls: int = 0
    creation_tokens: int = 0
    read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.read_tokens + self.creation_tokens

    @property
    def hit_rate(self) -> float:
        """Cache read fraction in ``[0.0, 1.0]``; ``0.0`` when no
        cacheable tokens were seen (avoids divide-by-zero)."""
        return self.read_tokens / max(self.total_tokens, 1)

    def summary_line(self) -> str:
        """One-line human summary for end-of-run output.

        Degrades gracefully when no cacheable tokens were seen (no
        cache configured, or prompt below the caching threshold).
        """
        if self.total_tokens == 0:
            return "Polish cache: no cacheable tokens observed (cache not configured?)"
        return (
            f"Polish cache hit: {self.hit_rate:.0%} "
            f"({self.read_tokens} read / {self.total_tokens} total tokens, "
            f"{self.calls} call(s))"
        )


def _polish_cache_telemetry() -> dict[str, int]:
    """Per-process aggregate of prompt-cache token usage.

    Stored on the function as an attribute so the end-of-run summary
    can read totals without module-level state — same idiom as
    ``generator._faithfulness_telemetry``. Reset via
    :func:`reset_polish_cache_telemetry`.
    """
    state = getattr(_polish_cache_telemetry, "_state", None)
    if state is None:
        state = {"calls": 0, "creation": 0, "read": 0}
        _polish_cache_telemetry._state = state  # type: ignore[attr-defined]
    return state


def reset_polish_cache_telemetry() -> None:
    """Reset the per-process prompt-cache telemetry counters."""
    _polish_cache_telemetry._state = {  # type: ignore[attr-defined]
        "calls": 0,
        "creation": 0,
        "read": 0,
    }


def _record_cache_usage(creation: int, read: int, model: str) -> None:
    """Accumulate one polish call's cache token counts.

    Wired into :func:`call_anthropic` via its ``on_cache_usage``
    hook. ``model`` is accepted to match the callback signature but
    not aggregated — per-model breakdown is out of scope (decisions.md).
    """
    state = _polish_cache_telemetry()
    state["calls"] += 1
    state["creation"] += creation
    state["read"] += read


def polish_cache_stats() -> PolishCacheStats:
    """Snapshot the current per-process prompt-cache aggregate."""
    state = _polish_cache_telemetry()
    return PolishCacheStats(
        calls=state["calls"],
        creation_tokens=state["creation"],
        read_tokens=state["read"],
    )


def format_polish_cache_summary() -> str | None:
    """End-of-run summary line, or ``None`` if polish never ran.

    Appends a low-hit-rate warning when the run's hit rate falls below
    :data:`_CACHE_HIT_WARN_THRESHOLD` and at least one cacheable token
    was seen. Scope is the current process: callers reset at run start.
    """
    stats = polish_cache_stats()
    if stats.calls == 0:
        return None
    line = stats.summary_line()
    if stats.total_tokens > 0 and stats.hit_rate < _CACHE_HIT_WARN_THRESHOLD:
        line += (
            f" — WARNING: below {_CACHE_HIT_WARN_THRESHOLD:.0%}; "
            "the prompt cache may have regressed (see README 'Cache hit rate')"
        )
    return line


def _call_llm(
    content: str,
    feature_name: str,
    source_summary: str,
    template_type: str,
    augmented_context: str | None = None,
    include_ground_truth_anchor: bool = False,
) -> str:
    """Make the LLM call for polishing.

    Routes through :func:`attune.models.single_turn.call_llm`, which
    prefers the Claude subscription (Agent SDK) when running
    under Claude Code and falls back to the direct Anthropic
    SDK otherwise. Credential handling and error redaction
    stay in one place.

    Args:
        content: Template content to polish.
        feature_name: Feature name for context.
        source_summary: Source code summary.
        template_type: Template kind — selects system prompt.

    Returns:
        Polished content from LLM, or the original content
        when the LLM returned an empty response.

    Raises:
        AnthropicCallError: If no credentials are available
            (neither subscription session nor API key) or the
            LLM call fails on the resolved route.
    """
    system_prompt, user_message = build_polish_prompt(
        content,
        feature_name,
        source_summary,
        template_type,
        augmented_context=augmented_context,
        include_ground_truth_anchor=include_ground_truth_anchor,
    )

    polished = single_turn.call_llm(
        system=system_prompt,
        user_message=user_message,
        model=_polish_model(),
        max_tokens=POLISH_MAX_TOKENS,
        cache_system=POLISH_CACHE_SYSTEM,
        on_cache_usage=_record_cache_usage,
    )
    return polished or content


# Re-export so callers can catch a single exception type
# regardless of whether the failure came from the SDK call
# or from the wrapping polish layer.
__all__ = [
    "AnthropicCallError",
    "PolishCacheStats",
    "PolishError",
    "STRICT_ENV_VAR",
    "_env_strict_default",
    "build_source_summary",
    "clear_cache",
    "format_polish_cache_summary",
    "polish_cache_stats",
    "polish_template",
    "reset_polish_cache_telemetry",
]


#: Character cap for a single return-data block in the polish
#: prompt. Sized to comfortably fit a realistic MCP tool-schema
#: dump (6 tools × ~500 chars ≈ 3.5 KB) with headroom; kept
#: bounded so a pathological literal can't dominate the prompt.
_RETURN_DATA_MAX_CHARS = 8000


def _format_return_data(value: object, indent: int = 0) -> str:
    """Render a literal-return value as indented YAML-like text.

    The output is meant to be fed to the polish LLM as context, so it
    favors compactness and readability over round-trippable syntax.
    Dicts and lists are rendered with two-space indentation; scalars
    use their ``repr``. The whole rendering is length-capped so a
    large tool-schema dict can't dominate the prompt.
    """
    out = _format_return_data_inner(value, indent)
    if len(out) > _RETURN_DATA_MAX_CHARS:
        out = out[:_RETURN_DATA_MAX_CHARS] + "\n... (truncated)"
    return out


def _format_return_data_inner(value: object, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return pad + "{}"
        lines: list[str] = []
        for key, val in value.items():
            if isinstance(val, dict | list):
                lines.append(f"{pad}{key!r}:")
                lines.append(_format_return_data_inner(val, indent + 1))
            else:
                lines.append(f"{pad}{key!r}: {val!r}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return pad + "[]"
        lines = []
        for item in value:
            if isinstance(item, dict | list):
                lines.append(f"{pad}-")
                lines.append(_format_return_data_inner(item, indent + 1))
            else:
                lines.append(f"{pad}- {item!r}")
        return "\n".join(lines)
    return pad + repr(value)


def build_source_summary(
    public_classes: list[dict[str, str]],
    public_functions: list[dict[str, str]],
    module_docstrings: list[str],
    file_count: int,
    function_signatures: list[dict[str, str]] | None = None,
    class_signatures: list[dict[str, str]] | None = None,
    module_constants: list[dict[str, object]] | None = None,
) -> str:
    """Build a concise source summary for the polish prompt.

    Produces a structured summary the LLM can use as an
    accuracy anchor: module purposes, classes, functions,
    and — when available — their signatures. The summary
    is deliberately capped: the prompt context is more
    useful when it fits in a few hundred tokens than when
    it dominates the call.

    Args:
        public_classes: Class dicts with name/doc/file.
            Kept for backward compatibility when the
            signature list is not provided.
        public_functions: Function dicts with name/doc/file.
        module_docstrings: First lines of module docstrings.
        file_count: Total number of source files.
        function_signatures: Optional list of function dicts
            with name/signature/doc/file keys. When provided,
            overrides ``public_functions`` for the Functions
            section to give the LLM argument and return
            type context.
        class_signatures: Optional list of class dicts with
            name/methods/doc/file keys. ``methods`` is a
            newline-separated string of method signatures.
            When provided, augments the Classes section with
            method details.

    Returns:
        Formatted summary string, designed to sit comfortably
        within a single LLM prompt without dominating it.
    """
    parts: list[str] = []

    if module_docstrings:
        parts.append("Module purposes:")
        for doc in module_docstrings[:5]:
            parts.append(f"  - {doc}")

    classes = class_signatures or [
        {"name": c["name"], "doc": c.get("doc", ""), "methods": ""} for c in public_classes
    ]
    if classes:
        parts.append("")
        parts.append("Classes:")
        for cls in classes[:10]:
            parts.extend(_summarize_class(cls))

    functions = function_signatures or [
        {
            "name": f["name"],
            "signature": "",
            "doc": f.get("doc", ""),
        }
        for f in public_functions
    ]
    if functions:
        parts.append("")
        parts.append("Functions:")
        for fn in functions[:10]:
            parts.extend(_summarize_function(fn))

    if module_constants:
        parts.append("")
        parts.append("Module constants (string values; includes underscore-prefixed):")
        for const in module_constants[:20]:
            name = const.get("name", "")
            kind = const.get("kind", "")
            values = const.get("values", [])
            if kind == "str":
                parts.append(f"  - {name} ({kind}) = {values[0]!r}")
            else:
                rendered = ", ".join(repr(v) for v in values)
                parts.append(f"  - {name} ({kind}) = {{{rendered}}}")

    parts.append("")
    parts.append(f"Total source files: {file_count}")

    return "\n".join(parts)


def _summarize_class(cls: dict) -> list[str]:
    """Summary lines for one class entry (see build_source_summary)."""
    lines: list[str] = []
    doc = cls.get("doc", "")
    name = cls["name"]
    dc_tag = " [dataclass]" if cls.get("is_dataclass") else ""
    lines.append(f"  - {name}{dc_tag}" + (f": {doc}" if doc else ""))
    methods = cls.get("methods", "").strip()
    if methods:
        for method_line in methods.splitlines():
            stripped = method_line.strip()
            if stripped:
                lines.append(f"      {stripped}")
    for dc_field in cls.get("dataclass_fields", []) or []:
        field_name = dc_field.get("name", "")
        field_type = dc_field.get("type", "")
        field_default = dc_field.get("default", "")
        line = f"      field: {field_name}"
        if field_type:
            line += f": {field_type}"
        if field_default:
            line += f" = {field_default}"
        lines.append(line)
    for prop in cls.get("properties", []) or []:
        prop_name = prop.get("name", "")
        prop_type = prop.get("return_type", "")
        prop_doc = prop.get("doc", "")
        line = f"      property: {prop_name}"
        if prop_type:
            line += f" -> {prop_type}"
        if prop_doc:
            line += f"  # {prop_doc}"
        lines.append(line)
    return lines


def _summarize_function(fn: dict) -> list[str]:
    """Summary lines for one function entry (see build_source_summary)."""
    lines: list[str] = []
    sig = fn.get("signature", "").strip()
    doc = fn.get("doc", "")
    if sig:
        header = f"  - {sig}"
    else:
        header = f"  - {fn['name']}()"
    if doc:
        header = f"{header} — {doc}"
    lines.append(header)
    for r in fn.get("raises") or []:
        class_name = r.get("class_name", "") if isinstance(r, dict) else r
        message = r.get("message", "") if isinstance(r, dict) else ""
        if message:
            lines.append(f"      raises: {class_name} — {message!r}")
        else:
            lines.append(f"      raises: {class_name}")
    for pname, values in (fn.get("param_literals") or {}).items():
        lines.append(f"      {pname} allowed values: {', '.join(values)}")
    return_data = fn.get("return_data")
    if return_data is not None:
        lines.append("      returns (literal data — render this content in the reference):")
        rendered = _format_return_data(return_data)
        for line in rendered.splitlines():
            lines.append(f"        {line}")
    return lines
