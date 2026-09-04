#!/usr/bin/env python3
"""Generate Concept templates — what/why/how for system concepts.

Sources:
  1. Framework features from the website/codebase
  2. Architecture patterns from .claude/CLAUDE.md

Usage:
    python scripts/generate_concept_templates.py           # Generate
    python scripts/generate_concept_templates.py --check   # Verify
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output


@dataclass
class ConceptTemplate:
    """Populated Concept template."""

    name: str
    title: str
    what: str
    why: str
    how: str
    example: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


# Core concepts from the framework
_CONCEPTS: list[dict] = [
    {
        "name": "tier-routing",
        "title": "Model tier routing",
        "what": (
            "Tier routing automatically selects the right Claude model "
            "based on task complexity: CHEAP resolves to Haiku, CAPABLE "
            "to Sonnet, and PREMIUM to Claude Fable 5.1 "
            "(`claude-fable-5-1`). Simple tasks use cheap models; complex "
            "tasks escalate to premium."
        ),
        "why": (
            "Reduces API costs without sacrificing quality — most "
            "workflow stages don't need the most expensive model. Note "
            "the premium tier runs `claude-fable-5-1` at 2x the former "
            "Opus pricing ($10 input / $50 output per MTok), so "
            "premium-tier stages cost twice what they did on Opus."
        ),
        "how": (
            "Each workflow defines a `tier_map` mapping stages to tiers "
            "(CHEAP, CAPABLE, PREMIUM). `attune.model_tiers` resolves "
            "each tier to a model ID per call, honoring env overrides "
            "(`ATTUNE_MODEL_PREMIUM`, `ATTUNE_MODEL_CAPABLE`, "
            "`ATTUNE_MODEL_CHEAP`). Tier fallback escalates "
            "automatically if a cheaper tier fails. Editing/polish "
            "passes are deliberately not a tier: they run a dedicated "
            "editing model (`ATTUNE_MODEL_EDITING`, default "
            "`claude-opus-5`)."
        ),
        "example": '`tier_map = {"initial_scan": ModelTier.CHEAP, "deep_review": ModelTier.PREMIUM}`',
        "tags": ["architecture", "cost-optimization"],
        "source": "src/attune/model_tiers.py",
    },
    {
        "name": "socratic-discovery",
        "title": "Socratic discovery",
        "what": (
            "The core UX principle of Attune AI: always guide users "
            "through questions before executing actions. Understand "
            "the goal, narrow scope, confirm choices, then execute."
        ),
        "why": (
            "Prevents wasted execution by ensuring the right task runs "
            "with the right scope. Users get better results because "
            "the system understands their intent first."
        ),
        "how": (
            "Every skill and workflow starts with scoping questions "
            "(AskUserQuestion). The discovery flow is: 1) understand "
            "goal, 2) narrow scope, 3) confirm choices, 4) execute. "
            "The /attune command is the entry point for Socratic routing."
        ),
        "tags": ["philosophy", "ux"],
        "source": ".claude/CLAUDE.md",
    },
    {
        "name": "sync-paradigm",
        "title": "The sync paradigm",
        "what": (
            "A six-step pattern for generating documentation from code: "
            "Discover, Parse, Transform, Validate, Output, Verify. "
            "Every generator in the doc stack follows this pattern."
        ),
        "why": (
            "Ensures consistency, idempotency, and verifiability. "
            "The --check mode can validate that generated content "
            "matches its source without regenerating."
        ),
        "how": (
            "1. Discover — find source files (SKILL.md, tool_schemas.py). "
            "2. Parse — extract structured data from source. "
            "3. Transform — convert to template dataclass. "
            "4. Validate — check schema compliance. "
            "5. Output — render via Jinja2 to generated/ directory. "
            "6. Verify — --check mode compares output to existing files."
        ),
        "example": "`python scripts/generate_all.py --check` verifies all 498 templates in sync.",
        "tags": ["architecture", "documentation"],
        "source": "scripts/generate_all.py",
    },
    {
        "name": "progressive-depth",
        "title": "Progressive depth",
        "what": (
            "Templates adapt their verbosity based on repeated access. "
            "First view shows a compact summary; asking again shows "
            "normal detail; asking a third time shows everything."
        ),
        "why": (
            "Respects the user's attention. Most of the time, a one-line "
            "answer is enough. When it's not, the user drills deeper "
            "without switching tools or commands."
        ),
        "how": (
            "The engine tracks session state (last template ID + depth "
            "level). populate_progressive() increments depth on repeated "
            "access to the same template. Depth maps to verbosity: "
            "0=compact, 1=normal, 2=detailed. New template resets to 0."
        ),
        "example": "Call `populate_progressive('err-shadow-dirs')` three times to see escalation.",
        "tags": ["help-system", "ux"],
        "source": "src/attune/help/engine.py",
    },
    {
        "name": "cross-linking",
        "title": "Template cross-linking",
        "what": (
            "Deterministic relationships between 498 templates across "
            "11 types. Error links to Warning, Skill links to Tool, "
            "FAQ links to Error, Task links to Reference."
        ),
        "why": (
            "Users don't navigate documentation in a linear path. "
            "Cross-links let the help system surface related content "
            "regardless of where the user starts."
        ),
        "how": (
            "build_cross_links.py derives relationships from source data: "
            "slug matching (Error<->Warning), tool name extraction "
            "(Skill->Tool), token overlap (Error->Tip). Results stored "
            "in cross_links.json with a tag_index for search."
        ),
        "example": "`attune help-docs --tag security` returns 37 templates across all types.",
        "tags": ["help-system", "architecture"],
        "source": "scripts/build_cross_links.py",
    },
    {
        "name": "audience-adaptation",
        "title": "Audience-adaptive rendering",
        "what": (
            "The same template source produces different output for "
            "three channels: Claude Code (inline conversation), "
            "marketplace (static docs), and CLI (Rich terminal)."
        ),
        "why": (
            "Users access help in different contexts. A terminal user "
            "needs color-coded panels; a Claude Code user needs concise "
            "markdown; a docs browser needs full navigation."
        ),
        "how": (
            "Three render functions in transformers.py: "
            "render_claude_code() strips Related Topics and truncates; "
            "render_marketplace() adds YAML frontmatter for SSG; "
            "render_cli() uses Rich panels, tables, and color."
        ),
        "tags": ["help-system", "architecture"],
        "source": "src/attune/help/transformers.py",
    },
    {
        "name": "template-composition",
        "title": "Template composition",
        "what": (
            "Templates can inline related content at render time. "
            "An Error template embeds its prevention Tip; a Skill "
            "reference embeds its Tool parameter table."
        ),
        "why": (
            "Users get complete context without navigating between "
            "templates. A composed view answers the question and "
            "prevents recurrence in one read."
        ),
        "how": (
            "cross_links.json stores embed rules derived from "
            "prevented_by and references_tools relationships. "
            "populate(compose=True) follows embed rules and appends "
            "compact versions of linked templates. Max depth: 1."
        ),
        "tags": ["help-system"],
        "source": "src/attune/help/engine.py",
    },
    {
        "name": "workflow-chain-prediction",
        "title": "Workflow chain prediction",
        "what": (
            "After a workflow completes, the system suggests relevant "
            "follow-up workflows based on transition patterns. "
            "For example: code-review -> security-audit -> test-gen."
        ),
        "why": (
            "Reduces decision fatigue. Users don't need to remember "
            "which workflows complement each other — the system "
            "surfaces the right next step."
        ),
        "how": (
            "suggestions.py maintains a _TRANSITION_REGISTRY mapping "
            "each workflow to its likely follow-ups. get_workflow_help() "
            "in the engine maps these to template IDs via workflow_map "
            "in cross_links.json."
        ),
        "tags": ["help-system", "workflow"],
        "source": "src/attune/workflows/suggestions.py",
    },
    {
        "name": "feedback-loop",
        "title": "Template feedback loop",
        "what": (
            "Users can rate templates as good or bad. Ratings accumulate "
            "into a confidence score that influences template ranking."
        ),
        "why": (
            "Template quality is only measurable by whether it actually "
            "helps users. Feedback closes the loop between generation "
            "and usefulness."
        ),
        "how": (
            "record_template_feedback() stores ratings in feedback.json. "
            "get_template_confidence() returns good/(good+bad) as a "
            "0.0-1.0 score. CLI: `attune help-docs <id> --feedback good|bad`."
        ),
        "tags": ["help-system", "telemetry"],
        "source": "src/attune/help/engine.py",
    },
]


def _discover_concepts_from_skills(repo_root: Path) -> list[dict]:
    """Auto-derive concept templates from plugin skill definitions.

    Reads each SKILL.md's frontmatter (name, description) and
    generates a concept dict. Only creates entries for skills
    that don't already have a curated concept in _CONCEPTS.

    Args:
        repo_root: Repository root directory.

    Returns:
        List of concept dicts for newly discovered skills.
    """
    import frontmatter

    skills_dir = repo_root / "plugin" / "skills"
    if not skills_dir.exists():
        return []

    curated_names = {c["name"] for c in _CONCEPTS}
    output_dir = repo_root / "plugin" / "help" / "generated" / "concepts"
    discovered: list[dict] = []

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            post = frontmatter.load(str(skill_md))
        except Exception:  # noqa: BLE001
            # INTENTIONAL: skip unparseable skill files
            continue

        skill_name = post.get("name", skill_dir.name)
        concept_name = f"tool-{skill_name}"

        # Skip if a curated concept already exists
        if concept_name in curated_names:
            continue

        # Skip if a hand-written concept already exists on disk
        # (tagged with non-auto-discovered tags)
        existing = output_dir / f"{concept_name}.md"
        if existing.exists():
            try:
                existing_post = frontmatter.load(str(existing))
                tags = existing_post.get("tags", [])
                if "auto-discovered" not in (tags if isinstance(tags, list) else []):
                    continue  # Hand-written, don't overwrite
            except Exception:  # noqa: BLE001
                pass

        description = post.get("description", "")
        # Strip trigger info from description (after "Triggers on:")
        short_desc = description.split("Triggers on:")[0].strip().rstrip(".")

        discovered.append(
            {
                "name": concept_name,
                "title": skill_name.replace("-", " ").title(),
                "what": short_desc or f"The {skill_name} skill.",
                "why": (
                    "See the full reference for details on what "
                    "this tool checks and when to use it."
                ),
                "how": f"Run `/{skill_name}` to get started.",
                "tags": ["skill", "auto-discovered"],
                "source": f"plugin/skills/{skill_dir.name}/SKILL.md",
            }
        )

    return discovered


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Concept template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "concepts"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    # Merge curated + auto-discovered (curated takes precedence)
    all_concept_dicts = list(_CONCEPTS)
    discovered = _discover_concepts_from_skills(repo_root)
    all_concept_dicts.extend(discovered)

    concepts = [ConceptTemplate(**c) for c in all_concept_dicts]
    print(f"  Concepts: {len(concepts)} found ({len(discovered)} auto-discovered)")

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Concept templates from {len(concepts)} entries\n")

    items = [
        {
            "name": c.name,
            "title": c.title,
            "what": c.what,
            "why": c.why,
            "how": c.how,
            "example": c.example,
            "tags": c.tags,
            "source": c.source,
            "related_topics": c.related_topics,
        }
        for c in concepts
    ]

    successes, failures = render_and_output(
        env,
        "concept.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_concept_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
