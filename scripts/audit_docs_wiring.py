#!/usr/bin/env python3
"""Documentation wiring audit — v1.1 (anchors + nav + features + mkdocstrings).

Implements Tasks 1 + 2 (v1) and Tasks 3, 4, 9 (v1.1, Phase 4
approved 2026-07-15) of ``docs/specs/docs-wiring-audit/tasks.md``
per the spec's [design.md](../docs/specs/docs-wiring-audit/design.md).

Checks:

- ``anchor`` (Task 2) — every internal ``[text](file.md#anchor)``
  and ``[text](#anchor)`` link resolves to a real heading anchor.
- ``nav`` (Task 3) — every static ``nav:`` entry in mkdocs.yml
  points at an existing file; every built doc (not excluded by
  ``exclude_docs``) is reachable via nav or allowlisted. Paths
  under the ``feature_nav.py`` hook's roots are exempt — that hook
  injects the Features nav section at build time, so they are
  navigable without appearing in the static nav.
- ``features`` (Task 4, adapted 2026-07-15) — every ``_docs`` entry
  in ``.help/features.yaml`` exists on disk (error). The spec's
  original per-feature ``doc_paths`` premise predates the projector
  migration: features are ``status: manual`` and their docs↔feature
  consistency is owned by the projection-drift gate
  (``tests/unit/authoring/test_projection_drift.py``, #1372) — not
  re-checked here.
- ``mkdocstrings`` (Task 9) — every ``::: dotted.path`` directive
  across docs/ resolves against the live package, verified in a
  subprocess so a broken import can't take the audit down.

v1.2 (deferred): reciprocal See-Also advisory.

**Layout deviation from design.md:** the design proposed a
``scripts/audit_docs_wiring/`` package layout. Ships single-file
because (a) it's under the size the package split was meant to
manage, and (b) the existing ``scripts/check_help_coverage.py``
convention matches single-file.

Run:

    python scripts/audit_docs_wiring.py                # all checks
    python scripts/audit_docs_wiring.py --check anchor # one check
    python scripts/audit_docs_wiring.py --format json  # CI-shaped

Exit codes:
    0  — No error-severity findings (warnings are advisory).
    1  — One or more error-severity findings remain (CI fails).
    2  — Bad invocation (unknown check name, malformed allowlist).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

__version__ = "0.1.0"

# ---------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single wiring-audit finding.

    Frozen so callers can put findings in sets / use as dict keys
    without surprise mutation.
    """

    check: str
    severity: str
    file: str
    line: int | None
    message: str
    fix: str | None = None


# ---------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Allowlist:
    """Subtree-level allowlist for orphan checks.

    Per ``docs-wiring-audit/decisions.md`` Q2: entries are
    subtree paths (trailing slash for directories, glob for
    top-level file patterns). Loaded from ``.audit/orphans.yml``;
    each entry MUST have a ``# reason:`` comment on the preceding
    line — enforced at load time.
    """

    orphan_subtrees: tuple[str, ...] = field(default_factory=tuple)

    def is_orphan_exempt(self, path: str) -> bool:
        """True if ``path`` is under any allowlisted subtree."""
        for entry in self.orphan_subtrees:
            if entry.endswith("/") and path.startswith(entry):
                return True
            if "*" in entry:
                # Glob-style match for patterns like docs/BLOG_*.md
                import fnmatch

                if fnmatch.fnmatch(path, entry):
                    return True
            if path == entry:
                return True
        return False


