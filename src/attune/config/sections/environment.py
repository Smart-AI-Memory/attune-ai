"""Environment configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class EnvironmentConfig:
    """Environment and display configuration.

    Controls logging, output formatting, and shell integration settings.

    Attributes:
        log_level: Logging verbosity level.
        log_file: Path to log file (None for no file logging).
        color_output: Enable colored terminal output.
        unicode_output: Enable unicode characters in output.
        editor: Default editor for file editing.
        pager: Default pager for long output.
        shell: Default shell for command execution.
        timezone: Timezone for timestamps.
    """

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str | None = None
    color_output: bool = True
    unicode_output: bool = True
    editor: str = "code"
    pager: str = "less"
    shell: str = "/bin/bash"
    timezone: str = "UTC"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "log_level": self.log_level,
            "log_file": self.log_file,
            "color_output": self.color_output,
            "unicode_output": self.unicode_output,
            "editor": self.editor,
            "pager": self.pager,
            "shell": self.shell,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnvironmentConfig":
        """Create from dictionary."""
        return cls(
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file"),
            color_output=data.get("color_output", True),
            unicode_output=data.get("unicode_output", True),
            editor=data.get("editor", "code"),
            pager=data.get("pager", "less"),
            shell=data.get("shell", "/bin/bash"),  # nosec B604 -- dataclass field, not subprocess
            timezone=data.get("timezone", "UTC"),
        )
