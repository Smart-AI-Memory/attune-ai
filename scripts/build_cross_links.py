#!/usr/bin/env python3
"""Build cross-link index between generated templates.

Creates deterministic relationships:
  - Error <-> Warning (same slug from same Lessons Learned entry)
  - Skill -> Tool (tool names found in SKILL.md body)
  - Tool -> Skill (inverse of above)
  - Error -> Tip (2+ non-stopword token overlap in titles)
  - All -> Tags (tag index for search/filtering)

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/build_cross_links.py           # Generate
    python scripts/build_cross_links.py --check   # Verify
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

# Stopwords to skip in title overlap matching
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "and",
        "or",
        "not",
        "no",
        "but",
        "if",
        "when",
        "with",
        "from",
        "by",
        "as",
        "its",
        "it",
        "this",
        "that",
        "can",
        "will",
        "do",
        "has",
        "have",
        "had",
        "may",
        "must",
        "should",
        "would",
        "could",
    }
)


@dataclass
class TemplateEntry:
    """Parsed template metadata from frontmatter."""

    template_id: str
    type: str
    name: str
    title: str
    tags: list[str] = field(default_factory=list)
    subtype: str = ""
    category: str = ""


def _parse_template(filepath: Path) -> TemplateEntry | None:
    """Parse a template file's frontmatter.

    Args:
        filepath: Path to a generated template .md file.

    Returns:
        TemplateEntry or None if parsing fails.
    """
    try:
        post = frontmatter.load(str(filepath))
    except Exception:  # noqa: BLE001
        # INTENTIONAL: skip unparseable files
        return None

    ttype = post.get("type", "")
    name = post.get("name", filepath.stem)
    tags_raw = post.get("tags", [])

    # Tags may be a list or a comma-separated string
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",")]
    else:
        tags = list(tags_raw)

    # Extract title from first # heading
    title = ""
    for line in post.content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return TemplateEntry(
        template_id=f"{ttype[:3]}-{name}" if ttype else name,
        type=ttype,
        name=name,
        title=title,
        tags=tags,
        subtype=post.get("subtype", ""),
        category=post.get("category", ""),
    )


def _discover_templates(
    generated_dir: Path,
) -> dict[str, list[TemplateEntry]]:
    """Discover all generated templates by type.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Dict mapping type name to list of entries.
    """
    result: dict[str, list[TemplateEntry]] = {}

    for type_dir in sorted(generated_dir.iterdir()):
        if not type_dir.is_dir():
            continue

        entries: list[TemplateEntry] = []
        for md_file in sorted(type_dir.glob("*.md")):
            entry = _parse_template(md_file)
            if entry:
                entries.append(entry)

        if entries:
            result[type_dir.name] = entries

    return result


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase non-stopword tokens.

    Args:
        text: Input text.

    Returns:
        Set of meaningful tokens.
    """
    words = set()
    for word in text.lower().split():
        # Strip punctuation
        clean = word.strip(":`'\"-(),./\\[]{}!?;")
        if clean and clean not in _STOPWORDS and len(clean) > 2:
            words.add(clean)
    return words


def _build_error_warning_links(
    errors: list[TemplateEntry],
    warnings: list[TemplateEntry],
) -> dict[str, dict]:
    """Build Error <-> Warning links by matching slugs.

    Args:
        errors: Error template entries.
        warnings: Warning template entries.

    Returns:
        Dict of template_id -> link data.
    """
    links: dict[str, dict] = {}

    warning_by_name = {w.name: w for w in warnings}

    for err in errors:
        if err.name in warning_by_name:
            warn = warning_by_name[err.name]
            err_id = f"err-{err.name}"
            warn_id = f"war-{warn.name}"

            links.setdefault(err_id, {})["related_warning"] = [warn_id]
            links.setdefault(warn_id, {})["related_error"] = [err_id]

    return links


