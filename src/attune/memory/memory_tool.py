"""Anthropic Memory-tool backend over attune's MemoryBackend.

Implements Anthropic's client-side **Memory tool** (``memory_20250818``)
on top of attune's existing memory backends (the file backend by
default, ``attune_redis.AMSMemoryBackend`` when AMS is configured).

Anthropic's Memory tool is file-addressed: the model issues
``view`` / ``create`` / ``str_replace`` / ``insert`` / ``delete`` /
``rename`` commands against a ``/memories`` directory, and the host
implements the storage. This adapter maps that file model onto the
``MemoryBackend`` key/value surface — a memory file *path* becomes a
backend *key* (prefixed so memory-tool files are enumerable), and the
file *content* is the stored value. The result: the same durable,
optionally-Redis-backed store that powers attune's SessionStart recall
also serves Anthropic's native memory interface.

Pass an instance to the Anthropic SDK's ``tool_runner`` (or call
``execute``/``call`` directly) to give an agent a ``/memories``
directory persisted on attune's backend.

See ``docs/specs/anthropic-memory-tool-backend/`` for the design.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from anthropic.types.beta import (
        BetaMemoryTool20250818CreateCommand,
        BetaMemoryTool20250818DeleteCommand,
        BetaMemoryTool20250818InsertCommand,
        BetaMemoryTool20250818RenameCommand,
        BetaMemoryTool20250818StrReplaceCommand,
        BetaMemoryTool20250818ViewCommand,
    )

    from .backend import MemoryBackend

logger = logging.getLogger(__name__)

#: Virtual root the Anthropic Memory tool addresses files under.
_DEFAULT_ROOT = "/memories"

#: Backend-key prefix so memory-tool files are enumerable (``view`` of a
#: directory) and distinct from other ``stash`` keys in the same namespace.
_KEY_PREFIX = "memtool"


def _import_base() -> type:
    """Import ``BetaAbstractMemoryTool`` lazily.

    Kept out of module import so ``attune.memory`` stays importable when an
    older ``anthropic`` without the memory-tool helper is installed; the
    factory raises a clear error only when the bridge is actually used.
    """
    try:
        from anthropic.lib.tools import BetaAbstractMemoryTool
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "Anthropic Memory-tool bridge requires the `anthropic` SDK with "
            "memory-tool support (anthropic.lib.tools.BetaAbstractMemoryTool)."
        ) from exc
    return BetaAbstractMemoryTool


class _PathError(ValueError):
    """Raised for an invalid/unsafe memory path (caught, returned as text)."""


def _normalize_path(path: str, root: str) -> str:
    """Validate a Memory-tool path and return its root-relative form.

    Args:
        path: The model-supplied path (e.g. ``/memories/notes/todo.md``).
        root: The virtual root (default ``/memories``).

    Returns:
        The path relative to ``root`` with no leading slash (``""`` for the
        root itself).

    Raises:
        _PathError: On null bytes, traversal (``..``), or a path outside root.
    """
    if not isinstance(path, str) or "\x00" in path:
        raise _PathError("path must be a non-empty string without null bytes")
    cleaned = path.strip()
    if not cleaned.startswith(root):
        # Tolerate paths given relative to the root, too.
        rel = cleaned.lstrip("/")
    else:
        rel = cleaned[len(root) :].lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise _PathError(f"path traversal is not allowed: {path!r}")
    return "/".join(parts)


def _with_line_numbers(text: str) -> str:
    """Render file content with 1-indexed line numbers (Memory-tool view)."""
    lines = text.splitlines()
    width = len(str(len(lines))) if lines else 1
    return "\n".join(f"{i:>{width}}\t{line}" for i, line in enumerate(lines, 1))


class AttuneMemoryTool:  # mixed with BetaAbstractMemoryTool in __new__
    """Anthropic Memory tool backed by an attune ``MemoryBackend``.

    Example::

        from attune.memory.memory_tool import AttuneMemoryTool
        from attune.memory.file_stash import FileStashBackend

        tool = AttuneMemoryTool(FileStashBackend())
        # pass `tool` to anthropic tool_runner, or:
        tool.execute(create_command)
    """

    def __init__(
        self,
        backend: MemoryBackend,
        *,
        root: str = _DEFAULT_ROOT,
        user_id: str | None = None,
    ) -> None:
        """Initialize the bridge.

        Args:
            backend: Any attune ``MemoryBackend`` (file by default, AMS when
                configured). Provides ``stash``/``retrieve``/``keys``/``delete``.
            root: Virtual root the model addresses files under.
            user_id: When set, namespaces keys so memory is per-user.
        """
        # BetaAbstractMemoryTool.__init__ takes no args; call it via super
        # through the dynamically-composed class (see __init_subclass shim).
        super().__init__()  # type: ignore[misc]
        self._backend = backend
        self._root = root.rstrip("/") or "/"
        self._user_id = user_id

    # -- key mapping ------------------------------------------------------ #

    def _key(self, rel: str) -> str:
        """Backend key for a root-relative memory path."""
        scope = self._user_id or "_"
        return f"{_KEY_PREFIX}:{scope}:{rel}"

    def _key_prefix(self, rel: str = "") -> str:
        """Backend-key glob for enumerating files under a relative dir."""
        scope = self._user_id or "_"
        base = f"{_KEY_PREFIX}:{scope}:{rel}".rstrip(":")
        return f"{base}*" if not rel else f"{base}/*"

    def _read(self, rel: str) -> str | None:
        val = self._backend.retrieve(self._key(rel))
        if val is None:
            return None
        return val if isinstance(val, str) else str(val)

    # -- the six Memory-tool commands ------------------------------------ #

    def view(self, command: BetaMemoryTool20250818ViewCommand) -> str:
        """Read a file (optionally a line range) or list a directory."""
        try:
            rel = _normalize_path(command.path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        text = self._read(rel)
        if text is not None:
            view_range = getattr(command, "view_range", None)
            if view_range:
                lines = text.splitlines()
                start, end = view_range[0], view_range[1]
                end = len(lines) if end == -1 else end
                start = max(1, start)
                sliced = lines[start - 1 : end]
                width = len(str(end)) if end else 1
                return "\n".join(f"{i:>{width}}\t{ln}" for i, ln in enumerate(sliced, start))
            return _with_line_numbers(text)
        # Not a file — treat as a directory listing under the prefix.
        prefix = f"{_KEY_PREFIX}:{self._user_id or '_'}:"
        try:
            all_keys = self._backend.keys(self._key_prefix(rel))
        except Exception as e:  # noqa: BLE001 - best-effort listing
            logger.error("memory_tool view list failed: %s", e)
            return f"Error: could not list {command.path}"
        entries = sorted(k[len(prefix) :] for k in all_keys if k.startswith(prefix))
        if not entries:
            return f"Error: path not found: {command.path}"
        listing = "\n".join(f"{self._root}/{e}" for e in entries)
        return f"Directory {command.path}:\n{listing}"

    def create(self, command: BetaMemoryTool20250818CreateCommand) -> str:
        """Create (or overwrite) a memory file."""
        try:
            rel = _normalize_path(command.path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        if not rel:
            return "Error: cannot create the root directory as a file"
        ok = self._backend.stash(self._key(rel), command.file_text)
        return f"Created {command.path}" if ok else f"Error: write failed: {command.path}"

    def str_replace(self, command: BetaMemoryTool20250818StrReplaceCommand) -> str:
        """Replace the first occurrence of ``old_str`` with ``new_str``."""
        try:
            rel = _normalize_path(command.path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        text = self._read(rel)
        if text is None:
            return f"Error: path not found: {command.path}"
        if command.old_str not in text:
            return f"Error: no match for old_str in {command.path}"
        updated = text.replace(command.old_str, command.new_str, 1)
        ok = self._backend.stash(self._key(rel), updated)
        return f"Edited {command.path}" if ok else f"Error: write failed: {command.path}"

    def insert(self, command: BetaMemoryTool20250818InsertCommand) -> str:
        """Insert text after the given (1-indexed) line."""
        try:
            rel = _normalize_path(command.path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        text = self._read(rel)
        if text is None:
            return f"Error: path not found: {command.path}"
        lines = text.splitlines()
        at = command.insert_line
        if at < 0 or at > len(lines):
            return f"Error: insert_line {at} out of range for {command.path}"
        new_lines = lines[:at] + command.insert_text.splitlines() + lines[at:]
        ok = self._backend.stash(self._key(rel), "\n".join(new_lines))
        return f"Inserted into {command.path}" if ok else f"Error: write failed: {command.path}"

    def delete(self, command: BetaMemoryTool20250818DeleteCommand) -> str:
        """Delete a memory file."""
        try:
            rel = _normalize_path(command.path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        ok = self._backend.delete(self._key(rel))
        return f"Deleted {command.path}" if ok else f"Error: path not found: {command.path}"

    def rename(self, command: BetaMemoryTool20250818RenameCommand) -> str:
        """Rename/move a memory file (copy then delete)."""
        try:
            old_rel = _normalize_path(command.old_path, self._root)
            new_rel = _normalize_path(command.new_path, self._root)
        except _PathError as e:
            return f"Error: {e}"
        text = self._read(old_rel)
        if text is None:
            return f"Error: path not found: {command.old_path}"
        if self._read(new_rel) is not None:
            return f"Error: destination exists: {command.new_path}"
        if not self._backend.stash(self._key(new_rel), text):
            return f"Error: write failed: {command.new_path}"
        self._backend.delete(self._key(old_rel))
        return f"Renamed {command.old_path} to {command.new_path}"

    def clear_all_memory(self) -> None:
        """Delete every memory-tool file for this scope (best-effort)."""
        prefix = f"{_KEY_PREFIX}:{self._user_id or '_'}:"
        try:
            for k in self._backend.keys(self._key_prefix()):
                if k.startswith(prefix):
                    self._backend.delete(k)
        except Exception as e:  # noqa: BLE001 - best-effort teardown
            logger.error("memory_tool clear_all failed: %s", e)


def make_memory_tool(
    backend: MemoryBackend | None = None,
    *,
    root: str = _DEFAULT_ROOT,
    user_id: str | None = None,
) -> Any:
    """Build an Anthropic Memory-tool instance backed by an attune backend.

    Composes ``AttuneMemoryTool`` with the SDK's ``BetaAbstractMemoryTool``
    at call time (so importing this module never requires the SDK helper),
    and resolves a default backend when none is given.

    Args:
        backend: An attune ``MemoryBackend``. Defaults to the resolved
            backend (file by default; AMS when configured).
        root: Virtual root the model addresses files under.
        user_id: When set, namespaces memory per-user.

    Returns:
        A ``BetaAbstractMemoryTool`` subclass instance ready to pass to the
        Anthropic SDK ``tool_runner``.
    """
    base = _import_base()

    # Compose the concrete tool with the SDK's abstract base. The handler
    # bodies live on AttuneMemoryTool; the base supplies execute/call/name.
    composed = type("AttuneMemoryTool", (AttuneMemoryTool, base), {})

    if backend is None:
        from .session_stash import resolve_backend

        backend = resolve_backend(None)
        if backend is None:  # pragma: no cover - depends on environment
            raise RuntimeError("no memory backend available")

    return composed(backend, root=root, user_id=user_id)


__all__ = ["AttuneMemoryTool", "make_memory_tool"]
