"""Drift guard: Redis connection env vars are read ONLY by the resolver.

redis-config-truth rct-4 AC: after the consumer migration, ANY direct
read of the eight connection env names outside
``src/attune/memory/config.py`` (the canonical resolver home) fails
CI. Covered access forms: ``os.environ.get``, ``os.environ[...]``,
``os.getenv`` (including ``from os import getenv``), and the
``get_attune_env`` compat helper — each proven caught by a planted
violation below.

The allowlist is seeded EMPTY (rct-4 AC). Adding an entry is the
exception and needs a justifying comment naming why the resolver
cannot serve that call site.

Toggles (REDIS_MODE, ATTUNE_REDIS_MOCK, REDIS_ENABLED, SSL/timeout
settings, ...) are NOT connection components and stay readable.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The eight connection component names (R1). Everything else
#: REDIS_-prefixed is a toggle or tuning knob, not a component.
GUARDED_NAMES = frozenset(
    {
        "REDIS_URL",
        "REDIS_PRIVATE_URL",
        "REDIS_PUBLIC_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_PASSWORD",
        "REDIS_USER",
    }
)

#: The one sanctioned home for connection-env reads.
RESOLVER_MODULE = "src/attune/memory/config.py"

#: Repo-relative paths allowed to read connection names directly.
#: SEEDED EMPTY (rct-4 AC) — additions need a justifying comment.
ALLOWLIST: frozenset[str] = frozenset()

#: Directories scanned (production code only — tests set env freely).
SCAN_ROOTS = ("src/attune", "attune_redis", "plugin")

#: Bare call names that read the environment when their first
#: argument is a guarded constant.
_ENV_CALL_NAMES = frozenset({"getenv", "get_attune_env"})


def _is_environ_ref(node: ast.AST) -> bool:
    """True for ``environ`` / ``os.environ`` references."""
    return (isinstance(node, ast.Attribute) and node.attr == "environ") or (
        isinstance(node, ast.Name) and node.id == "environ"
    )


def _violations_in_source(source: str, rel_path: str) -> list[tuple[str, int, str]]:
    """All guarded-name env reads in one file's source."""
    tree = ast.parse(source)
    out: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Receiver-aware (codex D11 lane): ``.get`` counts only on
            # an ``environ`` receiver, so ordinary dict/config lookups
            # like ``parsed.get("REDIS_URL")`` never false-fire.
            # ``.getenv`` counts on any receiver (os.getenv, aliased
            # module); bare ``getenv`` / ``get_attune_env`` count too.
            if isinstance(func, ast.Attribute):
                is_env_call = (func.attr == "get" and _is_environ_ref(func.value)) or (
                    func.attr == "getenv"
                )
            elif isinstance(func, ast.Name):
                is_env_call = func.id in _ENV_CALL_NAMES
            else:
                is_env_call = False
            if not is_env_call or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and first.value in GUARDED_NAMES:
                out.append((rel_path, node.lineno, str(first.value)))
        elif isinstance(node, ast.Subscript):
            container = node.value
            is_environ = (isinstance(container, ast.Attribute) and container.attr == "environ") or (
                isinstance(container, ast.Name) and container.id == "environ"
            )
            if not is_environ:
                continue
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in GUARDED_NAMES:
                out.append((rel_path, node.lineno, str(key.value)))
    return out


def _scan_tree() -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for py in sorted(base.rglob("*.py")):
            rel = py.relative_to(REPO_ROOT).as_posix()
            if rel == RESOLVER_MODULE or rel in ALLOWLIST:
                continue
            if "/tests/" in rel:
                continue
            try:
                source = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                violations.extend(_violations_in_source(source, rel))
            except SyntaxError:
                continue
    return violations


def test_no_connection_env_reads_outside_resolver():
    """The rct-4 ratchet: the corpus carries ZERO direct reads."""
    violations = _scan_tree()
    assert not violations, (
        "Direct Redis connection-env reads outside the resolver "
        f"({RESOLVER_MODULE}). Route them through "
        "resolve_redis_connection() — its URL carries merged "
        "credentials and its source_map records provenance:\n  "
        + "\n  ".join(f"{f}:{ln} reads {name}" for f, ln, name in violations)
    )


