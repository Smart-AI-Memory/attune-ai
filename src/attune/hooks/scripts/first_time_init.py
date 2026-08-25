"""First-Time Initialization Hook

Checks if Attune AI is initialized in the current project.
If not, prompts user with initialization dialog.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from attune.security.path_validation import _validate_file_path
except ImportError:  # direct script execution (hook) — bootstrap repo src/
    from _bootstrap import ensure_repo_src_on_path

    ensure_repo_src_on_path()
    from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Default configuration template
DEFAULT_CONFIG = """# Attune AI Configuration
# Generated: {timestamp}

agent:
  name: empathy-assistant
  model_tier: capable

hooks:
  enabled: true
  log_executions: false

learning:
  enabled: true
  auto_evaluate: true
  quality_threshold: good
  max_patterns_per_session: 10

context:
  auto_compact: true
  token_threshold: 80
"""

# Directories to create
INIT_DIRECTORIES = [
    ".attune",
    ".attune/compact_states",
    ".attune/learned_skills",
    ".attune/sessions",
    ".attune/patterns",
]


def get_project_root(**context: Any) -> Path:
    """Get the project root directory.

    Args:
        **context: Hook context with project_path

    Returns:
        Project root path

    """
    project_path = context.get("project_path")
    if project_path:
        return Path(project_path)

    # Fall back to current working directory
    return Path.cwd()


def is_initialized(project_root: Path) -> bool:
    """Check if Attune AI is initialized in the project.

    Args:
        project_root: Project root directory

    Returns:
        True if .empathy directory exists with config

    """
    empathy_dir = project_root / ".attune"
    config_file = project_root / "attune.config.yaml"

    return empathy_dir.exists() or config_file.exists()


def get_never_ask_file(project_root: Path) -> Path:
    """Get path to the 'never ask' marker file."""
    return project_root / ".empathy_never_init"


def should_skip_init(project_root: Path) -> bool:
    """Check if user previously said 'never ask again'."""
    return get_never_ask_file(project_root).exists()


def mark_never_ask(project_root: Path) -> None:
    """Mark project to never ask about init again."""
    marker = _validate_file_path(str(get_never_ask_file(project_root)))
    marker.write_text(f"Created: {datetime.now().isoformat()}\n", encoding="utf-8")


def initialize_project(project_root: Path) -> dict[str, Any]:
    """Initialize Attune AI in the project.

    Args:
        project_root: Project root directory

    Returns:
        Initialization result

    """
    result = {
        "success": True,
        "created_directories": [],
        "created_files": [],
        "errors": [],
    }

    # Create directories
    for dir_path in INIT_DIRECTORIES:
        full_path = project_root / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            result["created_directories"].append(str(dir_path))
            logger.info("Created directory: %s", dir_path)
        except OSError as e:
            result["errors"].append(f"Failed to create {dir_path}: {e}")
            logger.error("Failed to create directory %s: %s", dir_path, e)

    # Create config file
    config_path = project_root / "attune.config.yaml"
    if not config_path.exists():
        try:
            config_content = DEFAULT_CONFIG.format(timestamp=datetime.now().isoformat())
            validated_config = _validate_file_path(str(config_path))
            validated_config.write_text(config_content, encoding="utf-8")
            result["created_files"].append("attune.config.yaml")
            logger.info("Created config file: attune.config.yaml")
        except OSError as e:
            result["errors"].append(f"Failed to create config: {e}")
            logger.error("Failed to create config file: %s", e)

    # Create .gitignore entries file
    gitignore_additions = project_root / ".attune" / ".gitignore_additions"
    try:
        gitignore_content = """# Add these to your .gitignore:
.attune/compact_states/
.attune/sessions/
.attune/learned_skills/
"""
        validated_gitignore = _validate_file_path(str(gitignore_additions))
        validated_gitignore.write_text(gitignore_content, encoding="utf-8")
        result["created_files"].append(".attune/.gitignore_additions")
    except OSError:
        pass  # Non-critical

    if result["errors"]:
        result["success"] = False

    return result


def check_init(**context: Any) -> dict[str, Any]:
    """Check if initialization is needed and return appropriate response.

    This is called on SessionStart to check if the project needs initialization.

    Args:
        **context: Hook context

    Returns:
        Dict with initialization status and prompt if needed

    """
    project_root = get_project_root(**context)

    result = {
        "checked": True,
        "project_root": str(project_root),
        "timestamp": datetime.now().isoformat(),
        "needs_init": False,
        "prompt_user": False,
        "already_initialized": False,
        "skipped": False,
    }

    # Check if already initialized
    if is_initialized(project_root):
        result["already_initialized"] = True
        logger.debug("Project already initialized: %s", project_root)
        return result

    # Check if user said "never ask"
    if should_skip_init(project_root):
        result["skipped"] = True
        logger.debug("Skipping init prompt (user preference): %s", project_root)
        return result

    # Need to prompt user
    result["needs_init"] = True
    result["prompt_user"] = True
    result["prompt"] = {
        "header": "Setup",
        "question": "Welcome! Set up Attune AI for this project?",
        "options": [
            {
                "label": "Yes, initialize now",
                "description": "Create .attune/ folder and default config",
                "action": "init",
            },
            {
                "label": "Not now",
                "description": "Ask me again next session",
                "action": "skip_once",
            },
            {
                "label": "Never for this project",
                "description": "Don't ask again for this project",
                "action": "never",
            },
        ],
    }

    logger.info("Project needs initialization: %s", project_root)
    return result


def handle_init_response(action: str, **context: Any) -> dict[str, Any]:
    """Handle user's response to the initialization prompt.

    Args:
        action: User's selected action (init, skip_once, never)
        **context: Hook context

    Returns:
        Result of the action

    """
    project_root = get_project_root(**context)

    if action == "init":
        result = initialize_project(project_root)
        if result["success"]:
            result["message"] = "Attune AI initialized successfully!"
        else:
            result["message"] = "Initialization completed with errors."
        return result

    if action == "never":
        mark_never_ask(project_root)
        return {
            "success": True,
            "action": "never",
            "message": "Got it! Won't ask again for this project.",
        }

    # skip_once
    return {
        "success": True,
        "action": "skip_once",
        "message": "No problem! I'll ask again next time.",
    }


def main(**context: Any) -> dict[str, Any]:
    """Main hook entry point.

    Called on SessionStart to check if initialization is needed.

    Args:
        **context: Hook context

    Returns:
        Initialization check result

    """
    return check_init(**context)


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    # Allow running as a script for testing
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        # Test initialization
        result = initialize_project(Path.cwd())
    else:
        # Test check
        result = main(project_path=str(Path.cwd()))

    print(json.dumps(result, indent=2))
