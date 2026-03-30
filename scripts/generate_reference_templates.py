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


@dataclass
class Parameter:
    """A tool parameter."""

    name: str
    type: str
    description: str
    default: str = ""


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
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


def _parse_body_sections(body: str) -> list[Section]:
    """Parse ## sections from a SKILL.md body.

    Args:
        body: Markdown body text (after frontmatter).

    Returns:
        List of Section objects.
    """
    sections: list[Section] = []
    # Split on ## headings
    parts = re.split(r"^## ", body, flags=re.MULTILINE)

    for part in parts[1:]:  # skip preamble before first ##
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        section_body = lines[1].strip() if len(lines) > 1 else ""
        if heading:
            sections.append(Section(heading=heading, body=section_body))

    return sections


def _extract_tool_names_from_body(body: str) -> list[str]:
    """Extract MCP tool names referenced in a SKILL.md body.

    Looks for backtick-quoted tool names that match the
    snake_case pattern used in tool_schemas.py.

    Args:
        body: Markdown body text.

    Returns:
        List of tool name strings.
    """
    # Match backtick-quoted names like `security_audit`
    matches = re.findall(r"`([a-z][a-z0-9_]+)`", body)
    # Filter to likely tool names (contain underscore or known patterns)
    tool_patterns = {
        "security_audit",
        "bug_predict",
        "code_review",
        "test_generation",
        "test_audit",
        "test_gen_parallel",
        "performance_audit",
        "release_prep",
        "doc_audit",
        "doc_gen",
        "doc_orchestrator",
        "refactor_plan",
        "dependency_check",
        "simplify_code",
        "deep_review",
        "secure_release",
        "health_check",
        "research_synthesis",
        "analyze_batch",
        "analyze_image",
        "auth_status",
        "auth_recommend",
        "telemetry_stats",
        "attune_get_level",
        "attune_set_level",
        "context_get",
        "context_set",
        "memory_store",
        "memory_retrieve",
        "memory_search",
        "memory_forget",
    }
    return [m for m in matches if m in tool_patterns]


def parse_skill_references(skills_dir: Path) -> list[ReferenceTemplate]:
    """Parse skill SKILL.md files into procedural ReferenceTemplates.

    Uses python-frontmatter to extract YAML frontmatter and
    parses ## sections from the body.

    Args:
        skills_dir: Path to plugin/skills/ directory.

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

        # Parse body sections
        sections = _parse_body_sections(post.content)

        # Extract tool references for cross-linking
        tool_names = _extract_tool_names_from_body(post.content)
        related: list[dict[str, str]] = []
        if tool_names:
            related.append(
                {
                    "type": "Reference",
                    "description": f"MCP tools: {', '.join(tool_names)}",
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

    Imports tool schema functions directly (pure data, no
    side effects).

    Args:
        tool_schemas_path: Path to tool_schemas.py.

    Returns:
        List of ReferenceTemplate objects (subtype=tabular).
    """
    import importlib.util

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
                    )
                )

            related: list[dict[str, str]] = []
            siblings = [t for t in group_tool_names if t != tool_name]
            if siblings:
                related.append(
                    {
                        "type": "Reference",
                        "description": (
                            f"Related {group_name} tools: " f"{', '.join(siblings[:3])}"
                        ),
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
                    tags=["mcp", "tool", group_name],
                    source="src/attune/mcp/tool_schemas.py",
                    related_topics=related,
                )
            )

    return templates


def _template_for_subtype(subtype: str) -> str:
    """Map subtype to Jinja2 template filename.

    Args:
        subtype: One of procedural, tabular, freeform.

    Returns:
        Template filename string.
    """
    return f"reference-{subtype}.md.jinja2"


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Reference template generator.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
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

    # Step 1: Discover from both sources
    refs: list[ReferenceTemplate] = []

    if skills_dir.exists():
        skill_refs = parse_skill_references(skills_dir)
        refs.extend(skill_refs)
        print(f"  Skill references (procedural): {len(skill_refs)} found")

    if tool_schemas_path.exists():
        tool_refs = parse_tool_references(tool_schemas_path)
        refs.extend(tool_refs)
        print(f"  Tool references (tabular): {len(tool_refs)} found")

    if not refs:
        print("No references found from any source")
        return 1

    # Step 2: Render — group by subtype for template dispatch
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

    # Group by subtype
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
                "sections": [{"heading": s.heading, "body": s.body} for s in r.sections],
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "default": p.default,
                    }
                    for p in r.parameters
                ],
                "usage": r.usage,
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

    print(f"\n{'Checked' if check else 'Generated'}: " f"{total_ok} ok, {total_fail} failed")
    print(f"Output: {output_dir}")

    if check and total_fail > 0:
        print("\nRun 'python scripts/generate_reference_templates.py'" " to regenerate.")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