#: One planted violation per access form — the guard must catch EACH.
_PLANTED_FORMS = {
    "environ_get": 'import os\nurl = os.environ.get("REDIS_URL")\n',
    "environ_get_with_default": 'import os\nu = os.environ.get("REDIS_URL", "redis://x")\n',
    "environ_subscript": 'import os\npw = os.environ["REDIS_PASSWORD"]\n',
    "os_getenv": 'import os\nhost = os.getenv("REDIS_HOST")\n',
    "component_var_read": 'import os\nport = os.getenv("REDIS_PORT", "6379")\n',
    "bare_getenv_import": 'from os import getenv\ndb = getenv("REDIS_DB")\n',
    "compat_helper": (
        "from attune.config.env_compat import get_attune_env\n"
        'host = get_attune_env("REDIS_HOST", "")\n'
    ),
    "environ_alias_subscript": 'from os import environ\nuser = environ["REDIS_USER"]\n',
}


@pytest.mark.parametrize("form", sorted(_PLANTED_FORMS))
def test_planted_violation_is_caught(form: str):
    """AC proof: every access form fires the guard."""
    hits = _violations_in_source(_PLANTED_FORMS[form], f"planted/{form}.py")
    assert hits, f"planted {form} violation was NOT caught by the scanner"


def test_resolver_module_exists_and_holds_the_resolver():
    """Sanity: the scope exclusion points at a real module that still
    defines the canonical resolver (non-blindness is proven by the
    planted-violation params above)."""
    resolver_path = REPO_ROOT / RESOLVER_MODULE
    assert resolver_path.is_file(), f"{RESOLVER_MODULE} moved — update RESOLVER_MODULE"
    assert "def resolve_redis_connection(" in resolver_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "snippet",
    [
        # Ordinary mapping lookups must NOT fire (codex D11 lane —
        # receiver-aware matching).
        'parsed = {}\nurl = parsed.get("REDIS_URL")\n',
        'cfg = {}\npw = cfg.get("REDIS_PASSWORD", "")\n',
        'row = {}\nhost = row["x"] if "REDIS_HOST" in row else None\n',
    ],
    ids=["dict_get", "dict_get_default", "membership"],
)
def test_non_env_lookups_do_not_fire(snippet: str):
    assert _violations_in_source(snippet, "planted/negative.py") == []


def test_allowlist_is_empty():
    """rct-4 AC: the allowlist ships empty. Additions are exceptional
    and need a justifying comment at the entry."""
    assert ALLOWLIST == frozenset()


def test_suite_scrubs_every_guarded_connection_var():
    """Drift guard for ``_scrub_redis_connection_env`` (tests/conftest.py).

    A developer shell exporting any of the eight leaks into resolution:
    the resolver MERGES what a test did not set, so a passwordless
    ``REDIS_URL`` patched by a test silently becomes
    ``redis://:<ambient secret>@host`` — the assertion fails and the real
    password lands in pytest output. Asserted on ``os.environ`` because
    the autouse fixture has already run for this test.
    """
    import os

    from tests.conftest import _REDIS_CONNECTION_ENV

    # REDIS_HOST is the one deliberate exclusion: the conftest loopback
    # pin owns it (windows-exit139 hang class). Asserted as an exact set
    # difference so ADDING a guarded name without scrubbing it fails here.
    assert GUARDED_NAMES - _REDIS_CONNECTION_ENV == {"REDIS_HOST"}, (
        "the conftest scrub list and this gate's GUARDED_NAMES have drifted "
        "— a guarded name that is not scrubbed is an unscrubbed leak"
    )
    still_set = sorted(n for n in _REDIS_CONNECTION_ENV if n in os.environ)
    assert still_set == [], f"suite isolation regressed — still set: {still_set}"
    # The excluded one must still be pinned, not merely absent.
    assert os.environ.get("REDIS_HOST") not in (None, "", "localhost")
