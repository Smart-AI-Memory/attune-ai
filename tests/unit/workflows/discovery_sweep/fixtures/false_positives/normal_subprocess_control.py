"""Control: subprocess in a normal source file (not a fuzz target).

The file lives outside any fuzz path. The rule must NOT fire
here — this IS a potential shell-injection if user input flows
to ``cmd``.
"""

import subprocess


def run_user_cmd(cmd: str) -> int:
    """Run a user-supplied command. shell=True is dangerous."""
    return subprocess.call(cmd, shell=True)
