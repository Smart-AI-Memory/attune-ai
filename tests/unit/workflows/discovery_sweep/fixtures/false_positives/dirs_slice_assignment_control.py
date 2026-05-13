"""Control: dirs[:] OUTSIDE an os.walk loop.

Same syntax, different context — this IS an unnecessary copy
because the surrounding code doesn't depend on in-place
modification. The rule must NOT fire here.
"""


def reverse_then_uppercase(dirs: list[str]) -> list[str]:
    """Reverse a list of names and return upper-cased copies.

    The ``dirs[:] = ...`` rebind here doesn't filter os.walk —
    it's just a slice copy and could equally be ``dirs = ...``.
    """
    dirs[:] = [d.upper() for d in dirs[::-1]]
    return dirs
