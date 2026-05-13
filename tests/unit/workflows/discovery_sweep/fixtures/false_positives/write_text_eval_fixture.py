"""False-positive fixture: eval inside a .write_text() call.

The eval() appears in TEST DATA written to a temp file —
fixture content for a scanner test. The scanner sees the
string 'eval(' but it's not actually executable code.
"""

from pathlib import Path


def setup_fixture(tmp_path: Path) -> Path:
    """Write a Python source file containing eval() as test data."""
    fixture = tmp_path / "dangerous_input.py"
    fixture.write_text(
        """
def unsafe(code):
    # Scanner should flag this in a real source file
    return eval(code)
"""
    )
    return fixture
