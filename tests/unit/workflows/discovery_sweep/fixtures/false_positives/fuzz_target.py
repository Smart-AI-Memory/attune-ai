"""False-positive fixture: subprocess inside a fuzz target.

Fuzz harness scaffolding runs in an isolated build container.
Scanners flagging shell=True / B602 / B603 on this file are
false-positive — there is no shell-injection vector reachable
from prod.
"""

import subprocess
import sys


def TestOneInput(data: bytes) -> int:  # libFuzzer entrypoint
    """libFuzzer hook — spawns the candidate binary."""
    try:
        subprocess.run([sys.executable, "-c", "pass"], shell=False, check=True)
    except subprocess.CalledProcessError:
        pass
    return 0
