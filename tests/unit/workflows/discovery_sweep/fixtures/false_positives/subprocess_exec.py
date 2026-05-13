"""False-positive fixture: asyncio.create_subprocess_exec.

Scanners that substring-match on 'exec' flag this safe asyncio
helper as dangerous_eval. It is NOT eval/exec.
"""

import asyncio


async def run_ls() -> int:
    """Spawn /bin/ls via asyncio's safe exec helper."""
    proc = await asyncio.create_subprocess_exec("/bin/ls", "-1")
    return await proc.wait()
