"""False-positive fixture: dirs[:] inside os.walk loop.

The scanner flags ``dirs[:] = [...]`` as a memory leak / large
list copy, but this pattern is REQUIRED for in-place dir
filtering during os.walk traversal.
"""

import os


def find_python_files(root: str) -> list[str]:
    """Walk ``root`` and return all .py file paths, skipping caches."""
    matches: list[str] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".venv"}]
        for f in files:
            if f.endswith(".py"):
                matches.append(os.path.join(dirpath, f))
    return matches
