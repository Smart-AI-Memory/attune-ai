"""Template engine for Attune AI project scaffolding.

Provides the scaffolding logic for creating new projects from
templates, including placeholder replacement, file creation, and
CLI command handling.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path
from attune.template_defs_basic import MINIMAL_TEMPLATE, PYTHON_CLI_TEMPLATE
from attune.template_defs_web import PYTHON_AGENT_TEMPLATE, PYTHON_FASTAPI_TEMPLATE

# Assembled registry of all templates
TEMPLATES: dict[str, dict[str, Any]] = {
    "minimal": MINIMAL_TEMPLATE,
    "python-cli": PYTHON_CLI_TEMPLATE,
    "python-fastapi": PYTHON_FASTAPI_TEMPLATE,
    "python-agent": PYTHON_AGENT_TEMPLATE,
}


def list_templates() -> list:
    """List available templates.

    Returns:
        List of dicts with id, name, and description for each template.

    """
    return [
        {"id": tid, "name": t["name"], "description": t["description"]}
        for tid, t in TEMPLATES.items()
    ]


def scaffold_project(
    template_name: str,
    project_name: str,
    target_dir: str | None = None,
    force: bool = False,
) -> dict:
    """Create a new project from a template.

    Args:
        template_name: Template ID (minimal, python-cli,
            python-fastapi, python-agent)
        project_name: Name for the new project
        target_dir: Directory to create project in
            (default: ./{project_name})
        force: Overwrite existing files

    Returns:
        Dict with created files and status

    """
    if template_name not in TEMPLATES:
        return {
            "success": False,
            "error": f"Unknown template: {template_name}",
            "available": list(TEMPLATES.keys()),
        }

    template = TEMPLATES[template_name]
    target = Path(target_dir) if target_dir else Path(project_name)

    # Check if directory exists
    if target.exists() and not force:
        if any(target.iterdir()):
            return {
                "success": False,
                "error": (
                    f"Directory '{target}' exists and is not empty." " Use --force to overwrite."
                ),
            }

    # Create directory
    target.mkdir(parents=True, exist_ok=True)

    # Create project name class version (for Python class names)
    project_name_class = "".join(
        word.capitalize() for word in project_name.replace("-", "_").replace(" ", "_").split("_")
    )

    # Create files
    created_files = []
    files = template["files"]
    if not isinstance(files, dict):
        return {"success": False, "error": "Invalid template structure"}
    for file_path, content in files.items():
        # Replace placeholders in path
        actual_path = file_path.replace("{{project_name}}", project_name)

        # Replace placeholders in content
        actual_content = content.replace("{{project_name}}", project_name)
        actual_content = actual_content.replace("{{project_name_class}}", project_name_class)

        # Create file
        full_path = target / actual_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle special files
        if file_path == ".gitignore_additions":
            # Append to existing .gitignore or create new
            gitignore_path = target / ".gitignore"
            validated_gitignore = _validate_file_path(str(gitignore_path))
            if validated_gitignore.exists():
                with open(validated_gitignore, "a", encoding="utf-8") as f:
                    f.write("\n" + actual_content)
            else:
                with open(validated_gitignore, "w", encoding="utf-8") as f:
                    f.write(actual_content)
            created_files.append(".gitignore")
        else:
            validated_path = _validate_file_path(str(full_path))
            with open(validated_path, "w", encoding="utf-8") as f:
                f.write(actual_content)
            created_files.append(actual_path)

    # Create patterns directory
    (target / "patterns").mkdir(exist_ok=True)

    return {
        "success": True,
        "template": template_name,
        "project_name": project_name,
        "target_dir": str(target),
        "files_created": created_files,
        "next_steps": [
            f"cd {target}",
            "pip install -e .",
            "attune doctor",
        ],
    }


def cmd_new(args: object) -> int:
    """CLI command handler for creating new projects.

    Args:
        args: Parsed CLI arguments with template, name,
            output, force, and list attributes.

    Returns:
        Exit code (0 for success, 1 for error).

    """
    template = getattr(args, "template", None)
    project_name = getattr(args, "name", None)
    target_dir = getattr(args, "output", None)
    force = getattr(args, "force", False)
    list_only = getattr(args, "list", False)

    if list_only:
        print("\nAvailable Templates:")
        print("-" * 50)
        for t in list_templates():
            print(f"  {t['id']:15} {t['description']}")
        print("\nUsage: attune new <template> <project-name>")
        print()
        return 0

    if not template or not project_name:
        print("Usage: attune new <template> <project-name>")
        print("       attune new --list")
        return 1

    print(f"\nCreating new project from '{template}' template...")

    result = scaffold_project(template, project_name, target_dir, force)

    if result["success"]:
        print(f"\n  Project created: {result['target_dir']}")
        print("\n  Files created:")
        for f in result["files_created"]:
            print(f"    - {f}")
        print("\n  Next steps:")
        for step in result["next_steps"]:
            print(f"    $ {step}")
        print()
        return 0
    print(f"\n  Error: {result['error']}")
    if "available" in result:
        print(f"  Available templates: {', '.join(result['available'])}")
    print()
    return 1
