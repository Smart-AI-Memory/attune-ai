"""Regression tests for skill-derived task help generation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SCRIPT = SCRIPTS_DIR / "generate_task_templates.py"
SPEC = importlib.util.spec_from_file_location("generate_task_templates_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


def test_execution_markdown_keeps_paragraphs_and_list_indentation(tmp_path: Path) -> None:
    """A workspace subsection must not collapse into one malformed line."""
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo
description: Demo task generation.
---

# Demo

## Execution

### Shared command workspace (preferred)

Open adapter `demo` and render its workspace.

Publish the exact terminal receipt.

```
demo_tool()
verify_result()
```
""",
        encoding="utf-8",
    )

    task = GENERATOR.parse_skill_tasks(tmp_path)[0]
    assert task.steps[0].detail == (
        "### Shared command workspace (preferred)\n\n"
        "Open adapter `demo` and render its workspace.\n\n"
        "Publish the exact terminal receipt."
    )

    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "plugin" / "help" / "templates")),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = env.get_template("task.md.jinja2").render(
        name=task.name,
        title=task.title,
        introduction=task.introduction,
        steps=[
            {
                "action": step.action,
                "detail": step.detail,
                "code": step.code,
                "code_language": step.code_language,
            }
            for step in task.steps
        ],
        prerequisites=task.prerequisites,
        tags=task.tags,
        source=task.source,
        related_topics=task.related_topics,
    )
    assert (
        "1. **Run the tool**\n"
        "   ### Shared command workspace (preferred)\n\n"
        "   Open adapter `demo` and render its workspace."
    ) in rendered
    assert "   demo_tool()\n   verify_result()" in rendered


def test_execution_parts_bind_prose_to_each_code_block() -> None:
    """Multi-option sections keep each label beside its own command."""
    execution = """First option:

```shell-session {data-demo=true}
run-first
```

Second option:

```bash
run-second
```

Terminal receipt guidance.
"""

    assert GENERATOR._execution_parts(execution) == [
        GENERATOR.ExecutionPart("First option:", "run-first", "shell-session"),
        GENERATOR.ExecutionPart("Second option:", "run-second", "bash"),
        GENERATOR.ExecutionPart("Terminal receipt guidance.", ""),
    ]


def test_execution_parts_handle_empty_and_markdown_fences() -> None:
    """Empty/labeled fences cannot consume later prose or leak fence markers."""
    execution = """Empty example:

~~~language-with-hyphen {title=demo}
~~~

Report shape:

```markdown
## Result

Passed.
```
"""

    assert GENERATOR._execution_parts(execution) == [
        GENERATOR.ExecutionPart("Empty example:", "", "language-with-hyphen"),
        GENERATOR.ExecutionPart("Report shape:", "## Result\n\nPassed.", "markdown"),
    ]


def test_parse_skill_labels_output_and_trailing_guidance(tmp_path: Path) -> None:
    """Only executable fences are presented as runnable tool options."""
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo
description: Demo task generation.
---

## Execution

Run the command:

```bash
demo_tool
```

Expected shape:

```markdown
## Result
```

Preserve the terminal receipt.
""",
        encoding="utf-8",
    )

    task = GENERATOR.parse_skill_tasks(tmp_path)[0]
    assert [step.action for step in task.steps] == [
        "Run the tool",
        "Review output example",
        "Review demo execution guidance",
    ]
    assert task.steps[0].code_language == "bash"
    assert task.steps[1].code_language == "markdown"


def test_empty_details_get_role_specific_fallbacks(tmp_path: Path) -> None:
    """Output examples never inherit command-execution placeholder text."""
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo
description: Demo task generation.
---

## Execution

```bash
demo_tool
```
```markdown
## Result
```
""",
        encoding="utf-8",
    )

    task = GENERATOR.parse_skill_tasks(tmp_path)[0]
    assert [step.detail for step in task.steps] == [
        "Run this command with the scoped parameters.",
        "Compare the result with this expected output shape.",
    ]


def test_extract_section_ignores_headings_inside_code_fences() -> None:
    """A Markdown result example cannot truncate its owning section."""
    body = """## Execution

```markdown
## Result

Passed.
```

Keep this trailing guidance.

## Follow-Up

Next step.
"""

    assert GENERATOR._extract_section(body, "Execution") == (
        "```markdown\n## Result\n\nPassed.\n```\n\nKeep this trailing guidance."
    )


def test_extract_section_matches_fence_type_and_length() -> None:
    """Nested/different markers and inline ticks cannot desynchronize scanning."""
    body = """## Execution

````markdown
~~~text
## Nested result
~~~
`````

Inline `~~~` text remains ordinary prose.

## Follow-Up

Next step.
"""

    assert GENERATOR._extract_section(body, "Execution") == (
        "````markdown\n~~~text\n## Nested result\n~~~\n`````\n\n"
        "Inline `~~~` text remains ordinary prose."
    )
