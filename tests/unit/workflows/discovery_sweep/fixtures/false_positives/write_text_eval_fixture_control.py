"""Control: real eval() outside any .write_text() call.

A scanner finding on the eval() line below is a true positive.
The rule must NOT fire here.
"""


def evaluate_user_input(expr: str) -> object:
    """Run eval() on caller-supplied text."""
    return eval(expr)
