"""Personal cross-session memory backed by attune-author polish + attune-rag retrieval.

Captures session decisions, patterns, troubleshooting findings, and
reference material as polished markdown in ``~/.attune/memory/<topic>/<kind>.md``.
Retrieves them in future sessions via attune-rag's keyword pipeline.

Both attune-author and attune-rag are optional at import time — missing deps
degrade gracefully so Stop hook calls never crash.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from attune.memory.curated_audit import (
    format_age_annotation,
    format_status_annotation,
    load_memory,
    resolve_age_basis,
    unverified_age_days,
)

logger = logging.getLogger(__name__)

_GLOBAL_ROOT = Path.home() / ".attune" / "memory"
_SUMMARIES_FILE = "summaries_by_path.json"

#: Topic slug validation — rejects path traversal before any I/O.
_TOPIC_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,49}$")


def _load_author() -> Any:
    """Lazy-import attune.authoring.polish.polish_template, or None."""
    try:
        from attune.authoring.polish import polish_template  # noqa: PLC0415

        return polish_template
    except Exception:  # noqa: BLE001
        return None


def _load_rag() -> Any:
    """Lazy-import attune_rag pipeline + corpus, or None."""
    try:
        from attune_rag.corpus.directory import DirectoryCorpus  # noqa: PLC0415
        from attune_rag.pipeline import RagPipeline  # noqa: PLC0415

        return DirectoryCorpus, RagPipeline
    except Exception:  # noqa: BLE001
        return None


def _build_skeleton(topic: str, kind: str, content: str) -> str:
    """Build a raw markdown skeleton for the given kind without Jinja2."""
    if kind == "decision":
        return (
            f"# {topic}\n\n"
            f"## Decision\n\n"
            f"{content}\n\n"
            f"## Alternatives considered\n\n"
            f"_List rejected alternatives and one-line reasons._\n\n"
            f"## Context\n\n"
            f"_Constraints or assumptions that made this choice reasonable._\n\n"
            f"## Revisit when\n\n"
            f"_Conditions that would make this decision wrong._\n"
        )
    if kind == "pattern":
        return (
            f"# {topic}\n\n"
            f"## Problem\n\n"
            f"{content}\n\n"
            f"## When to apply\n\n"
            f"_Trigger condition — when to use vs. when NOT to use._\n\n"
            f"## Example\n\n"
            f"```\n_Minimal copy-pasteable example._\n```\n\n"
            f"## Anti-pattern\n\n"
            f"_The wrong approach this replaces, and why it fails._\n"
        )
    if kind == "troubleshooting":
        return (
            f"# {topic}\n\n"
            f"## Symptoms\n\n"
            f"{content}\n\n"
            f"## Diagnosis steps\n\n"
            f"_Ordered cheapest-first: reproduction → logging → code._\n\n"
            f"## Fix\n\n"
            f"_Concrete commands or code changes that resolve the issue._\n"
        )
    # reference
    return (
        f"# {topic}\n\n"
        f"## Overview\n\n"
        f"{content}\n\n"
        f"## Quick reference\n\n"
        f"_API signatures, commands, or config snippets._\n"
    )


def _secret_gate(content: str) -> str:
    """Refuse to capture curated content carrying a secret (R2). Fail closed.

    The curated write path polishes content through an LLM before writing, so a
    secret here would leak to the polish provider *and* land in plaintext
    markdown + Redis. This gates the raw input up front — before any network
    call — mirroring the raw tier's ``session_stash._sanitize``.

    Unlike the raw hook path (which returns None to skip a best-effort write),
    ``capture`` is a deliberate action, so a detected secret RAISES: the caller
    must know their content was refused and rotate the exposed value (deletion
    is insufficient — see the spec). PII is redacted in place, not blocked.

    Args:
        content: Raw content passed to :meth:`PersonalMemory.capture`.

    Returns:
        The content with PII redacted.

    Raises:
        SecurityError: If a critical/high-severity secret is detected, or if
            the gate itself is unavailable (fail closed — never write
            unscanned).
    """
    try:
        from attune.memory.short_term.security import DataSanitizer
    except ImportError as exc:
        raise RuntimeError(f"secret gate unavailable; refusing capture: {exc}") from exc

    sanitizer = DataSanitizer(pii_scrub_enabled=True, secrets_detection_enabled=True)
    sanitized, redactions = sanitizer.sanitize(content)  # raises SecurityError on secrets
    if redactions:
        logger.info("personal_memory: %d PII value(s) redacted before capture", redactions)
    return sanitized if isinstance(sanitized, str) else str(sanitized)


def _extract_summary(text: str) -> str:
    """Return first non-heading, non-blank, non-frontmatter line ≤ 120 chars."""
    in_frontmatter = False
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:120]
    return ""


class PersonalMemory:
    """Store and retrieve personal cross-session memory.

    Args:
        global_root: Root for global (user-wide) memory.
            Defaults to ``~/.attune/memory/``.
        project_root: Root for project-local memory.
            Defaults to ``.attune/memory/`` if it exists, else ``None``.
    """

    VALID_KINDS = frozenset({"decision", "pattern", "troubleshooting", "reference"})

    def __init__(
        self,
        global_root: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._global_root: Path = global_root or _GLOBAL_ROOT
        _project_default = Path.cwd() / ".attune" / "memory"
        self._project_root: Path | None = project_root or (
            _project_default if _project_default.is_dir() else None
        )
        # When cwd is the home directory, the project default resolves to
        # the global root itself — scanning it twice duplicates every hit.
        if (
            self._project_root is not None
            and self._project_root.resolve() == self._global_root.resolve()
        ):
            self._project_root = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(
        self,
        topic: str,
        content: str,
        kind: str = "decision",
        strict_polish: bool = False,
        project_local: bool = False,
    ) -> Path:
        """Capture content as a polished memory document.

        Args:
            topic: Slug identifying the memory topic (``auth-architecture``).
            content: Raw content to capture and polish.
            kind: One of ``decision``, ``pattern``, ``troubleshooting``,
                ``reference``.
            strict_polish: If ``True``, raise on polish failure instead of
                falling back to the raw skeleton.
            project_local: Write to ``.attune/memory/`` instead of global root.

        Returns:
            Path to the written markdown file.

        Raises:
            ValueError: If ``topic`` or ``kind`` is invalid.
        """
        if not _TOPIC_RE.match(topic):
            raise ValueError(
                f"Invalid topic slug {topic!r}. "
                "Use only [a-zA-Z0-9_-], 1-50 chars, starting with alphanumeric."
            )
        if kind not in self.VALID_KINDS:
            raise ValueError(f"Unknown kind {kind!r}. Valid kinds: {sorted(self.VALID_KINDS)}")

        content = _secret_gate(content)

        root = self._project_root if project_local else self._global_root

        skeleton = _build_skeleton(topic, kind, content)
        grounded = self._ground_personal(skeleton, root)
        polished = self._polish(grounded, kind, strict_polish)

        dest = root / topic / f"{kind}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(dest, polished)
        self._update_summaries(root, dest, polished)

        logger.info("personal_memory_captured topic=%s kind=%s path=%s", topic, kind, dest)
        return dest

    def query(
        self,
        query: str,
        k: int = 3,
        kind_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the most relevant memory entries for a query.

        Merges global and project-local corpora; project entries win on
        tied scores.

        Args:
            query: Natural-language retrieval query.
            k: Maximum number of results.
            kind_filter: If set, limit results to this kind.

        Returns:
            List of dicts with keys ``path``, ``summary``, ``excerpt``,
            ``score``.
        """
        rag = _load_rag()
        if rag is None:
            logger.warning("personal_memory_rag_unavailable")
            return []

        DirectoryCorpus, RagPipeline = rag

        hits: list[dict[str, Any]] = []

        for root, is_project in [
            (self._project_root, True),
            (self._global_root, False),
        ]:
            if root is None or not root.is_dir():
                continue
            try:
                corpus = DirectoryCorpus(
                    root,
                    summaries_file=_SUMMARIES_FILE,
                    glob="**/*.md",
                )
                pipeline = RagPipeline(corpus=corpus)
                rag_result = pipeline.run(query, k=k * 2)
                for hit in rag_result.citation.hits:
                    path_str = hit.template_path
                    if kind_filter and not path_str.endswith(f"/{kind_filter}.md"):
                        continue
                    hits.append(
                        {
                            "path": path_str,
                            "summary": hit.excerpt or "",
                            "excerpt": hit.excerpt or "",
                            "score": hit.score + (0.001 if is_project else 0.0),
                        }
                    )
            except Exception:  # noqa: BLE001
                logger.warning("personal_memory_query_failed root=%s", root)

        # Dedup by path (keep best score) — two roots can surface the same
        # relative path, and returning it twice is useless to the caller.
        best: dict[str, dict[str, Any]] = {}
        for hit in hits:
            prior = best.get(hit["path"])
            if prior is None or hit["score"] > prior["score"]:
                best[hit["path"]] = hit

        deduped = sorted(best.values(), key=lambda h: h["score"], reverse=True)
        results = deduped[:k]
        self._annotate_staleness(results)
        self._stamp_provenance(results)
        # P3 task 2: per-stem serve telemetry — the R6 frequency term's
        # data source. Best-effort; stems only, never content.
        try:
            from attune.memory.serve_telemetry import log_curated_recall  # noqa: PLC0415

            log_curated_recall(
                [Path(str(hit.get("path", ""))).stem for hit in results],
                surface="personal_query",
            )
        except ImportError:
            # The emitter itself never raises (fail-open by contract);
            # only a broken import can escape, and telemetry must never
            # cost the caller their recall results.
            logger.debug("curated serve telemetry unavailable")
        return results

    def _stamp_provenance(self, hits: list[dict[str, Any]]) -> None:
        """Attach R1 provenance + instruction flags to each hit, in place.

        Curated memories are human-authored, so they carry more standing than
        raw findings — but the linter checks format, not content, so
        attacker-shaped prose can still reach recall (memory-security-hardening
        R1). Stamping tier/source/author and flagging instruction-shaped text
        lets a reading session weigh a recalled item without re-deriving its
        origin. Labels only — never reorders or drops (D1 of
        memory-status-integrity holds here too).
        """
        from attune.memory.provenance import AUTHOR_CURATED, provenance_fields

        for hit in hits:
            try:
                text = str(hit.get("excerpt") or hit.get("summary") or "")
                hit["provenance"] = provenance_fields(
                    tier="curated",
                    source=str(hit.get("path", "curated")),
                    author_class=AUTHOR_CURATED,
                    text=text,
                )
            except (KeyError, TypeError, ValueError):
                logger.debug("provenance stamp failed path=%s", hit.get("path"))

    def _annotate_staleness(self, hits: list[dict[str, Any]]) -> None:
        """Add unverified-age to each hit, in place.

        Per ``docs/specs/memory-status-integrity`` R2, a reader must see how
        long it has been since a claim was confirmed without having to ask.
        The annotation only labels — it never reorders or drops a hit, which
        would violate D1 (label, never suppress by age).

        Failures are swallowed: a missing file or unreadable stat must not
        cost the caller their recall results. The handler is narrow on
        purpose — ``load_memory`` already absorbs its own I/O errors, so the
        only escapes left here are a malformed hit dict or a path the OS
        refuses. Catching broadly would add a site to the shrink-only
        broad-except ratchet for no coverage gain.
        """
        for hit in hits:
            try:
                path = self._resolve_hit_path(hit["path"])
                if path is None:
                    continue
                mem = load_memory(path)
                latest = self._latest_verdict_for(mem)
                days = unverified_age_days(mem, latest_verdict=latest)
                _, basis = resolve_age_basis(mem, latest)
                hit["unverified_days"] = days
                hit["staleness"] = format_age_annotation(days)
                # P2 task 8: the calibrated tier label (settled /
                # check-before-acting / suspect) — a number without a base
                # rate is not a signal a reading model can act on.
                hit["status"] = format_status_annotation(mem.mem_type, basis, days)
            except (KeyError, OSError, ValueError):
                logger.debug("staleness_annotation_failed path=%s", hit.get("path"))

    def _latest_verdict_for(self, mem: Any) -> Any:
        """The memory's latest verdict from its corpus root's log, if any.

        Best-effort — a missing or unreadable log reads as unbound, which
        is the honest default the audit side already uses.
        """
        from attune.memory.verdict_log import latest_verdicts

        for root in (self._project_root, self._global_root):
            if root is not None and root in mem.path.parents:
                return latest_verdicts(root).get(mem.stem)
        return None

    def _resolve_hit_path(self, path_str: str) -> Path | None:
        """Resolve a corpus-relative hit path against the known roots."""
        for root in (self._project_root, self._global_root):
            if root is None:
                continue
            candidate = root / path_str
            if candidate.is_file():
                return candidate
        return None

    def list_topics(self) -> list[str]:
        """Return sorted list of topic slugs across global and project memory."""
        topics: set[str] = set()
        for root in [self._global_root, self._project_root]:
            if root is None or not root.is_dir():
                continue
            for p in root.iterdir():
                if p.is_dir() and _TOPIC_RE.match(p.name):
                    topics.add(p.name)
        return sorted(topics)

    def forget_topic(self, topic: str, kind: str | None = None) -> int:
        """Delete memory entries for a topic.

        Args:
            topic: Topic slug to delete.
            kind: If set, delete only this kind file; otherwise delete the
                entire topic directory.

        Returns:
            Number of files deleted.

        Raises:
            ValueError: If ``topic`` or ``kind`` is invalid.
        """
        if not _TOPIC_RE.match(topic):
            raise ValueError(
                f"Invalid topic slug {topic!r}. "
                "Use only [a-zA-Z0-9_-], 1-50 chars, starting with alphanumeric."
            )
        if kind is not None and kind not in self.VALID_KINDS:
            raise ValueError(f"Unknown kind {kind!r}. Valid kinds: {sorted(self.VALID_KINDS)}")
        deleted = 0
        for root in [self._global_root, self._project_root]:
            if root is None or not root.is_dir():
                continue
            topic_dir = root / topic
            if not topic_dir.is_dir():
                continue
            if kind is not None:
                target = topic_dir / f"{kind}.md"
                if target.exists():
                    target.unlink()
                    self._remove_from_summaries(root, target)
                    deleted += 1
            else:
                for f in topic_dir.glob("*.md"):
                    self._remove_from_summaries(root, f)
                    deleted += 1
                shutil.rmtree(topic_dir, ignore_errors=True)
        return deleted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ground_personal(self, skeleton: str, root: Path) -> str:
        """Query personal corpus for context to inject into the polish prompt.

        Returns skeleton unchanged when RAG is unavailable or the corpus
        is empty.
        """
        if not root.is_dir():
            return skeleton

        rag = _load_rag()
        if rag is None:
            return skeleton

        DirectoryCorpus, RagPipeline = rag
        try:
            corpus = DirectoryCorpus(root, summaries_file=_SUMMARIES_FILE, glob="**/*.md")
            if sum(1 for _ in corpus.entries()) == 0:
                return skeleton
            # Just return skeleton; grounding context is informational
            # for the polish call but we don't inject it into the text
        except Exception:  # noqa: BLE001
            pass
        return skeleton

    def _polish(self, text: str, kind: str, strict: bool) -> str:
        """Run attune-author polish pass, degrading gracefully on failure."""
        polish_fn = _load_author()
        if polish_fn is None:
            return text
        try:
            # polish_template(content, feature_name, source_summary, ...):
            # the two positionals are required — omitting them raised
            # TypeError on every call, silently killing the polish pass
            # (library-review M2). Personal memories have no feature or
            # source summary, so pass empty strings.
            result = polish_fn(text, "", "", template_type=kind)
            if not result:
                return text
            if not result.endswith("\n"):
                result += "\n"
            return result
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise
            logger.warning("personal_memory_polish_failed: %s", exc)
            return text

    def _atomic_write_text(self, dest: Path, text: str) -> None:
        """Write text atomically using a temp file + Path.replace()."""
        tmp = dest.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(dest)

    def _update_summaries(self, root: Path, path: Path, text: str) -> None:
        """Upsert the path-keyed summaries_by_path.json sidecar."""
        sidecar = root / _SUMMARIES_FILE
        summaries: dict[str, str] = {}
        if sidecar.exists():
            try:
                summaries = json.loads(sidecar.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                summaries = {}

        key = path.relative_to(root).as_posix()
        summaries[key] = _extract_summary(text)

        tmp = sidecar.with_suffix(".tmp")
        tmp.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(sidecar)

    def _remove_from_summaries(self, root: Path, path: Path) -> None:
        """Remove a path key from the summaries sidecar if present."""
        sidecar = root / _SUMMARIES_FILE
        if not sidecar.exists():
            return
        try:
            summaries = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        key = path.relative_to(root).as_posix()
        if key in summaries:
            summaries.pop(key)
            tmp = sidecar.with_suffix(".tmp")
            tmp.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(sidecar)