def _build_skill_tool_links(
    references: list[TemplateEntry],
) -> dict[str, dict]:
    """Build Skill -> Tool and Tool -> Skill links.

    Skill references with subtype=procedural may have
    tool references in their Related Topics. Tool
    references get inverse links.

    Args:
        references: Reference template entries.

    Returns:
        Dict of template_id -> link data.
    """
    links: dict[str, dict] = {}

    skills = [r for r in references if r.category == "skill"]
    tools = {r.name.replace("tool-", ""): r for r in references if r.category == "tool"}

    # Read skill files to find tool references
    repo_root = Path(__file__).resolve().parent.parent
    for skill in skills:
        skill_file = repo_root / "plugin" / "skills" / skill.name.replace("skill-", "") / "SKILL.md"
        if not skill_file.exists():
            continue

        body = skill_file.read_text(encoding="utf-8")
        skill_id = f"ref-{skill.name}"
        found_tools: list[str] = []

        for tool_name in tools:
            if tool_name in body:
                tool_id = f"ref-tool-{tool_name}"
                found_tools.append(tool_id)

                # Inverse link: tool -> skill
                links.setdefault(tool_id, {}).setdefault(
                    "referenced_by_skills",
                    [],
                ).append(skill_id)

        if found_tools:
            links.setdefault(skill_id, {})["references_tools"] = found_tools

    return links


def _build_error_tip_links(
    errors: list[TemplateEntry],
    tips: list[TemplateEntry],
) -> dict[str, dict]:
    """Build Error -> Tip links by title token overlap.

    Links errors to tips when 2+ non-stopword tokens
    overlap between their titles.

    Args:
        errors: Error template entries.
        tips: Tip template entries.

    Returns:
        Dict of template_id -> link data.
    """
    links: dict[str, dict] = {}

    tip_tokens = [(t, _tokenize(t.title)) for t in tips]

    for err in errors:
        err_tokens = _tokenize(err.title)
        err_id = f"err-{err.name}"

        for tip, tokens in tip_tokens:
            overlap = err_tokens & tokens
            if len(overlap) >= 2:
                tip_id = f"tip-{tip.name}"
                links.setdefault(err_id, {}).setdefault(
                    "prevented_by",
                    [],
                ).append(tip_id)

    return links


def _build_tag_index(
    all_templates: dict[str, list[TemplateEntry]],
) -> dict[str, list[str]]:
    """Build tag -> template_id index.

    Args:
        all_templates: Dict of type -> entries.

    Returns:
        Dict of tag -> list of template_ids.
    """
    index: dict[str, list[str]] = {}

    prefix_map = {
        "errors": "err",
        "warnings": "war",
        "tips": "tip",
        "references": "ref",
    }

    for type_name, entries in all_templates.items():
        prefix = prefix_map.get(type_name, type_name[:3])
        for entry in entries:
            template_id = f"{prefix}-{entry.name}"
            for tag in entry.tags:
                index.setdefault(tag, []).append(template_id)

    # Sort each tag's entries for deterministic output
    for tag in index:
        index[tag].sort()

    return index


def _build_workflow_map(
    references: list[TemplateEntry],
    tips: list[TemplateEntry],
) -> dict[str, list[str]]:
    """Build workflow name -> relevant template IDs map.

    Maps workflow slugs (e.g. "code-review") to templates
    that document or relate to that workflow.

    Args:
        references: Reference template entries.
        tips: Tip template entries.

    Returns:
        Dict of workflow_name -> list of template_ids.
    """
    wf_map: dict[str, list[str]] = {}

    # Workflow transition tips (named "after-{workflow}")
    for tip in tips:
        if tip.name.startswith("after-"):
            source_wf = tip.name[6:]  # strip "after-"
            wf_map.setdefault(source_wf, []).append(f"tip-{tip.name}")

    # Skill references (skill name often matches workflow name)
    skill_to_wf = {
        "security-audit": "security-audit",
        "code-quality": "code-review",
        "smart-test": "test-gen",
        "bug-predict": "bug-predict",
        "release-prep": "release-prep",
        "refactor-plan": "refactor-plan",
        "doc-gen": "doc-gen",
    }
    for ref in references:
        if ref.category == "skill":
            skill_name = ref.name.replace("skill-", "")
            wf_name = skill_to_wf.get(skill_name)
            if wf_name:
                wf_map.setdefault(wf_name, []).append(f"ref-{ref.name}")

    # Tool references (tool name maps to workflow)
    tool_to_wf = {
        "security-audit": "security-audit",
        "bug-predict": "bug-predict",
        "code-review": "code-review",
        "test-generation": "test-gen",
        "performance-audit": "perf-audit",
        "release-prep": "release-prep",
        "refactor-plan": "refactor-plan",
        "simplify-code": "simplify-code",
        "dependency-check": "dependency-check",
        "deep-review": "deep-review",
    }
    for ref in references:
        if ref.category == "tool":
            tool_name = ref.name.replace("tool-", "")
            wf_name = tool_to_wf.get(tool_name)
            if wf_name:
                wf_map.setdefault(wf_name, []).append(f"ref-{ref.name}")

    # Sort each workflow's templates for deterministic output
    for wf in wf_map:
        wf_map[wf] = sorted(set(wf_map[wf]))

    return dict(sorted(wf_map.items()))