def load_allowlist(path: Path | None = None) -> Allowlist:
    """Load ``.audit/orphans.yml`` with reason-comment enforcement.

    The file format is intentionally a tiny YAML subset (a single
    ``orphan_subtrees:`` list) so we can parse it with stdlib
    line-walking and enforce the reason-comment rule without
    needing a YAML parser dep. Empty / missing file returns an
    empty allowlist.

    Raises:
        ValueError: when any entry lacks a ``# reason:`` comment
            on the immediately preceding non-blank line.
    """
    if path is None:
        path = Path(".audit/orphans.yml")
    if not path.exists():
        return Allowlist()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    entries: list[str] = []
    last_comment: str | None = None
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # blank line — preserve last_comment so a list entry
            # right after blanks still sees its reason
            continue
        if stripped.startswith("#"):
            last_comment = stripped
            continue
        if stripped.startswith("orphan_subtrees:"):
            in_list = True
            continue
        if in_list and stripped.startswith("- "):
            entry = stripped[2:].strip().strip("\"'")
            if last_comment is None or "reason:" not in last_comment.lower():
                raise ValueError(
                    f"Allowlist entry {entry!r} in {path} lacks a "
                    f"'# reason:' comment on the preceding line. "
                    "Every entry requires a reason."
                )
            entries.append(entry)
            last_comment = None  # consumed — next entry needs a fresh one
            continue
        # Anything else (top-level key, malformed line) ends the list block.
        in_list = False

    return Allowlist(orphan_subtrees=tuple(entries))


# ---------------------------------------------------------------------
# Slugify (mirrors Python-Markdown's toc extension default)
# ---------------------------------------------------------------------


def slugify(text: str, separator: str = "-") -> str:
    """Slugify a heading to its anchor form.

    Matches Python-Markdown's ``markdown.extensions.toc.slugify``
    so anchor links in docs resolve the same way mkdocs would
    resolve them at build time. We mirror the algorithm inline
    instead of importing ``markdown`` to keep this script
    stdlib-only.

    Args:
        text: The heading text (without the leading ``#`` markers).
        separator: Separator character used between words.

    Returns:
        Slugified anchor string suitable for ``#anchor`` links.
    """
    # Normalize to NFKD and drop non-ASCII (matches Python-Markdown).
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Strip everything that isn't word-char, whitespace, or dash.
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    # Collapse runs of whitespace OR the separator into a single separator.
    return re.sub(rf"[{re.escape(separator)}\s]+", separator, value)


# ---------------------------------------------------------------------
# Anchor integrity check
# ---------------------------------------------------------------------

# Markdown heading patterns. ATX-style: # / ## / ### headers.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# Inline link: [text](url "optional title"). url captured greedily up
# to the closing paren or whitespace.
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Inline code span — single-backtick-delimited. Used to mask out
# documentation that mentions a link pattern as code without it being
# a real link, e.g. `` `[text](#anchor)` `` in a spec describing the
# syntax. Multi-backtick fenced spans (```) are matched first so they
# don't get partially-consumed by the single-backtick rule.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


# Explicit HTML anchors: <a name="foo"></a> or <a id="foo"></a>. Common
# in legacy markdown where authors wanted stable anchors independent of
# heading text (e.g. emoji-prefixed headings, where the slugify of the
# emoji+text is awkward). Matched both inside and outside headings.
_HTML_ANCHOR_RE = re.compile(r"<a\s+(?:name|id)=[\"']([^\"']+)[\"']", re.I)


def _extract_headings(text: str) -> set[str]:
    """Return the set of anchors (slugified headings + HTML name/id) for a doc.

    Includes:
    - Slugified ATX headings (``# H1``, ``## H2`` …).
    - Explicit HTML anchors anywhere in the document
      (``<a name="foo">`` or ``<a id="foo">``). These let authors
      pin stable anchors that don't depend on heading text.
    """
    anchors: set[str] = set()
    for match in _HEADING_RE.finditer(text):
        heading_text = match.group(2)
        # Strip trailing # marks (e.g. "## Section ##")
        heading_text = re.sub(r"\s+#+\s*$", "", heading_text)
        anchors.add(slugify(heading_text))
    for match in _HTML_ANCHOR_RE.finditer(text):
        anchors.add(match.group(1))
    return anchors


