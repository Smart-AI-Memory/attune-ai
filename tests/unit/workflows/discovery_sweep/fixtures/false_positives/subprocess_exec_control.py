"""Control: real eval() call.

This IS a dangerous_eval. The rule must NOT fire here just
because the line happens to also have the word 'subprocess'
elsewhere.
"""


def evaluate(expr: str, subprocess_unused: str = "") -> object:
    """Evaluate ``expr`` with eval()."""
    return eval(expr)