def _merge_links(
    *link_dicts: dict[str, dict],
) -> dict[str, dict]:
    """Merge multiple link dicts, combining list values.

    Args:
        link_dicts: Variable number of link dicts.

    Returns:
        Merged dict with combined lists.
    """
    merged: dict[str, dict] = {}

    for links in link_dicts:
        for template_id, data in links.items():
            if template_id not in merged:
                merged[template_id] = {}
            for key, value in data.items():
                if key in merged[template_id]:
                    merged[template_id][key].extend(value)
                else:
                    merged[template_id][key] = list(value)

    return merged


def build_cross_links(generated_dir: Path) -> dict:
    """Build the complete cross-link index.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Complete cross-links dict ready for JSON output.
    """
    all_templates = _discover_templates(generated_dir)

    errors = all_templates.get("errors", [])
    warnings = all_templates.get("warnings", [])
    tips = all_templates.get("tips", [])
    references = all_templates.get("references", [])

    # Build relationship links
    ew_links = _build_error_warning_links(errors, warnings)
    st_links = _build_skill_tool_links(references)
    et_links = _build_error_tip_links(errors, tips)

    # Merge all links
    all_links = _merge_links(ew_links, st_links, et_links)

    # Add tags to each entry
    prefix_map = {
        "errors": "err",
        "warnings": "war",
        "tips": "tip",
        "references": "ref",
    }
    for type_name, entries in all_templates.items():
        prefix = prefix_map.get(type_name, type_name[:3])
        for entry in entries:
            tid = f"{prefix}-{entry.name}"
            if entry.tags:
                all_links.setdefault(tid, {})["tags"] = entry.tags

    # Sort links by key for deterministic output
    sorted_links = dict(sorted(all_links.items()))

    # Build tag index
    tag_index = _build_tag_index(all_templates)

    # Build workflow map
    workflow_map = _build_workflow_map(references, tips)

    # Stats
    total_templates = sum(len(v) for v in all_templates.values())
    linked = sum(1 for v in sorted_links.values() if any(k != "tags" for k in v))

    return {
        "version": 1,
        "stats": {
            "total_templates": total_templates,
            "linked_templates": linked,
            "total_tags": len(tag_index),
        },
        "links": sorted_links,
        "tag_index": dict(sorted(tag_index.items())),
        "workflow_map": workflow_map,
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point for the cross-link builder.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    generated_dir = repo_root / "plugin" / "help" / "generated"
    output_file = generated_dir / "cross_links.json"

    if not generated_dir.exists():
        print(f"ERROR: {generated_dir} not found")
        return 1

    index = build_cross_links(generated_dir)
    rendered = json.dumps(index, indent=2, ensure_ascii=False) + "\n"

    mode = "Checking" if check else "Generating"
    stats = index["stats"]
    print(
        f"{mode} cross-links: {stats['total_templates']} templates, "
        f"{stats['linked_templates']} linked, "
        f"{stats['total_tags']} tags"
    )

    if check:
        if not output_file.exists():
            print("  [FAIL] cross_links.json: missing")
            return 1
        existing = output_file.read_text(encoding="utf-8")
        if existing == rendered:
            print("  [  OK] cross_links.json: in sync")
            return 0
        print("  [FAIL] cross_links.json: out of sync")
        print("\nRun 'python scripts/build_cross_links.py' to regenerate.")
        return 1

    output_file.write_text(rendered, encoding="utf-8")
    print("  [  OK] cross_links.json: generated")
    print(f"Output: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
