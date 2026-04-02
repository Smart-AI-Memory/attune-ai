#!/usr/bin/env python3
"""Generate Reference templates from skills and MCP tool schemas.

Sources:
  1. plugin/skills/*/SKILL.md — procedural references (13 skills)
  2. src/attune/mcp/tool_schemas.py — tabular references (31 tools)

Each source auto-selects a subtype:
  - Skills -> procedural (intro + structured sections)
  - Tools -> tabular (description + parameter table)

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_reference_templates.py           # Generate
    python scripts/generate_reference_templates.py --check   # Verify
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output, slugify


@dataclass
class Section:
    """A body section parsed from a SKILL.md file."""

    heading: str
    body: str
    subsections: list[Section] = field(default_factory=list)


@dataclass
class Parameter:
    """A tool parameter."""

    name: str
    type: str
    description: str
    default: str = ""
    constraints: str = ""


@dataclass
class ReferenceTemplate:
    """Populated Reference template ready for rendering."""

    name: str
    title: str
    description: str
    category: str
    subtype: str  # procedural | tabular | freeform
    sections: list[Section] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    usage: str = ""
    group: str = ""
    usage_example: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


def _load_tool_names(tool_schemas_path: Path) -> set[str]:
    """Load all tool names from tool_schemas.py dynamically.

    Args:
        tool_schemas_path: Path to tool_schemas.py.

    Returns:
        Set of tool name strings.
    """
    spec = importlib.util.spec_from_file_location(
        "tool_schemas",
        tool_schemas_path,
    )
    if spec is None or spec.loader is None:
        return set()

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    names: set[str] = set()
    for get_fn in [
        module.get_workflow_tools,
        module.get_utility_tools,
        module.get_memory_tools,
    ]:
        names.update(get_fn().keys())
    return names


def _parse_body_sections(body: str) -> list[Section]:
    """Parse ## and ### sections from a SKILL.md body.

    First splits on ## headings, then within each section
    splits on ### to populate subsections.

    Args:
        body: Markdown body text (after frontmatter).

    Returns:
        List of Section objects with nested subsections.
    """
    sections: list[Section] = []
    parts = re.split(r"^## ", body, flags=re.MULTILINE)

    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        section_body = lines[1].strip() if len(lines) > 1 else ""
        if not heading:
            continue

        # Parse ### subsections
        subsections: list[Section] = []
        sub_parts = re.split(r"^### ", section_body, flags=re.MULTILINE)
        main_body = sub_parts[0].strip() if sub_parts else ""

        for sub_part in sub_parts[1:]:
            sub_lines = sub_part.strip().split("\n", 1)
            sub_heading = sub_lines[0].strip()
            sub_body = sub_lines[1].strip() if len(sub_lines) > 1 else ""
            if sub_heading:
                subsections.append(Section(heading=sub_heading, body=sub_body))

        sections.append(Section(heading=heading, body=main_body, subsections=subsections))

    return sections


def _extract_tool_names_from_body(
    body: str,
    known_tools: set[str],
) -> list[str]:
    """Extract MCP tool names referenced in a SKILL.md body.

    Uses the dynamic tool name set instead of a hardcoded
    whitelist. Deduplicates while preserving order.

    Args:
        body: Markdown body text.
        known_tools: Set of valid tool names from tool_schemas.py.

    Returns:
        Deduplicated list of tool name strings.
    """
    matches = re.findall(r"`([a-z][a-z0-9_]+)`", body)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m in known_tools and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def parse_skill_references(
    skills_dir: Path,
    known_tools: set[str],
) -> list[ReferenceTemplate]:
    """Parse skill SKILL.md files into procedural ReferenceTemplates.

    Args:
        skills_dir: Path to plugin/skills/ directory.
        known_tools: Set of valid tool names for cross-linking.

    Returns:
        List of ReferenceTemplate objects (subtype=procedural).
    """
    templates: list[ReferenceTemplate] = []

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        post = frontmatter.load(str(skill_file))
        name = post.get("name", skill_dir.name)
        description = post.get("description", "")
        argument_hint = post.get("argument-hint", "")

        usage = ""
        if argument_hint:
            usage = f"`/{name} {argument_hint}`"

        sections = _parse_body_sections(post.content)

        # Extract tool references — one Related entry per tool
        tool_names = _extract_tool_names_from_body(post.content, known_tools)
        related: list[dict[str, str]] = []
        for tn in tool_names:
            display = tn.replace("_", " ").title()
            related.append(
                {
                    "type": "Reference",
                    "description": f"Tool: {display} (`{tn}`)",
                }
            )

        templates.append(
            ReferenceTemplate(
                name=slugify(f"skill-{name}"),
                title=f"Skill: {name}",
                description=description,
                category="skill",
                subtype="procedural",
                sections=sections,
                usage=usage,
                tags=["skill", "plugin"],
                source=f"plugin/skills/{skill_dir.name}/SKILL.md",
                related_topics=related,
            )
        )

    return templates


def parse_tool_references(tool_schemas_path: Path) -> list[ReferenceTemplate]:
    """Parse MCP tool schemas into tabular ReferenceTemplates.

    Extracts parameters with constraints (enum, min/max),
    group info, and auto-generated usage examples.

    Args:
        tool_schemas_path: Path to tool_schemas.py.

    Returns:
        List of ReferenceTemplate objects (subtype=tabular).
    """
    spec = importlib.util.spec_from_file_location(
        "tool_schemas",
        tool_schemas_path,
    )
    if spec is None or spec.loader is None:
        return []

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    templates: list[ReferenceTemplate] = []

    groups = [
        ("workflow", module.get_workflow_tools),
        ("utility", module.get_utility_tools),
        ("memory", module.get_memory_tools),
    ]

    for group_name, get_tools_fn in groups:
        tools = get_tools_fn()
        group_tool_names = list(tools.keys())

        for tool_name, tool_def in tools.items():
            description = tool_def.get("description", "")
            input_schema = tool_def.get("input_schema", {})
            properties = input_schema.get("properties", {})
            required = set(input_schema.get("required", []))

            params: list[Parameter] = []
            for param_name, param_def in properties.items():
                # Extract constraints
                constraints_parts: list[str] = []
                if "enum" in param_def:
                    constraints_parts.append(f"enum: {'|'.join(str(v) for v in param_def['enum'])}")
                if "minimum" in param_def or "maximum" in param_def:
                    lo = param_def.get("minimum", "")
                    hi = param_def.get("maximum", "")
                    constraints_parts.append(f"range: {lo}-{hi}")

                params.append(
                    Parameter(
                        name=param_name,
                        type=param_def.get("type", "string"),
                        description=param_def.get("description", ""),
                        default=str(
                            param_def.get(
                                "default",
                                "required" if param_name in required else "",
                            )
                        ),
                        constraints="; ".join(constraints_parts),
                    )
                )

            # Build usage example from required params
            req_params = [p for p in params if p.default == "required"]
            example_args = ", ".join(f'{p.name}="..."' for p in req_params)
            usage_example = f"`{tool_name}({example_args})`"

            # Related: sibling tools with descriptions
            related: list[dict[str, str]] = []
            siblings = [t for t in group_tool_names if t != tool_name]
            for sib in siblings[:3]:
                sib_desc = tools[sib].get("description", "")
                sib_display = sib.replace("_", " ").title()
                # Truncate long descriptions
                short_desc = sib_desc[:60] + "..." if len(sib_desc) > 60 else sib_desc
                related.append(
                    {
                        "type": "Reference",
                        "description": f"Tool: {sib_display} — {short_desc}",
                    }
                )

            display_name = tool_name.replace("_", " ").title()
            templates.append(
                ReferenceTemplate(
                    name=slugify(f"tool-{tool_name}"),
                    title=f"Tool: {display_name}",
                    description=description,
                    category="tool",
                    subtype="tabular",
                    parameters=params,
                    group=group_name,
                    usage_example=usage_example,
                    tags=["mcp", "tool", group_name],
                    source="src/attune/mcp/tool_schemas.py",
                    related_topics=related,
                )
            )

    return templates


def _template_for_subtype(subtype: str) -> str:
    """Map subtype to Jinja2 template filename."""
    return f"reference-{subtype}.md.jinja2"


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Reference template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "plugin" / "skills"
    tool_schemas_path = repo_root / "src" / "attune" / "mcp" / "tool_schemas.py"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "references"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    # Load dynamic tool names for cross-referencing
    known_tools = _load_tool_names(tool_schemas_path) if tool_schemas_path.exists() else set()

    refs: list[ReferenceTemplate] = []

    if skills_dir.exists():
        skill_refs = parse_skill_references(skills_dir, known_tools)
        refs.extend(skill_refs)
        print(f"  Skill references (procedural): {len(skill_refs)} found")

    if tool_schemas_path.exists():
        tool_refs = parse_tool_references(tool_schemas_path)
        refs.extend(tool_refs)
        print(f"  Tool references (tabular): {len(tool_refs)} found")

    if not refs:
        print("No references found from any source")
        return 1

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Reference templates from {len(refs)} entries\n")

    total_ok = 0
    total_fail = 0

    by_subtype: dict[str, list[ReferenceTemplate]] = {}
    for r in refs:
        by_subtype.setdefault(r.subtype, []).append(r)

    for subtype, group in by_subtype.items():
        template_name = _template_for_subtype(subtype)

        items = [
            {
                "name": r.name,
                "title": r.title,
                "description": r.description,
                "category": r.category,
                "sections": [
                    {
                        "heading": s.heading,
                        "body": s.body,
                        "subsections": [
                            {"heading": ss.heading, "body": ss.body} for ss in s.subsections
                        ],
                    }
                    for s in r.sections
                ],
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "default": p.default,
                        "constraints": p.constraints,
                    }
                    for p in r.parameters
                ],
                "usage": r.usage,
                "group": r.group,
                "usage_example": r.usage_example,
                "tags": r.tags,
                "source": r.source,
                "related_topics": r.related_topics,
            }
            for r in group
        ]

        ok, fail = render_and_output(
            env,
            template_name,
            items,
            output_dir,
            check,
        )
        total_ok += ok
        total_fail += fail

    print(f"\n{'Checked' if check else 'Generated'}: {total_ok} ok, {total_fail} failed")
    print(f"Output: {output_dir}")

    if check and total_fail > 0:
        print("\nRun 'python scripts/generate_reference_templates.py' to regenerate.")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
