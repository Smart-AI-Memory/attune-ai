"""Pin the ``cryptography`` PyO3 extension once, at pytest startup.

Why this exists
---------------
``cryptography`` ships its core as a Rust/PyO3 extension
(``cryptography.hazmat.bindings._rust``). PyO3 extensions built for
CPython 3.8-or-older ABI may be **initialized only once per interpreter
process**; a second initialization raises::

    ImportError: PyO3 modules compiled for CPython 3.8 or older may only
    be initialized once per interpreter process

That second init is normally impossible, but it happens during *serial*
``pytest --cov`` runs whose ``--cov`` target is an ``attune.memory.*``
module. pytest-cov imports the coverage source at startup (before any
conftest). For a memory target that import transitively eager-loads
``redis`` -> ``redis.auth.token`` -> ``PyJWT`` -> ``cryptography``,
initializing ``_rust`` once. That startup import then unwinds and evicts
the cryptography modules from ``sys.modules`` while PyO3's *process-global*
once-only counter stays incremented. When ``tests/conftest.py`` later
re-imports the chain, ``cryptography`` is re-imported, ``_rust`` is
initialized a second time, and the import fails. The failure is swallowed
by ``attune.memory.encryption``'s ``except ImportError`` guard, leaving
``HAS_ENCRYPTION = False`` for the whole session, so every test that builds
``EncryptionManager(master_key=...)`` errors.

CI is unaffected because it measures coverage under xdist (``-n auto``),
which isolates workers; this only bites serial ``--cov`` runs used for
local QA coverage measurement.

The fix
-------
Import ``cryptography`` exactly once, cleanly, at pytest startup -- before
pytest-cov imports the coverage source. This module is loaded as a
``pytest11`` plugin, so its top-level import runs while pytest loads
setuptools entry points, which is earlier than pytest-cov's source import.
With ``_rust`` already cached, every later import (the unwinding startup
import, conftest, the test bodies) is a cache hit and never re-initializes
the extension.

The import is best-effort: if ``cryptography`` is genuinely absent, the
guard does nothing and ``HAS_ENCRYPTION`` is legitimately ``False``.
"""

try:  # noqa: SIM105 - explicit guard is clearer than contextlib.suppress here
    import cryptography.exceptions  # noqa: F401
    import cryptography.hazmat.primitives.ciphers.aead  # noqa: F401
except ImportError:
    # INTENTIONAL: cryptography is optional; if it is truly missing the
    # encryption layer is correctly disabled and there is nothing to pin.
    pass
