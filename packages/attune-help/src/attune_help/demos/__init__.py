"""Demo templates showing the per-feature help format.

Contains a ``security-audit`` feature with concept, task,
and reference templates.  Copy the feature directory into
your project's ``.help/templates/`` as a starting point.
"""

from pathlib import Path


def get_demo_path() -> Path:
    """Return path to the bundled demo templates directory."""
    return Path(__file__).resolve().parent
