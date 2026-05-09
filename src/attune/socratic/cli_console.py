"""Console formatting and interactive form rendering for Socratic CLI.

Provides colored terminal output and interactive form input collection
for the Socratic Workflow Builder CLI.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys

# Avoid circular import — Form imported for type annotations only
from typing import TYPE_CHECKING, Any

from .forms import FieldType, FormField

if TYPE_CHECKING:
    from .forms import Form


# =============================================================================
# CONSOLE FORMATTING
# =============================================================================


class Console:
    """Simple console output formatting."""

    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
    }

    def __init__(self, use_color: bool = True):
        """Initialize the CLI console renderer.

        Args:
            use_color: Enable ANSI color output (auto-disabled if not a TTY).
        """
        self.use_color = use_color and sys.stdout.isatty()

    def _c(self, color: str, text: str) -> str:
        """Apply color to text."""
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def header(self, text: str) -> None:
        """Print a header."""
        print()
        print(self._c("bold", "=" * 60))
        print(self._c("bold", f"  {text}"))
        print(self._c("bold", "=" * 60))
        print()

    def subheader(self, text: str) -> None:
        """Print a subheader."""
        print()
        print(self._c("cyan", f"\u2500\u2500 {text} \u2500\u2500"))
        print()

    def success(self, text: str) -> None:
        """Print success message."""
        print(self._c("green", f"\u2713 {text}"))

    def error(self, text: str) -> None:
        """Print error message."""
        print(self._c("red", f"\u2717 {text}"))

    def warning(self, text: str) -> None:
        """Print warning message."""
        print(self._c("yellow", f"\u26a0 {text}"))

    def info(self, text: str) -> None:
        """Print info message."""
        print(self._c("blue", f"\u2139 {text}"))

    def dim(self, text: str) -> None:
        """Print dimmed text."""
        print(self._c("dim", text))

    def progress(self, value: float, width: int = 30) -> str:
        """Generate progress bar."""
        filled = int(value * width)
        bar = "\u2593" * filled + "\u2591" * (width - filled)
        return f"[{bar}] {value:.0%}"

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Print a simple table."""
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))

        # Print header
        header_line = " | ".join(self._c("bold", h.ljust(widths[i])) for i, h in enumerate(headers))
        print(header_line)
        print("-" * (sum(widths) + len(widths) * 3 - 1))

        # Print rows
        for row in rows:
            row_line = " | ".join(
                str(cell).ljust(widths[i]) for i, cell in enumerate(row) if i < len(widths)
            )
            print(row_line)


# Module-level console instance
console = Console()


# =============================================================================
# INTERACTIVE FORM RENDERER
# =============================================================================


def render_form_interactive(form: Form, console: Console) -> dict[str, Any]:
    """Render a form and collect user input.

    Args:
        form: Form to render
        console: Console for output

    Returns:
        Dictionary of answers

    """
    console.subheader(form.title)

    if form.description:
        print(form.description)
        print()

    print(console.progress(form.progress))
    print()

    answers: dict[str, Any] = {}

    for field in form.fields:
        # Check visibility
        if not field.should_show(answers):
            continue

        # Render field
        required = " *" if field.validation.required else ""
        print(f"{console._c('bold', field.label)}{required}")

        if field.help_text:
            console.dim(f"  {field.help_text}")

        # Handle by field type
        if field.field_type == FieldType.SINGLE_SELECT:
            answers[field.id] = _input_single_select(field, console)

        elif field.field_type == FieldType.MULTI_SELECT:
            answers[field.id] = _input_multi_select(field, console)

        elif field.field_type == FieldType.BOOLEAN:
            answers[field.id] = _input_boolean(field, console)

        elif field.field_type == FieldType.TEXT_AREA:
            answers[field.id] = _input_text_area(field, console)

        else:  # TEXT, NUMBER, etc.
            answers[field.id] = _input_text(field, console)

        print()

    return answers


def _input_single_select(field: FormField, console: Console) -> str | None:
    """Input for single select field."""
    for i, opt in enumerate(field.options, 1):
        rec = console._c("green", " (Recommended)") if opt.recommended else ""
        print(f"  {i}. {opt.label}{rec}")
        if opt.description:
            console.dim(f"     {opt.description}")

    while True:
        response = input("\n  Enter number: ").strip()

        if not response:
            if not field.validation.required:
                return None
            console.error("This field is required")
            continue

        try:
            idx = int(response) - 1
            if 0 <= idx < len(field.options):
                return field.options[idx].value
            console.error(f"Enter a number between 1 and {len(field.options)}")
        except ValueError:
            console.error("Enter a valid number")


def _input_multi_select(field: FormField, console: Console) -> list[str]:
    """Input for multi select field."""
    for i, opt in enumerate(field.options, 1):
        rec = console._c("green", " (Recommended)") if opt.recommended else ""
        print(f"  {i}. {opt.label}{rec}")
        if opt.description:
            console.dim(f"     {opt.description}")

    while True:
        response = input("\n  Enter numbers (comma-separated): ").strip()

        if not response:
            if not field.validation.required:
                return []
            console.error("Select at least one option")
            continue

        try:
            indices = [int(x.strip()) - 1 for x in response.split(",")]
            selected = []
            for idx in indices:
                if 0 <= idx < len(field.options):
                    selected.append(field.options[idx].value)

            if selected:
                return selected
            console.error("No valid options selected")
        except ValueError:
            console.error("Enter valid numbers separated by commas")


def _input_boolean(field: FormField, console: Console) -> bool:
    """Input for boolean field."""
    while True:
        response = input("  (y/n): ").strip().lower()

        if response in ("y", "yes", "true", "1"):
            return True
        if response in ("n", "no", "false", "0") or (
            not response and not field.validation.required
        ):
            return False
        console.error("Enter 'y' or 'n'")


def _input_text(field: FormField, console: Console) -> str:
    """Input for text field."""
    prompt = f"  {field.placeholder or 'Enter value'}: " if field.placeholder else "  > "

    while True:
        response = input(prompt).strip()

        if not response:
            if not field.validation.required:
                return ""
            console.error("This field is required")
            continue

        # Validate
        is_valid, error = field.validate(response)
        if is_valid:
            return response
        console.error(error)


def _input_text_area(field: FormField, console: Console) -> str:
    """Input for text area field."""
    print("  (Enter text, then press Enter twice to finish)")

    lines: list[str] = []
    empty_count = 0

    while True:
        line = input("  > " if not lines else "    ")

        if not line:
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append("")
        else:
            empty_count = 0
            lines.append(line)

    response = "\n".join(lines).strip()

    if not response and field.validation.required:
        console.error("This field is required")
        return _input_text_area(field, console)

    return response
