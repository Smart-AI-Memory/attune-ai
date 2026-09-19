"""Optional read-in-place bridge to the shared Harness memory worker.

Existing writers keep ownership of existing corpora. Their current contracts do
not qualify versioned worker mutations; this adapter never invents that guarantee.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from attune_harness.memory_contract import CLASSIFICATIONS, bounded_json, strings
from attune_harness.review_contract import bounded_text, digest, fields, parse_json, versioned

from attune.memory.file_stash import DEFAULT_TTL_DAYS, FileStashBackend
from attune.memory.personal import PersonalMemory
from attune.memory.session_stash import prepare_strict_content, recall_entries, recent_entries
from attune.security.path_validation import _validate_file_path

FILE_LIMIT = 8 * 1024 * 1024


class CompatibilityAdapter:
    """Read only explicitly authorized roots; never resolve a default backend."""

    def __init__(self, config: dict[str, Any]) -> None:
        bounded_json(config, 65536)
        fields(
            config,
            ("schema_version", "actor", "owners", "scopes", "classifications", "profiles", "roots"),
        )
        versioned(config)
        bounded_text(config["actor"], "actor", 512)
        for name in ("owners", "scopes", "classifications", "profiles"):
            strings(config[name], name, nonempty=True)
        if not set(config["classifications"]) <= set(CLASSIFICATIONS):
            raise ValueError("Unknown security classification")
        if not isinstance(config["roots"], list) or not config["roots"]:
            raise ValueError("At least one explicit memory root is required")
        identities = set()
        for root in config["roots"]:
            fields(root, ("id", "path", "tier", "scope", "owner", "classification"))
            if not isinstance(root["id"], str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,64}", root["id"]
            ):
                raise ValueError("Invalid root identity")
            if root["id"] in identities:
                raise ValueError("Duplicate root identity")
            identities.add(root["id"])
            if root["tier"] not in ("raw", "personal", "curated"):
                raise ValueError("Tier uses its existing governed path; no new adapter capability")
            for field, policy in (
                ("scope", "scopes"),
                ("owner", "owners"),
                ("classification", "classifications"),
            ):
                if root[field] not in config[policy]:
                    raise ValueError("Memory root is outside host authority")
            bounded_text(root["path"], "root path")
            path = Path(root["path"])
            if not path.is_absolute() or path != path.resolve() or path.is_symlink():
                raise ValueError("Memory root must be a canonical absolute path without symlinks")
            _validate_file_path(str(path / ".scope-validation"))
        self.config = deepcopy(config)
        self.binding = digest(config)

    def capabilities(self) -> dict[str, Any]:
        """Disclose new support separately from retained existing operations."""
        return {
            "read": ["raw", "personal", "curated"],
            "worker_mutations": [],
            "mutation_status": "unavailable: legacy writers lack qualified versioned serialization",
            "retained_paths": [
                "keyed working memory",
                "governed persisted patterns",
                "existing memory commands",
            ],
        }

    def _root(self, root_id: str) -> dict[str, Any]:
        if digest(self.config) != self.binding:
            raise ValueError("Adapter authority changed; construct a new adapter")
        for root in self.config["roots"]:
            if root["id"] == root_id:
                return root
        raise ValueError("Unknown root identity")

    def _read(self, root: dict[str, Any], relative: str) -> bytes:
        return self._capture(root, relative)[0]

    def _capture(self, root: dict[str, Any], relative: str) -> tuple[bytes, str, int]:
        path = Path(root["path"])
        child = Path(relative)
        if child.is_absolute() or not child.parts or ".." in child.parts:
            raise ValueError("Source escapes its authorized root")
        target = path / child
        if path != path.resolve() or not path.is_dir():
            raise ValueError("Root changed or unavailable")
        if any(
            parent.is_symlink() for parent in [target, *target.parents] if parent != path.parent
        ):
            raise ValueError("Symlink source is not authorized")
        _validate_file_path(str(target))
        if os.name != "posix":
            raise ValueError("Scoped descriptor reads are currently qualified only on POSIX")
        # Walk every component through held directory descriptors. Checking a
        # path then reopening it by name would permit a symlink-swap escape.
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in (*path.parts[1:], *child.parts[:-1]):
                next_fd = os.open(
                    component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
                )
                os.close(fd)
                fd = next_fd
            source_fd = os.open(
                child.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd
            )
        finally:
            os.close(fd)
        with os.fdopen(source_fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("Source must be a regular file without hard links")
            content = stream.read(FILE_LIMIT + 1)
            after = os.fstat(stream.fileno())
        if len(content) > FILE_LIMIT:
            raise ValueError("Source exceeds read limit; select a narrower source")
        if (before.st_mtime_ns, before.st_ctime_ns, before.st_size) != (
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_size,
        ):
            raise ValueError("Source changed while being read")
        version = digest(
            {
                "sha256": hashlib.sha256(content).hexdigest(),
                "device": after.st_dev,
                "inode": after.st_ino,
                "mtime_ns": after.st_mtime_ns,
                "ctime_ns": after.st_ctime_ns,
                "size": after.st_size,
            }
        )
        return content, version, after.st_mtime_ns

    def _sidecars(self, root: dict[str, Any]) -> dict[str, tuple[bytes, str, int]]:
        result = {}
        for name in ("summaries_by_path.json", ".verdicts.jsonl"):
            try:
                result[name] = self._capture(root, name)
            except FileNotFoundError:
                result[name] = (b"", "absent", 0)
        return result

    def _document_version(
        self, source_version: str, sidecars: dict[str, tuple[bytes, str, int]]
    ) -> str:
        return digest(
            {
                "source": source_version,
                "sidecars": {key: value[1] for key, value in sidecars.items()},
            }
        )

    def _documents(self, root: dict[str, Any], query: str, k: int) -> list[dict[str, Any]]:
        # The existing RAG service opens its own files. Supply a bounded private
        # snapshot of descriptor-checked bytes so it cannot follow a later swap
        # outside the authorized root. Originals remain in place and unchanged.
        path = Path(root["path"])
        sources: dict[str, tuple[bytes, str, int]] = {}
        total = 0
        with tempfile.TemporaryDirectory(prefix="attune-memory-query-") as temporary:
            snapshot = Path(temporary)
            sidecars = self._sidecars(root)
            for name, (data, token, _) in sidecars.items():
                total += len(data)
                if token != "absent":
                    _validate_file_path(str(snapshot / name)).write_bytes(data)
            for index, source in enumerate(path.glob("**/*.md")):
                if index >= 4096:
                    raise ValueError("Corpus exceeds snapshot file limit; narrow the root")
                relative = source.relative_to(path).as_posix()
                raw, version, mtime_ns = self._capture(root, relative)
                total += len(raw)
                if total > 64 * 1024 * 1024:
                    raise ValueError("Corpus exceeds 64 MiB query snapshot limit; narrow the root")
                sources[relative] = (raw, version, mtime_ns)
                target = _validate_file_path(str(snapshot / relative))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                # Age and content come from the same held source descriptor.
                os.utime(target, ns=(mtime_ns, mtime_ns))
            memory = PersonalMemory(global_root=snapshot, project_root=snapshot)
            items = []
            hits = memory.query(query, k=k, strict=True)
            if self._sidecars(root) != sidecars:
                raise ValueError("Retrieval metadata changed; refresh context")
            for hit in hits:
                raw, version, mtime_ns = sources[hit["path"]]
                if self._capture(root, hit["path"]) != (raw, version, mtime_ns):
                    raise ValueError("Source changed during retrieval; refresh context")
                items.append(
                    self._item(
                        root,
                        {"path": hit["path"]},
                        raw,
                        raw.decode("utf-8"),
                        Path(hit["path"]).stem,
                        hit,
                        self._document_version(version, sidecars),
                    )
                )
            return items

    def _raw(self, root: dict[str, Any]) -> tuple[bytes, dict[str, dict[str, Any]], str]:
        source = Path(root["path"]) / "findings.jsonl"
        if not source.exists():
            return b"", {}, "absent"
        content, version, _ = self._capture(root, "findings.jsonl")
        rows = {}
        for line in content.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = parse_json(line, FILE_LIMIT)
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("id"), str)
                or not row["id"]
                or row["id"] in rows
            ):
                raise ValueError("Malformed or duplicate raw identity; exact retrieval unavailable")
            if not isinstance(row.get("text"), str) or not isinstance(row.get("topics", []), list):
                raise ValueError("Malformed raw record")
            rows[row["id"]] = row
        return content, rows, version

    def _item(
        self,
        root: dict[str, Any],
        locator: dict[str, str],
        raw: bytes,
        text: str,
        kind: str,
        metadata: dict[str, Any],
        version: str,
    ) -> dict[str, Any]:
        # Guard every surfaced metadata string as well as full source text.
        def guard(value: Any, label: str = "metadata") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    guard(str(key), "metadata_key")
                    guard(child, str(key))
            elif isinstance(value, list):
                for child in value:
                    guard(child, label)
            elif isinstance(value, str):
                candidate = label + "=" + value
                if prepare_strict_content(candidate, max_chars=None) != candidate:
                    raise ValueError(
                        "Source is unsafe or requires redaction; governed exposure refused"
                    )

        guard(text, "content")
        guard(metadata)
        labels = metadata
        normalized = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        if root["tier"] != "raw" and re.match(r"---[ \t]*\n", normalized):
            import yaml

            header = re.split(r"(?m)^---[ \t]*$", normalized, maxsplit=2)
            if len(header) != 3:
                raise ValueError("Unterminated source security metadata")
            try:
                labels = yaml.safe_load(header[1])
            except yaml.YAMLError as error:
                raise ValueError("Unreadable source security metadata") from error
            if labels is not None and not isinstance(labels, dict):
                raise ValueError("Source security metadata must be an object")
        if isinstance(labels, dict):
            for key in ("owner", "scope", "classification"):
                if key in labels and labels[key] != root[key]:
                    raise ValueError("Source security metadata conflicts with root authority")
        return {
            "id": root["id"] + ":" + next(iter(locator.values())),
            "locator": {"root_id": root["id"], **locator},
            "version": version,
            "authority": self.binding,
            "text": text,
            "kind": kind,
            "metadata": deepcopy(metadata),
            "scope": root["scope"],
            "owner": root["owner"],
            "classification": root["classification"],
        }

    def _raw_items(self, root: dict[str, Any], query: str) -> list[dict[str, Any]]:
        items = []
        before, rows, version = self._raw(root)
        with tempfile.TemporaryDirectory(prefix="attune-memory-raw-") as temporary:
            snapshot = _validate_file_path(str(Path(temporary) / "findings.jsonl"))
            snapshot.write_bytes(before)
            backend = FileStashBackend(base_dir=temporary)
            hits = (
                recall_entries(query, top_k=max(1, len(rows)), backend=backend)
                if query.strip()
                else recent_entries(top_k=max(1, len(rows)), backend=backend)
            )
        for hit in hits:
            row = rows.get(hit["id"])
            if row is None or row.get("cwd") != root["scope"]:
                continue
            kinds = [
                t[5:] for t in row.get("topics", []) if isinstance(t, str) and t.startswith("type:")
            ]
            items.append(
                self._item(
                    root,
                    {"record_id": row["id"]},
                    before,
                    row["text"],
                    kinds[0] if len(kinds) == 1 else "unknown",
                    row,
                    version,
                )
            )
        if self._raw(root)[2] != version:
            raise ValueError("Raw source changed during retrieval")
        return items

    def query(self, query: str, *, k: int = 10) -> dict[str, Any]:
        """Return explicit partial/unavailable/empty states and full scoped sources."""
        if not isinstance(query, str) or type(k) is not int or not 1 <= k <= 100:
            raise ValueError("Invalid memory query or result bound")
        items, problems = [], []
        for declared in self.config["roots"]:
            root = self._root(declared["id"])
            path = Path(root["path"])
            try:
                if not path.is_dir():
                    raise FileNotFoundError("Explicit memory root is unavailable")
                if root["tier"] == "raw":
                    items.extend(self._raw_items(root, query))
                else:
                    # RAG must not read an escaping symlink before resolution checks.
                    if path != path.resolve() or any(p.is_symlink() for p in path.rglob("*")):
                        raise ValueError("Document corpus contains symlinks")
                    items.extend(self._documents(root, query, k))
            except (OSError, ValueError, ImportError) as error:
                # Expected filesystem, content and optional-dependency failures
                # degrade this root; programming defects propagate to the host.
                # Discard this root's partial results; other authorized roots survive.
                items = [item for item in items if item["locator"]["root_id"] != root["id"]]
                problems.append(
                    {"root_id": root["id"], "reason": type(error).__name__, "detail": str(error)}
                )
        state = (
            ("partial" if items else "unavailable")
            if problems
            else ("available" if items else "empty")
        )
        return {
            "status": state,
            "items": items[:k],
            "problems": problems,
            "authority": self.binding,
            "capabilities": self.capabilities(),
        }

    def resolve(self, handle: dict[str, Any]) -> dict[str, Any]:
        """Resolve current full content only when scope and source version still match."""
        if handle.get("authority") != self.binding:
            raise ValueError("Foreign or stale source authority")
        locator = handle["locator"]
        root = self._root(locator["root_id"])
        if root["tier"] == "raw":
            fields(locator, ("root_id", "record_id"))
            raw, rows, version = self._raw(root)
            row = rows[locator["record_id"]]
            if float(row.get("ts", 0) or 0) < time.time() - DEFAULT_TTL_DAYS * 86400:
                raise ValueError("Raw source expired; refresh context")
            if row.get("cwd") != root["scope"]:
                raise ValueError("Raw source scope changed")
            kinds = [
                t[5:] for t in row.get("topics", []) if isinstance(t, str) and t.startswith("type:")
            ]
            item = self._item(
                root,
                {"record_id": row["id"]},
                raw,
                row["text"],
                kinds[0] if len(kinds) == 1 else "unknown",
                row,
                version,
            )
        else:
            fields(locator, ("root_id", "path"))
            raw, version, _ = self._capture(root, locator["path"])
            item = self._item(
                root,
                {"path": locator["path"]},
                raw,
                raw.decode("utf-8"),
                Path(locator["path"]).stem,
                {},
                self._document_version(version, self._sidecars(root)),
            )
        if item["version"] != handle["version"] or item["id"] != handle["id"]:
            raise ValueError("Source was corrected, deleted or replaced; refresh context")
        return item

    def apply(self, *args: Any, **kwargs: Any) -> None:
        """Refuse unqualified worker effects without touching any existing corpus."""
        raise ValueError(
            "Worker mutations unavailable for legacy stores; use existing governed memory commands"
        )
