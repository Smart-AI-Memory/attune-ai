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

#: Call names that read the environment when their first argument is
#: a guarded constant.
_ENV_CALL_ATTRS = frozenset({"get", "getenv"})
_ENV_CALL_NAMES = frozenset({"getenv", "get_attune_env"})


def _violations_in_source(source: str, rel_path: str) -> list[tuple[str, int, str]]:
    """All guarded-name env reads in one file's source."""
    tree = ast.parse(source)
    out: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_env_call = (isinstance(func, ast.Attribute) and func.attr in _ENV_CALL_ATTRS) or (
                isinstance(func, ast.Name) and func.id in _ENV_CALL_NAMES
            )
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


def test_resolver_module_itself_reads_env():
    """Sanity: the scanner sees the resolver's own reads (scope, not
    blindness, is why the corpus test passes)."""
    resolver_src = (REPO_ROOT / RESOLVER_MODULE).read_text(encoding="utf-8")
    assert _violations_in_source(resolver_src, RESOLVER_MODULE), (
        "scanner found no env reads in the resolver module — the "
        "scanner is broken or the resolver moved; update RESOLVER_MODULE"
    )


def test_allowlist_is_empty():
    """rct-4 AC: the allowlist ships empty. Additions are exceptional
    and need a justifying comment at the entry."""
    assert ALLOWLIST == frozenset()
