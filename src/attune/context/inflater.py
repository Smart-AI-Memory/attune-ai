"""Context Inflater for Attune AI.

Inflates AST skeletons back into full source code representations when
an agent initiates code modifications on a file.
"""

from collections.abc import Iterable

# Canonical (provider-neutral) mutating action names, matched
# case-insensitively. Provider adapters that use different tool names
# (e.g. an IDE's ``replace_file_content``) pass their own set via the
# ``mutating_actions`` constructor argument.
DEFAULT_MUTATING_ACTIONS: frozenset[str] = frozenset({"edit", "write", "multiedit", "notebookedit"})


class ContextInflater:
    """Manages on-demand context expansion from skeleton to full source."""

    def __init__(
        self,
        full_source_repository: dict[str, str] | None = None,
        mutating_actions: Iterable[str] | None = None,
    ) -> None:
        """Initialize ContextInflater.

        Args:
            full_source_repository: Optional map of path -> full source code.
            mutating_actions: Optional override for the set of tool action
                names treated as mutating (case-insensitive).
        """
        self.repository = full_source_repository or {}
        self.mutating_actions = frozenset(
            a.lower() for a in (mutating_actions or DEFAULT_MUTATING_ACTIONS)
        )

    def register_file(self, file_path: str, full_source: str) -> None:
        """Registers a file's full source code in the repository."""
        self.repository[file_path] = full_source

    def inflate_if_requested(
        self,
        file_path: str,
        current_context: str,
        tool_action: str,
    ) -> str:
        """Expands skeleton context to full source if tool action mutates files.

        Args:
            file_path: Path of file being acted upon.
            current_context: Currently held context (skeleton or full).
            tool_action: Name of the tool action (e.g. ``Edit``, ``Write``).

        Returns:
            Full source code if mutating action, else original context.
        """
        if tool_action.lower() in self.mutating_actions and file_path in self.repository:
            return self.repository[file_path]

        return current_context
