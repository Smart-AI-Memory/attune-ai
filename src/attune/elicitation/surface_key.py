"""Durable installation authentication for ephemeral interaction receipts.

Only the key persists, never sessions, answers or receipt records. Publication
uses a complete private temporary file and a no-replace hard link, so concurrent
servers converge on one key and an interrupted writer cannot publish a short key.
"""

from __future__ import annotations

import os
import secrets
import stat
import tempfile
from pathlib import Path

from attune.security.path_validation import _validate_file_path


def _private_entry(info: os.stat_result, *, directory: bool = False) -> None:
    valid_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not valid_type:
        raise ValueError("receipt authentication entry has an unsafe file type")
    if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError("receipt authentication entry must be owned and private")


def load_installation_key(attune_home: Path) -> bytes:
    """Load/create a private 32-byte key beneath the server's configured home.

    The home comes from installation configuration, never a tool argument.
    Existing corrupt, public or symlink entries fail closed; they are not replaced.
    This POSIX adapter checks ownership/modes. Windows remains unavailable until
    a credential-store or verified private-ACL adapter is supplied. A malicious
    process running as the same account is outside this filesystem boundary.
    """
    if os.name != "posix":
        raise OSError("private receipt-key storage is not available on this platform")
    home = _validate_file_path(str(attune_home))
    home.mkdir(parents=True, exist_ok=True)
    directory = home / "surface-auth"
    # Do not resolve away a symlink before checking the dedicated private directory.
    directory.mkdir(mode=0o700, exist_ok=True)
    _private_entry(directory.lstat(), directory=True)
    path = directory / "receipt.key"
    _validate_file_path(str(path), str(directory))
    if not path.exists() and not path.is_symlink():
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(secrets.token_bytes(32))
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                # Another startup published a complete key first.
                pass
        finally:
            if temporary_path is not None:
                temporary_path.unlink()
    before = path.lstat()
    _private_entry(before)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        _private_entry(opened)
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("receipt authentication key changed while opening")
        key = source.read(33)
    if len(key) != 32:
        raise ValueError("receipt authentication key must contain exactly 32 bytes")
    return key