def _compute_line_starts(text: str) -> list[int]:
    """Return byte offsets where each line begins (0-indexed positions).

    Index 0 is always 0; subsequent entries are offsets immediately
    after each ``\\n``. Used by ``_offset_to_line`` for O(log n)
    line-number lookup.
    """
    line_starts = [0]
    for i, char in enumerate(text):
        if char == "\n":
            line_starts.append(i + 1)
    return line_starts


def _offset_to_line(line_starts: list[int], offset: int) -> int:
    """1-indexed line number containing ``offset``.

    Uses binary search over the pre-computed ``line_starts`` list
    (built by ``_compute_line_starts``). Lifted to module scope
    instead of a per-loop closure so ruff's B023 (loop-variable
    capture) doesn't false-positive on the safe inner-loop use.
    """
    return bisect.bisect_right(line_starts, offset)


def _is_external_link(url: str) -> bool:
    """True if the link should be skipped (external, mailto, cross-repo)."""
    if url.startswith(("http://", "https://", "mailto:", "ftp://")):
        return True
    return False


def _resolve_target_file(
    link_url: str,
    source_file: Path,
    docs_root: Path,
) -> Path | None:
    """Resolve ``[text](file.md#anchor)`` to an absolute file path.

    Returns ``None`` for intra-page links (no file part) — caller
    handles those by checking the source file's own headings.
    """
    # Strip the anchor portion to get just the file path.
    file_part = link_url.split("#", 1)[0]
    if not file_part:
        # Intra-page link: [text](#anchor)
        return None
    # Relative to the source file's directory.
    candidate = (source_file.parent / file_part).resolve()
    # Refuse to follow links outside docs/ (e.g. ../../src/foo.py).
    try:
        candidate.relative_to(docs_root.resolve())
    except ValueError:
        return None
    return candidate


