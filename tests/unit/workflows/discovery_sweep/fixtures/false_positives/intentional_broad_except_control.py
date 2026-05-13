"""Control: broad except WITHOUT noqa/INTENTIONAL markers.

This is the antipattern coding-standards.md prohibits. The rule
must NOT fire here.
"""


def load_config(path: str) -> dict:
    """Load config — broad except masks real failures."""
    try:
        import json

        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
