"""Multi-actor bulletin board — shared in-flight workflow state.

See docs/specs/multi-actor-bulletin/requirements.md for the spec.
"""

from .actor_id import resolve_actor
from .file_backend import FileBulletinBackend
from .protocol import BulletinBackend, BulletinEntry

__all__ = [
    "BulletinBackend",
    "BulletinEntry",
    "FileBulletinBackend",
    "resolve_actor",
]