def check_anchors(docs_root: Path) -> list[Finding]:
    """Walk docs/**/*.md and verify every internal anchor link resolves.

    Implements design.md §3a. Skips external links and refuses to
    follow links pointing outside ``docs_root``.

    Args:
        docs_root: Path to the docs root (typically ``Path("docs")``).

    Returns:
        List of ``Finding`` records — one per broken anchor.
    """
    findings: list[Finding] = []
    if not docs_root.is_dir():
        return findings

    # Pre-compute heading sets for every .md so we don't re-read.
    heading_cache: dict[Path, set[str]] = {}
    for md in docs_root.rglob("*.md"):
        try:
            heading_cache[md.resolve()] = _extract_headings(md.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            # Skip unreadable files; not a wiring issue.
            continue

    for md in sorted(docs_root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        line_starts = _compute_line_starts(text)
        # Mask out fenced + inline code spans so links inside backticks
        # (e.g. a spec describing the link syntax with ``[text](#anchor)``)
        # don't get matched as real links. We replace with spaces of the
        # same length to preserve byte offsets — line numbers stay correct.
        scan_text = _FENCED_CODE_RE.sub(lambda m: " " * (m.end() - m.start()), text)
        scan_text = _INLINE_CODE_RE.sub(lambda m: " " * (m.end() - m.start()), scan_text)

        for match in _LINK_RE.finditer(scan_text):
            url = match.group(2)
            if _is_external_link(url):
                continue
            if "#" not in url:
                # Not an anchor link; nav/filesystem check (future
                # v1.1 task) handles file-existence verification.
                continue

            anchor = url.split("#", 1)[1]
            if not anchor:
                # [text](file.md#) — empty anchor; skip
                continue

            # Distinguish intra-page (#anchor) from outside-docs
            # (../../src/foo.py#L42). Both are caught by the resolver
            # returning None, but only the former should be checked
            # against the source file's headings.
            file_part = url.split("#", 1)[0]
            target_file = _resolve_target_file(url, md, docs_root)
            if target_file is None and file_part:
                # Resolved file landed outside docs/ — skip; not our scope.
                continue
            if target_file is None:
                # Intra-page anchor — check against this file's headings
                target_anchors = heading_cache.get(md.resolve(), set())
                target_label = str(md.relative_to(docs_root.parent))
            else:
                target_anchors = heading_cache.get(target_file)
                if target_anchors is None:
                    # Link points at a file we couldn't read or that
                    # doesn't exist. Nav-vs-filesystem check (v1.1)
                    # owns file-existence; skip here to avoid double-
                    # reporting.
                    continue
                target_label = str(target_file.relative_to(docs_root.parent.resolve()))

            if anchor in target_anchors:
                continue

            # Build a "did-you-mean" hint listing up to 3 nearby headings.
            sample = sorted(target_anchors)[:5] if target_anchors else []
            hint = (
                f"available anchors in {target_label}: {', '.join(sample)}"
                if sample
                else f"target file has no headings ({target_label})"
            )
            findings.append(
                Finding(
                    check="anchor",
                    severity="error",
                    file=str(md.relative_to(docs_root.parent)),
                    line=_offset_to_line(line_starts, match.start()),
                    message=(f"Link target '#{anchor}' not found in {target_label} " f"({hint})"),
                    fix=(
                        "Update link to match an existing heading, or rename "
                        "the heading and update inbound links (see "
                        "docs-wiring-audit/decisions.md Q1 — update inbound "
                        "links, no redirect)."
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------
# Nav ↔ filesystem check (Task 3)
# ---------------------------------------------------------------------

#: Nav paths injected at build time by docs/hooks/feature_nav.py —
#: pages under this root are navigable without appearing in the
#: static ``nav:`` block.
_HOOK_INJECTED_NAV_ROOTS = ("features/",)

#: Projector-emitted per-feature page kinds. ``<kind>/<feature>.md``
#: pages are reached via their feature hub (docs/features/<feature>.md,
#: which feature_nav.py puts in nav) rather than the static nav — by
#: design (mkdocs.yml exclude_docs D12 note). Exempt them from the
#: orphan check when the stem matches a feature in .help/features.yaml.
_PROJECTOR_KINDS = ("reference", "how-to", "architecture", "tutorials")


def _projector_feature_names(repo_root: Path) -> frozenset[str]:
    """Feature names from ``.help/features.yaml`` (empty set on any failure)."""
    features_path = repo_root / ".help" / "features.yaml"
    if not features_path.exists():
        return frozenset()
    try:
        import yaml

        data = yaml.safe_load(features_path.read_text(encoding="utf-8")) or {}
        return frozenset(data.get("features") or {})
    except Exception:  # noqa: BLE001 — missing yaml / parse error both mean "no exemptions"
        return frozenset()


def _load_mkdocs_config(mkdocs_path: Path) -> dict | None:
    """Parse mkdocs.yml, tolerating mkdocs-material's custom YAML tags.

    Returns ``None`` when the file is missing or PyYAML is
    unavailable — callers surface that as a single advisory finding
    rather than crashing the audit.
    """
    if not mkdocs_path.exists():
        return None
    try:
        import yaml
    except ImportError:
        return None

    class _TagTolerantLoader(yaml.SafeLoader):
        pass

    def _ignore_unknown(loader, tag_suffix, node):  # noqa: ANN001
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        return loader.construct_mapping(node)

    _TagTolerantLoader.add_multi_constructor("", _ignore_unknown)
    _TagTolerantLoader.add_multi_constructor("!", _ignore_unknown)
    _TagTolerantLoader.add_multi_constructor("tag:", _ignore_unknown)
    try:
        return yaml.load(mkdocs_path.read_text(encoding="utf-8"), Loader=_TagTolerantLoader)
    except yaml.YAMLError:
        return None


def _walk_nav_files(nav: object) -> list[str]:
    """Flatten mkdocs' arbitrarily nested nav structure to file paths."""
    files: list[str] = []
    if isinstance(nav, str):
        files.append(nav)
    elif isinstance(nav, list):
        for item in nav:
            files.extend(_walk_nav_files(item))
    elif isinstance(nav, dict):
        for value in nav.values():
            files.extend(_walk_nav_files(value))
    return files


def _exclude_spec(config: dict):
    """Build a matcher for mkdocs' gitignore-style ``exclude_docs`` block.

    Uses ``pathspec`` (mkdocs' own matcher) when available; falls back
    to a coarse prefix/exact matcher on the non-comment lines.
    """
    raw = config.get("exclude_docs") or ""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    try:
        import pathspec

        spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        return spec.match_file
    except ImportError:

        def _coarse(path: str) -> bool:
            return any(
                path == ln
                or (ln.endswith("/") and path.startswith(ln))
                or path.startswith(ln + "/")
                for ln in lines
            )

        return _coarse


def check_nav(docs_root: Path, allowlist: Allowlist | None = None) -> list[Finding]:
    """Verify mkdocs.yml nav entries exist and built docs are navigable.

    Implements Task 3 (design.md §3b). Two directions:

    - Dangling nav entry (points at a missing file) → error.
    - Built doc (not matched by ``exclude_docs``) that is neither in
      the static nav, under a hook-injected nav root, nor allowlisted
      → error.
    """
    allowlist = allowlist or Allowlist()
    findings: list[Finding] = []
    mkdocs_path = docs_root.parent / "mkdocs.yml"
    config = _load_mkdocs_config(mkdocs_path)
    if config is None:
        findings.append(
            Finding(
                check="nav",
                severity="warning",
                file=str(mkdocs_path),
                line=None,
                message="mkdocs.yml missing or unparseable (PyYAML absent?) — nav check skipped",
                fix="Install pyyaml / repair mkdocs.yml so the nav check can run.",
            )
        )
        return findings

    nav_files = set(_walk_nav_files(config.get("nav") or []))
    for entry in sorted(nav_files):
        if not (docs_root / entry).is_file():
            findings.append(
                Finding(
                    check="nav",
                    severity="error",
                    file="mkdocs.yml",
                    line=None,
                    message=f"nav entry '{entry}' points at a missing file",
                    fix="Remove the nav entry or restore the file.",
                )
            )

    is_excluded = _exclude_spec(config)
    feature_names = _projector_feature_names(docs_root.parent)
    for md in sorted(docs_root.rglob("*.md")):
        rel = md.relative_to(docs_root).as_posix()
        if rel in nav_files or is_excluded(rel):
            continue
        if rel.startswith(_HOOK_INJECTED_NAV_ROOTS):
            continue
        parts = rel.split("/")
        if len(parts) == 2 and parts[0] in _PROJECTOR_KINDS and parts[1][:-3] in feature_names:
            continue
        repo_rel = f"{docs_root.name}/{rel}"
        if allowlist.is_orphan_exempt(repo_rel) or allowlist.is_orphan_exempt(rel):
            continue
        findings.append(
            Finding(
                check="nav",
                severity="error",
                file=repo_rel,
                line=None,
                message="built doc is not reachable from nav (orphan)",
                fix=(
                    "Add to mkdocs.yml nav, add to exclude_docs, or allowlist "
                    "in .audit/orphans.yml with a reason."
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------
# features.yaml ↔ filesystem check (Task 4, adapted — see docstring)
# ---------------------------------------------------------------------


def check_features_yaml(docs_root: Path, allowlist: Allowlist | None = None) -> list[Finding]:
    """Verify ``.help/features.yaml`` ``_docs`` entries exist on disk.

    Task 4 adapted 2026-07-15: the per-feature ``doc_paths`` premise
    predates the projector migration (features are ``status: manual``;
    the projection-drift gate owns feature↔doc consistency). What this
    check still owns: every hand-maintained ``_docs`` path must exist
    (a dangling entry silently drops a doc from the help corpus).
    """
    findings: list[Finding] = []
    features_path = docs_root.parent / ".help" / "features.yaml"
    if not features_path.exists():
        return findings
    try:
        import yaml

        data = yaml.safe_load(features_path.read_text(encoding="utf-8")) or {}
    except (ImportError, Exception):  # noqa: BLE001 — yaml.YAMLError subclasses vary
        findings.append(
            Finding(
                check="features",
                severity="warning",
                file=".help/features.yaml",
                line=None,
                message="features.yaml unparseable (or PyYAML absent) — check skipped",
                fix="Repair .help/features.yaml so the check can run.",
            )
        )
        return findings

    for entry in data.get("_docs") or []:
        if not isinstance(entry, str):
            continue
        if not (docs_root.parent / entry).is_file():
            findings.append(
                Finding(
                    check="features",
                    severity="error",
                    file=".help/features.yaml",
                    line=None,
                    message=f"_docs entry '{entry}' points at a missing file",
                    fix="Remove the _docs entry or restore the file.",
                )
            )
    return findings


# ---------------------------------------------------------------------
# mkdocstrings symbol resolution check (Task 9)
# ---------------------------------------------------------------------

_MKDOCSTRINGS_RE = re.compile(r"^:::\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)

#: Batch resolver: reads one dotted path per stdin line, prints one
#: result line per input — ``ok\t<dotted>`` or ``fail\t<dotted>\t<why>``.
#: One subprocess resolves every directive so the interpreter + package
#: import cost is paid once, and a crash mid-batch is recovered by
#: falling back to per-directive resolution for the remainder.
_RESOLVER_SNIPPET = """
import importlib, sys
for raw in sys.stdin:
    dotted = raw.strip()
    if not dotted:
        continue
    parts = dotted.split(".")
    resolved = False
    why = f"no importable module prefix in {dotted!r}"
    for i in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:i]))
        except ImportError:
            continue
        try:
            for attr in parts[i:]:
                obj = getattr(obj, attr)
        except AttributeError as exc:
            why = f"unresolved attribute: {exc}"
            break
        resolved = True
        break
    print(("ok\\t" + dotted) if resolved else ("fail\\t" + dotted + "\\t" + why), flush=True)
"""


def _resolve_directives(dotted_paths: list[str], env: dict[str, str]) -> dict[str, str | None]:
    """Resolve dotted paths in one subprocess; ``None`` = resolved.

    A timeout or crash mid-batch marks every unanswered path as failed
    with the batch error — a hanging import surfaces as findings, never
    as an audit crash.
    """
    import subprocess

    results: dict[str, str | None] = {}
    unique = list(dict.fromkeys(dotted_paths))
    if not unique:
        return results
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _RESOLVER_SNIPPET],
            input="\n".join(unique) + "\n",
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            check=False,
        )
        batch_error = None
        out = proc.stdout
    except subprocess.TimeoutExpired as exc:
        batch_error = "resolver subprocess timed out (hanging import?)"
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")

    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2 and parts[0] in ("ok", "fail"):
            results[parts[1]] = (
                None if parts[0] == "ok" else (parts[2] if len(parts) == 3 else "unresolved")
            )
    for dotted in unique:
        if dotted not in results:
            results[dotted] = batch_error or "resolver subprocess died before answering"
    return results


def check_mkdocstrings(docs_root: Path, allowlist: Allowlist | None = None) -> list[Finding]:
    """Verify every ``::: dotted.path`` directive resolves in src/.

    Implements Task 9 (design.md §4). Directives are resolved in a
    single batched subprocess (interpreter + imports paid once) so a
    directive whose import segfaults, exits, or hangs can't take the
    audit process down. ``src/`` is prepended to PYTHONPATH so the
    in-repo package is what resolves, matching audit_doc_imports.py.
    """
    import os

    findings: list[Finding] = []
    if not docs_root.is_dir():
        return findings

    directives: list[tuple[Path, int, str]] = []
    for md in sorted(docs_root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        line_starts = _compute_line_starts(text)
        for match in _MKDOCSTRINGS_RE.finditer(text):
            directives.append((md, _offset_to_line(line_starts, match.start()), match.group(1)))

    env = dict(os.environ)
    src = str((docs_root.parent / "src").resolve())
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")

    resolution = _resolve_directives([dotted for _, _, dotted in directives], env)
    for md, line, dotted in directives:
        why = resolution.get(dotted)
        if why is None:
            continue
        findings.append(
            Finding(
                check="mkdocstrings",
                severity="error",
                file=str(md.relative_to(docs_root.parent)),
                line=line,
                message=f"mkdocstrings directive '::: {dotted}' does not resolve ({why})",
                fix=(
                    "Fix the dotted path, or delete the directive if the "
                    "symbol was removed (mkdocs build would fail the same way)."
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------


def format_markdown(findings: list[Finding]) -> str:
    """Render findings as a human-readable markdown report."""
    if not findings:
        return "No findings."

    parts: list[str] = ["# Docs wiring audit\n"]
    parts.append(f"Total findings: **{len(findings)}**\n")

    # Group by check.
    by_check: dict[str, list[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    for check, items in sorted(by_check.items()):
        parts.append(f"\n## {check} ({len(items)})\n")
        parts.append("| File | Line | Severity | Message | Fix |")
        parts.append("|---|---|---|---|---|")
        for f in items:
            line_str = str(f.line) if f.line else "—"
            fix_str = f.fix or "—"
            # Escape pipes inside table cells.
            msg = f.message.replace("|", "\\|")
            fix_str = fix_str.replace("|", "\\|")
            parts.append(f"| `{f.file}` | {line_str} | {f.severity} | {msg} | {fix_str} |")

    return "\n".join(parts) + "\n"


def format_json(findings: list[Finding]) -> str:
    """Render findings as JSON for CI consumption."""
    return json.dumps(
        {"findings": [asdict(f) for f in findings]},
        indent=2,
        sort_keys=True,
    )


# ---------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------

CHECKS = {
    "anchor": lambda root, allow: check_anchors(root),
    "nav": check_nav,
    "features": check_features_yaml,
    "mkdocstrings": check_mkdocstrings,
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="audit_docs_wiring",
        description=(
            "Audit docs/ wiring (anchors, nav, features.yaml, "
            "mkdocstrings). v1 ships anchor check; nav + features.yaml "
            "+ mkdocstrings shipped in v1.1; reciprocal See-Also in v1.2."
        ),
    )
    parser.add_argument(
        "--check",
        choices=sorted(CHECKS.keys()) + ["all"],
        default="all",
        help="Which check to run. Default: all available.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path("docs"),
        help="Path to the docs root. Default: docs",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(".audit/orphans.yml"),
        help="Path to the orphan allowlist. Default: .audit/orphans.yml",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    """Top-level entry point. Returns the exit code."""
    args = _parse_args(argv)

    # Allowlist load — fails early on missing reason comments.
    try:
        allowlist = load_allowlist(args.allowlist)
    except ValueError as exc:
        print(f"Allowlist error: {exc}", file=sys.stderr)
        return 2

    # Dispatch.
    requested = sorted(CHECKS.keys()) if args.check == "all" else [args.check]
    all_findings: list[Finding] = []
    for name in requested:
        check_fn = CHECKS[name]
        all_findings.extend(check_fn(args.docs_root, allowlist))

    # Emit.
    if args.format == "json":
        print(format_json(all_findings))
    else:
        print(format_markdown(all_findings))

    # Warnings are advisory (they surface in reports but don't fail
    # CI); only error-severity findings gate.
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    sys.exit(run())
