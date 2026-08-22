"""Batched Redis reads for scan-then-fetch listings.

A listing that scans a key pattern and then calls ``client.get(key)`` per
key pays one network round trip per record — the N+1 shape. ``mget_json``
fetches every scanned record in a single ``MGET`` instead, so a listing
costs one round trip regardless of how many keys the scan returned.

Decoding is TOTAL, in the same spirit as ``attune.ops.data._as_int``: a
record that is missing, undecodable, not JSON, or not a JSON object
yields ``None`` for that key ONLY. One malformed record never costs the
whole listing.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

# Cap on keys per MGET. Redis serves one command at a time, so a single
# unbounded MGET over a large scan would block the server for its whole
# duration; chunking keeps each command short while still costing
# ceil(N / _MGET_CHUNK) round trips instead of N.
_MGET_CHUNK = 500


def _decode_key(key: Any) -> str:
    """Decode a scanned key to str (scan_iter yields bytes by default)."""
    if isinstance(key, bytes):
        return key.decode("utf-8", errors="replace")
    return str(key)


def decode_json_object(raw: Any) -> dict[str, Any] | None:
    """Decode one raw Redis value to a dict, or None. Never raises."""
    if not raw:
        return None
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):  # JSONDecodeError subclasses ValueError
        return None
    return value if isinstance(value, dict) else None


def mget_json(client: Any, keys: Iterable[Any]) -> list[tuple[str, dict[str, Any] | None]]:
    """Fetch many JSON records in one round trip per chunk of keys.

    Args:
        client: Redis client (needs ``mget``).
        keys: Keys as returned by ``scan_iter`` — bytes or str.

    Returns:
        ``(decoded_key, record_or_None)`` pairs in the order the keys were
        given. A key whose value is absent or malformed carries ``None``;
        callers skip those records individually.

    Note:
        Errors from ``mget`` itself are NOT swallowed — a broken client is
        a listing-wide failure, exactly as a broken ``get`` was, and every
        caller already handles it.

    """
    decoded_keys = [_decode_key(key) for key in keys]
    records: list[tuple[str, dict[str, Any] | None]] = []

    for start in range(0, len(decoded_keys), _MGET_CHUNK):
        chunk = decoded_keys[start : start + _MGET_CHUNK]
        values = client.mget(chunk)
        for key, raw in zip(chunk, values, strict=False):
            record = decode_json_object(raw)
            if record is None and raw:
                logger.debug("Skipping malformed record at %s", key)
            records.append((key, record))

    return records
