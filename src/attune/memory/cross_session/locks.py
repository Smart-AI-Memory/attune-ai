"""Owner-checked lock mutations, evaluated server-side.

A lock's value names its owner, and a lock carries a TTL — so it can
vanish at any moment, including between a client's read and the client's
next command. Releasing with ``GET`` then ``DELETE`` is check-then-act
across two round trips: the lock can expire and be re-acquired by
someone else in the window, and the delete then removes THEIR lock
(library-review H6, the release-side sibling of H2's acquire-side fix).

Both helpers here compare and mutate inside one Redis ``EVAL``, so the
server performs the whole operation with nothing interleaved. Note that
``client.eval`` is the Redis EVAL command — a script sent to the server —
and is unrelated to Python's built-in ``eval``, which this project
forbids. The scripts are module-level constants; no caller-supplied text
is ever executed.

Encoding note: redis-py encodes ``str``/``int`` arguments to UTF-8 on
the way out, so the Lua comparison is bytes-against-bytes on values that
were written through the same encoding path. Passing the owner exactly
as it was stored is therefore sufficient, and the helpers work whether
or not the client sets ``decode_responses`` (the reply is an integer).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

#: Delete the key only if it still holds the expected owner.
_RELEASE_IF_OWNER = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

#: Re-arm the TTL only if the key still holds the expected owner.
_REFRESH_IF_OWNER = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


def release_if_owner(client: Any, lock_key: str, owner: Any) -> bool:
    """Delete ``lock_key`` iff ``owner`` still holds it.

    Args:
        client: Redis client, or None when the memory layer is absent.
        lock_key: Full Redis key of the lock.
        owner: The owner value as it was written at acquisition time.

    Returns:
        True if this owner's lock was released, False otherwise —
        including when the lock had already expired or changed hands.

    """
    if client is None:
        return False
    return bool(client.eval(_RELEASE_IF_OWNER, 1, lock_key, owner))


def refresh_if_owner(client: Any, lock_key: str, owner: Any, ttl_seconds: int) -> bool:
    """Re-arm ``lock_key``'s TTL iff ``owner`` still holds it.

    Refreshing without the check keeps a lock alive from the outside
    after its holder has lost it, so the TTL stops tracking the live
    owner's liveness — the one thing a TTL on a singleton lock is for.

    Args:
        client: Redis client, or None when the memory layer is absent.
        lock_key: Full Redis key of the lock.
        owner: The owner value as it was written at acquisition time.
        ttl_seconds: New TTL to set.

    Returns:
        True if this owner's lock was extended, False otherwise.

    """
    if client is None:
        return False
    return bool(client.eval(_REFRESH_IF_OWNER, 1, lock_key, owner, ttl_seconds))
