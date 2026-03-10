"""Add # noqa: BLE001 to all unannotated except Exception lines."""

import re
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src" / "attune"
PATTERN = re.compile(r"^(\s*except\s+Exception\b.*?)(\s*#.*)?$")
NOQA = "# noqa: BLE001"

total_changed = 0
files_changed = 0

for py_file in sorted(SRC_DIR.rglob("*.py")):
    lines = py_file.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = False
    new_lines = []
    for line in lines:
        stripped = line.rstrip("\n\r")
        m = PATTERN.match(stripped)
        if m and NOQA not in stripped:
            # Add noqa annotation
            if m.group(2):  # existing comment
                new_line = stripped + "  " + NOQA
            else:
                new_line = stripped + "  " + NOQA
            new_lines.append(new_line + "\n")
            changed = True
            total_changed += 1
            print(f"  {py_file.relative_to(SRC_DIR.parent.parent)}:{lines.index(line)+1}")
        else:
            new_lines.append(line)
    if changed:
        py_file.write_text("".join(new_lines), encoding="utf-8")
        files_changed += 1

print(f"\nDone: {total_changed} lines changed across {files_changed} files.")
