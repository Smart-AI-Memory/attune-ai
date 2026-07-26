#!/usr/bin/env python3
"""Capability count projector (roundtable q-capability-count-projector-001).

Derives exactly three semantic values from the checked-out revision and
projects them into an explicit, frozen allowlist of claim sites:

- ``skill_count`` — publishable skills under ``plugin/skills/*/SKILL.md``.
- ``mcp_registered_tool_count`` — unique names in
  ``EmpathyMCPServer().tools`` (includes bundled plugin tools).
- ``mcp_core_schema_tool_count`` — unique names returned by the
  canonical ``attune.mcp.tool_schemas.get_*_tools()`` getters.

No network data, cached counts, caller overrides, remembered constants,
or anticipated capabilities. Empty, duplicate, malformed, or
environment-dependent discovery fails closed. The independent drift
gates (``tests/unit/gates/test_claim_drift.py``,
``tests/unit/test_website_version_accuracy.py``) deliberately do NOT
share this module's derivation or manifest.

Ownership model
---------------

- **Markdown** owns complete, uniquely marked claim fragments — never
  isolated numbers. The marker grammar is a one-line span::

      <!-- cap:VALUE -->fragment with the number<!-- /cap -->

  Every marked span in a governed file must be claimed by exactly one
  manifest target; stray, unclosed, unknown-value, or ambiguous
  markers fail closed.
- **JSON** (``.claude-plugin/marketplace.json``) is parsed as JSON; only
  the exact allowlisted description fields are rewritten. JSON receives
  no comment markers.
- **TypeScript** (``website/lib/features.ts``) updates exact named
  numeric fields inside the existing ``CAPABILITIES`` object. No
  generated JSON sidecar.

Usage::

    python scripts/project_capabilities.py           # read-only check
    python scripts/project_capabilities.py --check   # same as default
    python scripts/project_capabilities.py --write   # repair drift

Exit codes: 0 clean, 1 drift (check mode), 2 structural/derivation
failure or bad usage. ``--write`` computes and validates the complete
edit plan before touching any file, writes atomically per file, then
reruns the check from disk. A repeated ``--write`` is byte-idempotent.

Capability-changing PRs (adding/removing a plugin skill or MCP tool)
run ``--write`` in the same change; CI runs ``--check``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

VALUE_NAMES = (
    "skill_count",
    "mcp_registered_tool_count",
    "mcp_core_schema_tool_count",
)


class ProjectionError(RuntimeError):
    """Structural failure — fail closed, never write."""


# --- Derivation --------------------------------------------------------

# Provider packages that live in this repository. If one is importable
# it must resolve to THIS checkout, or the derived counts describe some
# other revision's tool set.
_IN_REPO_PACKAGES = (("attune", "src/attune"), ("attune_redis", "attune_redis"))


def _prepend_repo_paths(repo: Path) -> None:
    """Self-heal import resolution: front the repo's own package roots.

    ``sys.path`` entries beat the editable-install finder (it sits
    behind PathFinder on ``sys.meta_path``), so fronting ``repo/src``
    and ``repo`` makes a worktree run measure the tree it was pointed
    at instead of whichever checkout the editable install maps to.
    """
    root = repo.resolve()
    for entry in (str(root), str(root / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def _assert_in_repo_imports(repo: Path) -> None:
    """Imported in-repo provider packages must resolve to this checkout.

    Running the script as a file puts ``scripts/`` (not the repo root)
    at ``sys.path[0]``, so ``import attune_redis`` can silently fall
    through to another checkout via the editable install and register a
    different plugin tool set. The core-subset guard cannot catch that
    (core ⊆ registered still holds), so fail closed here instead.
    """
    root = repo.resolve()
    for pkg, rel in _IN_REPO_PACKAGES:
        if not (repo / rel).is_dir():
            continue
        module = sys.modules.get(pkg)
        if module is None:
            continue
        origin = getattr(module, "__file__", None)
        if origin is None:
            paths = list(getattr(module, "__path__", None) or [])
            origin = paths[0] if paths else None
        if origin is None:
            raise ProjectionError(f"cannot locate the imported {pkg!r} package — failing closed")
        if not Path(origin).resolve().is_relative_to(root):
            raise ProjectionError(
                f"imported {pkg!r} resolves to {origin}, outside the repo root "
                f"{root} — wrong-checkout registration; rerun with "
                f"PYTHONPATH={root}:{root / 'src'}"
            )


def derive_values(repo: Path) -> dict[str, int]:
    """Derive the three semantic values from the checked-out revision.

    Raises ProjectionError on any empty, duplicate, or inconsistent
    discovery — a count from an unstable environment is never published.
    """
    skill_files = sorted((repo / "plugin" / "skills").glob("*/SKILL.md"))
    if not skill_files:
        raise ProjectionError(
            f"no plugin/skills/*/SKILL.md found under {repo} — refusing to publish 0"
        )

    _prepend_repo_paths(repo)
    try:
        from attune.mcp import tool_schemas
        from attune.mcp.server import EmpathyMCPServer
    except ImportError as exc:
        raise ProjectionError(
            f"attune is not importable ({exc}) — run from the project environment"
        ) from exc
    if (repo / "attune_redis").is_dir():
        # Import explicitly (not just via the server's best-effort plugin
        # hook) so the provenance guard below can never silently skip it.
        try:
            import attune_redis  # noqa: F401
        except ImportError as exc:
            raise ProjectionError(
                f"in-repo attune_redis is not importable ({exc}) — its plugin "
                "tools would be silently missing from the count"
            ) from exc

    tools = EmpathyMCPServer().tools
    if not isinstance(tools, dict) or not tools:
        raise ProjectionError(
            "EmpathyMCPServer().tools is not a non-empty dict — unstable registration"
        )
    registered = set(tools)
    _assert_in_repo_imports(repo)

    getter_names = sorted(
        n for n in dir(tool_schemas) if n.startswith("get_") and n.endswith("_tools")
    )
    if not getter_names:
        raise ProjectionError("no get_*_tools() getters found in attune.mcp.tool_schemas")
    core: set[str] = set()
    for name in getter_names:
        schemas = getattr(tool_schemas, name)()
        if not isinstance(schemas, dict) or not schemas:
            raise ProjectionError(f"tool_schemas.{name}() returned a non-dict or empty result")
        dupes = core & set(schemas)
        if dupes:
            raise ProjectionError(
                f"duplicate tool names across get_*_tools() getters: {sorted(dupes)}"
            )
        core.update(schemas)

    if not core <= registered:
        raise ProjectionError(
            "core schema tools missing from the registered server "
            f"({sorted(core - registered)}) — environment-dependent registration, failing closed"
        )
    return {
        "skill_count": len(skill_files),
        "mcp_registered_tool_count": len(registered),
        "mcp_core_schema_tool_count": len(core),
    }


# --- Target manifest ---------------------------------------------------
#
# Every entry declares the semantic value it publishes, an exact
# locator, its renderer (via the dataclass type), expected match
# cardinality, and gets post-render validation in its planner.


@dataclass(frozen=True)
class MarkedFragmentTarget:
    """Markdown target: whole fragments wrapped in ownership markers.

    The projector owns every ``<!-- cap:VALUE -->…<!-- /cap -->`` span
    whose inner text matches ``template`` (which contains exactly one
    ``{n}`` placeholder; everything else is literal). ``count`` is the
    expected number of such spans in the file.
    """

    path: str
    label: str
    value: str
    template: str
    count: int = 1


@dataclass(frozen=True)
class JsonFieldTarget:
    """JSON target: one allowlisted string field, located by path.

    ``json_path`` elements are dict keys, except a (key, value) tuple
    which selects exactly one entry from a list. Only the located field
    is rewritten; the file's bytes are otherwise preserved and the
    result is re-validated as JSON.
    """

    path: str
    label: str
    value: str
    json_path: tuple = ()
    fragment: str = ""


@dataclass(frozen=True)
class TsCapabilityTarget:
    """features.ts target: one named numeric field inside CAPABILITIES."""

    path: str
    label: str
    value: str
    ts_field: str = ""


MANIFEST: tuple = (
    # skill_count
    MarkedFragmentTarget(
        "README.md",
        "comparison table skills row",
        "skill_count",
        "{n} auto-triggering skills",
    ),
    MarkedFragmentTarget(
        "plugin/README.md",
        "intro + comparison table skills claims",
        "skill_count",
        "{n} auto-triggering skills",
        count=2,
    ),
    MarkedFragmentTarget(
        "docs/getting-started/quickstart-plugin.md",
        "bold skills claim",
        "skill_count",
        "**{n} auto-triggering skills**",
    ),
    MarkedFragmentTarget(
        "docs/getting-started/quickstart-plugin.md",
        "plugin-vs-package skills note",
        "skill_count",
        "{n} natural-language skills",
    ),
    JsonFieldTarget(
        ".claude-plugin/marketplace.json",
        "marketplace metadata description",
        "skill_count",
        json_path=("metadata", "description"),
        fragment="{n} auto-triggering skills",
    ),
    JsonFieldTarget(
        ".claude-plugin/marketplace.json",
        "attune-ai plugin description",
        "skill_count",
        json_path=("plugins", ("name", "attune-ai"), "description"),
        fragment="{n} auto-triggering skills",
    ),
    TsCapabilityTarget(
        "website/lib/features.ts",
        "CAPABILITIES.skills",
        "skill_count",
        ts_field="skills",
    ),
    # mcp_registered_tool_count (total including bundled plugin tools)
    MarkedFragmentTarget(
        "README.md",
        "hero + comparison table tool counts",
        "mcp_registered_tool_count",
        "{n} MCP tools",
        count=2,
    ),
    MarkedFragmentTarget(
        "plugin/README.md",
        "intro + comparison table tool counts",
        "mcp_registered_tool_count",
        "{n} MCP tools",
        count=2,
    ),
    MarkedFragmentTarget(
        "docs/getting-started/quickstart-plugin.md",
        "MCP toolset link row",
        "mcp_registered_tool_count",
        "({n} tools)",
    ),
    MarkedFragmentTarget(
        "docs/getting-started/quickstart-plugin.md",
        "plugin-vs-package tools note",
        "mcp_registered_tool_count",
        "{n} MCP tools",
    ),
    MarkedFragmentTarget(
        "docs/getting-started/mcp-integration.md",
        "available tools heading",
        "mcp_registered_tool_count",
        "Available Tools ({n})",
    ),
    # mcp_core_schema_tool_count (canonical tool_schemas getters only)
    TsCapabilityTarget(
        "website/lib/features.ts",
        "CAPABILITIES.mcpTools",
        "mcp_core_schema_tool_count",
        ts_field="mcpTools",
    ),
)


# --- Planning ----------------------------------------------------------

MARKER_RE = re.compile(r"<!-- cap:([a-z_]+) -->(.*?)<!-- /cap -->")
MARKER_TOKEN_RE = re.compile(r"<!-- /?cap\b")


@dataclass
class FilePlan:
    """One governed file: original text, fully rendered text, drift."""

    path: str
    original: str
    new_text: str
    drifts: list[str]

    @property
    def changed(self) -> bool:
        return self.new_text != self.original


def _read(repo: Path, rel: str) -> str:
    path = (repo / rel).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ProjectionError(f"target escapes the repository root: {rel}")
    if not path.is_file():
        raise ProjectionError(f"target file missing: {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.read()


def _template_pattern(template: str) -> re.Pattern[str]:
    parts = template.split("{n}")
    if len(parts) != 2:
        raise ProjectionError(f"template must contain exactly one {{n}}: {template!r}")
    return re.compile(re.escape(parts[0]) + r"(\d+)" + re.escape(parts[1]))


def _render(template: str, expected: int) -> str:
    return template.replace("{n}", str(expected))


def _splice(text: str, spans: list[tuple[int, int]], replacement: str) -> str:
    out, last = [], 0
    for start, end in spans:
        out.append(text[last:start])
        out.append(replacement)
        last = end
    out.append(text[last:])
    return "".join(out)


def _scan_marked_spans(path_label: str, text: str) -> list[re.Match[str]]:
    """All well-formed one-line marker spans; stray tokens fail closed."""
    spans = list(MARKER_RE.finditer(text))
    for token in MARKER_TOKEN_RE.finditer(text):
        if not any(m.start() <= token.start() < m.end() for m in spans):
            line = text.count("\n", 0, token.start()) + 1
            raise ProjectionError(
                f"{path_label}: malformed or unclosed capability marker at line {line}"
            )
    return spans


def _validate_marker_coverage(
    path_label: str, text: str, targets: list[MarkedFragmentTarget]
) -> None:
    """Every marked span is claimed by exactly one manifest target."""
    for span in _scan_marked_spans(path_label, text):
        value, inner = span.group(1), span.group(2)
        claimants = [
            t
            for t in targets
            if t.value == value and _template_pattern(t.template).fullmatch(inner)
        ]
        if not claimants:
            line = text.count("\n", 0, span.start()) + 1
            raise ProjectionError(
                f"{path_label}: marker cap:{value} at line {line} with content "
                f"{inner!r} is claimed by no manifest target — unknown value, "
                "renamed claim, or wrong fragment shape"
            )
        if len(claimants) > 1:
            labels = ", ".join(repr(t.label) for t in claimants)
            raise ProjectionError(
                f"{path_label}: marker cap:{value} content {inner!r} is claimed "
                f"by {len(claimants)} targets ({labels}) — ambiguous ownership"
            )


def _plan_marked(target: MarkedFragmentTarget, text: str, expected: int) -> tuple[str, list[str]]:
    where = f"{target.path}: {target.label}"
    pattern = _template_pattern(target.template)
    mine = [
        m
        for m in _scan_marked_spans(target.path, text)
        if m.group(1) == target.value and pattern.fullmatch(m.group(2))
    ]
    if len(mine) != target.count:
        raise ProjectionError(
            f"{where}: {len(mine)} marked span(s) match template "
            f"{target.template!r}, expected {target.count} — the claim moved, "
            "vanished, or became ambiguous; fix the manifest WITH the wording"
        )
    observed = [m.group(2) for m in mine]
    new_inner = _render(target.template, expected)
    new_text = _splice(text, [m.span(2) for m in mine], new_inner)
    rendered = [
        m.group(2)
        for m in MARKER_RE.finditer(new_text)
        if m.group(1) == target.value and pattern.fullmatch(m.group(2))
    ]
    if rendered != [new_inner] * target.count:
        raise ProjectionError(f"{where}: post-render validation failed")
    drifts = []
    if any(inner != new_inner for inner in observed):
        drifts.append(
            f"{target.path}: {target.label} publishes {target.value} — expected "
            f"{new_inner!r}, observed {', '.join(repr(o) for o in observed)}"
        )
    return new_text, drifts


def _resolve_json_field(data: object, json_path: tuple, where: str) -> str:
    node = data
    for step in json_path:
        if isinstance(step, tuple):
            key, value = step
            if not isinstance(node, list):
                raise ProjectionError(f"{where}: selector {step!r} applied to non-list")
            hits = [e for e in node if isinstance(e, dict) and e.get(key) == value]
            if len(hits) != 1:
                raise ProjectionError(
                    f"{where}: selector {step!r} matched {len(hits)} entries, expected 1"
                )
            node = hits[0]
        else:
            if not isinstance(node, dict) or step not in node:
                raise ProjectionError(f"{where}: key {step!r} not found")
            node = node[step]
    if not isinstance(node, str):
        raise ProjectionError(f"{where}: located field is {type(node).__name__}, expected string")
    return node


def _plan_json(target: JsonFieldTarget, text: str, expected: int) -> tuple[str, list[str]]:
    where = f"{target.path}: {target.label}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"{where}: invalid JSON ({exc})") from exc
    old_field = _resolve_json_field(data, target.json_path, where)
    pattern = _template_pattern(target.fragment)
    matches = list(pattern.finditer(old_field))
    if len(matches) != 1:
        raise ProjectionError(
            f"{where}: fragment /{pattern.pattern}/ matched {len(matches)} "
            "time(s) in the field, expected 1"
        )
    observed = matches[0].group(0)
    rendered = _render(target.fragment, expected)
    new_field = _splice(old_field, [matches[0].span()], rendered)
    if new_field == old_field:
        return text, []

    old_encoded = json.dumps(old_field, ensure_ascii=False)
    if text.count(old_encoded) != 1:
        raise ProjectionError(
            f"{where}: JSON-encoded field value occurs {text.count(old_encoded)} "
            "time(s) in the raw file, expected 1 — cannot rewrite unambiguously"
        )
    new_text = text.replace(old_encoded, json.dumps(new_field, ensure_ascii=False), 1)
    # Post-render validation: still valid JSON, and only the owned field moved.
    try:
        new_data = json.loads(new_text)
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"{where}: rewrite produced invalid JSON ({exc})") from exc
    if _resolve_json_field(new_data, target.json_path, where) != new_field:
        raise ProjectionError(f"{where}: rewrite did not land in the owned field")
    drift = (
        f"{target.path}: {target.label} publishes {target.value} — expected "
        f"{rendered!r}, observed {observed!r}"
    )
    return new_text, [drift]


CAPS_BLOCK = re.compile(r"export const CAPABILITIES = \{(.*?)\} as const;", re.S)


def _plan_ts(target: TsCapabilityTarget, text: str, expected: int) -> tuple[str, list[str]]:
    where = f"{target.path}: {target.label}"
    blocks = list(CAPS_BLOCK.finditer(text))
    if len(blocks) != 1:
        raise ProjectionError(f"{where}: found {len(blocks)} CAPABILITIES blocks, expected 1")
    block = blocks[0]
    field_pattern = re.compile(r"\b" + re.escape(target.ts_field) + r"\s*:\s*(\d+)")
    matches = list(field_pattern.finditer(text, block.start(1), block.end(1)))
    if len(matches) != 1:
        raise ProjectionError(
            f"{where}: field {target.ts_field!r} matched {len(matches)} "
            "time(s) inside CAPABILITIES, expected 1"
        )
    observed = matches[0].group(1)
    new_text = _splice(text, [matches[0].span(1)], str(expected))
    new_blocks = list(CAPS_BLOCK.finditer(new_text))
    if len(new_blocks) != 1:
        raise ProjectionError(f"{where}: post-render validation failed (CAPABILITIES block)")
    check = list(field_pattern.finditer(new_text, new_blocks[0].start(1), new_blocks[0].end(1)))
    if len(check) != 1 or check[0].group(1) != str(expected):
        raise ProjectionError(f"{where}: post-render validation failed")
    drifts = []
    if observed != str(expected):
        drifts.append(
            f"{target.path}: {target.label} publishes {target.value} — expected "
            f"'{target.ts_field}: {expected}', observed '{target.ts_field}: {observed}'"
        )
    return new_text, drifts


_PLANNERS = {
    MarkedFragmentTarget: _plan_marked,
    JsonFieldTarget: _plan_json,
    TsCapabilityTarget: _plan_ts,
}


def build_plan(repo: Path, values: dict[str, int], manifest: tuple | None = None) -> list[FilePlan]:
    """Validate every target and render each file's new content — no writes.

    Targets on the same file are applied sequentially to the evolving
    text, so one file plan carries every claim it owns. Raises
    ProjectionError on the first structural problem so that one invalid
    target prevents every planned write.
    """
    if manifest is None:
        manifest = MANIFEST
    by_path: dict[str, list] = {}
    for target in manifest:
        by_path.setdefault(target.path, []).append(target)

    plans: list[FilePlan] = []
    for path, targets in by_path.items():
        original = _read(repo, path)
        marked = [t for t in targets if isinstance(t, MarkedFragmentTarget)]
        if marked:
            _validate_marker_coverage(path, original, marked)
        current, drifts = original, []
        for target in targets:
            if target.value not in values:
                raise ProjectionError(
                    f"{target.path}: {target.label!r} names unknown value {target.value!r}"
                )
            current, target_drifts = _PLANNERS[type(target)](target, current, values[target.value])
            drifts.extend(target_drifts)
        plans.append(FilePlan(path, original, current, drifts))
    return plans


def drift_lines(plans: list[FilePlan]) -> list[str]:
    return [line for plan in plans for line in plan.drifts]


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_name(path.name + ".capproj-tmp")
    try:
        fh = tmp.open("x", encoding="utf-8", newline="")
    except FileExistsError as exc:
        raise ProjectionError(
            f"stale temp file {tmp} already exists (crashed prior write?) — "
            "inspect and remove it, then re-run"
        ) from exc
    try:
        with fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def apply_plan(repo: Path, plans: list[FilePlan]) -> list[str]:
    """Atomically write every changed file; returns the changed paths."""
    changed: list[str] = []
    root = repo.resolve()
    for plan in plans:
        if plan.changed:
            path = (repo / plan.path).resolve()
            if not path.is_relative_to(root):
                raise ProjectionError(f"target escapes the repository root: {plan.path}")
            if not path.is_file():
                raise ProjectionError(f"target file missing: {path}")
            _atomic_write(path, plan.new_text)
            changed.append(plan.path)
    return changed


# --- CLI ---------------------------------------------------------------


def main(argv: list[str] | None = None, repo: Path | None = None) -> int:
    """Run the projector CLI; ``repo`` overrides the root for tests."""
    parser = argparse.ArgumentParser(
        description="Project derived capability counts into their allowlisted claim sites.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="read-only drift check (the default)")
    group.add_argument("--write", action="store_true", help="repair drift, then re-check")
    args = parser.parse_args(argv)

    if repo is None:
        repo = Path(__file__).resolve().parents[1]
    try:
        values = derive_values(repo)
        plans = build_plan(repo, values)
    except ProjectionError as exc:
        print(f"projection failed closed: {exc}", file=sys.stderr)
        return 2

    for name in VALUE_NAMES:
        print(f"{name} = {values[name]}")
    drift = drift_lines(plans)

    if not args.write:
        if drift:
            print("\nDRIFT:", file=sys.stderr)
            for line in drift:
                print(f"  {line}", file=sys.stderr)
            print("\nrun: python scripts/project_capabilities.py --write", file=sys.stderr)
            return 1
        print("all capability claims match the derived values")
        return 0

    if not drift:
        print("all capability claims already match — nothing to write")
        return 0
    try:
        changed = apply_plan(repo, plans)
    except ProjectionError as exc:
        print(f"write failed closed: {exc}", file=sys.stderr)
        return 2
    for line in drift:
        print(f"repaired: {line}")
    print(f"wrote {len(changed)} file(s): {', '.join(changed)}")
    try:
        recheck = build_plan(repo, values)
    except ProjectionError as exc:
        print(f"post-write re-check failed closed: {exc}", file=sys.stderr)
        return 2
    if drift_lines(recheck):
        print("post-write re-check still reports drift", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
