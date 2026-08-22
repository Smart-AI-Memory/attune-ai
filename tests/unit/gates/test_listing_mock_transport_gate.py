"""A listing test that stubs only ``get`` asserts nothing.

The telemetry listings read their records with one ``MGET`` instead of a
``get()`` per key. A test that stubs only ``get`` therefore hands the
listing a bare ``Mock`` for ``mget``, which is not iterable — the
resulting ``TypeError`` is swallowed by each listing's function-wide
``except Exception`` and the call returns ``[]`` / ``0`` / ``None``.

Any assertion expecting an empty result then passes **for the wrong
reason**: the payload the test set up is never read, and the logic the
test names never runs. This is not hypothetical — five tests were
silently vacuous this way after the MGET migration, including the only
test guarding ``get_pending_approvals``' "only pending" status filter.

The failure is invisible by construction: tests with POSITIVE assertions
(``assert len(x) == 1``) go red immediately and get fixed, while tests
asserting emptiness are satisfied by the very failure they should catch.
So the suite cannot self-report this class — hence a gate.

Fix a violation by wiring the transport, not by loosening this rule::

    mock_client.get.return_value = ...
    serve_mget_from_get(mock_client)      # replay get() through mget()
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TELEMETRY_TESTS = _REPO_ROOT / "tests" / "unit" / "telemetry"

#: Any of these in a test body (or in a fixture it requests) means the
#: batched transport is served, so the listing reads real records.
_WIRED_MARKERS = ("serve_mget_from_get", "mget", "CountingClient")


def _stubs_nonempty_scan(node: ast.AST) -> bool:
    """True if this function stubs ``scan_iter`` so a listing reaches MGET.

    An empty ``return_value`` cannot reach MGET (the helper short-circuits)
    and a raising ``side_effect`` fails before it, so neither can be
    vacuous — only a scan that actually yields keys qualifies.
    """
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Assign):
            continue
        for target in sub.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr not in ("return_value", "side_effect"):
                continue
            owner = target.value
            if not (isinstance(owner, ast.Attribute) and owner.attr == "scan_iter"):
                continue

            value = sub.value
            if isinstance(value, ast.List | ast.Tuple):
                return bool(value.elts)  # empty scan short-circuits
            if target.attr == "side_effect":
                # A raising side_effect fails before MGET; anything else
                # (a list, a generator) still feeds the listing.
                if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                    if value.func.id.endswith(("Error", "Exception")):
                        return False
                if isinstance(value, ast.Name) and value.id.endswith(("Error", "Exception")):
                    return False
            return True
    return False


def _fixture_sources(scope: ast.AST, source: str) -> dict[str, str]:
    """Map fixture name -> source text for fixtures defined DIRECTLY in ``scope``.

    Deliberately NOT recursive: one file often defines the same fixture name
    in several classes — one wiring the transport, one not — so module and
    class scopes must stay separate or the wrong definition wins and the
    gate reports a false positive.
    """
    out: dict[str, str] = {}
    for node in getattr(scope, "body", []):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if any("fixture" in ast.dump(dec) for dec in node.decorator_list):
            out[node.name] = ast.get_source_segment(source, node) or ""
    return out


def _violations(root: Path | None = None) -> list[str]:
    """Scan ``root`` (default: the telemetry tests) for the vacuity shape.

    ``root`` is a parameter so the self-check below can scan a throwaway
    directory. A test that wrote its fixture INTO the scanned tree would
    be mutating a directory pytest is collecting from — a race under
    xdist and a stray file if the run is killed mid-test.
    """
    root = root or _TELEMETRY_TESTS
    conftest = root / "conftest.py"
    conftest_src = conftest.read_text(encoding="utf-8") if conftest.exists() else ""
    conftest_tree = ast.parse(conftest_src) if conftest_src else ast.parse("")
    conftest_fixtures = _fixture_sources(conftest_tree, conftest_src)

    found: list[str] = []
    for path in sorted(root.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Module-level fixtures only; class fixtures are added per class
        # below. A name may be defined in several classes (one wiring the
        # transport, one not), so a flat map would resolve to the wrong one.
        module_fixtures = {
            **conftest_fixtures,
            **_fixture_sources(tree, source),
        }

        # (test node, fixtures visible to it) — class scope shadows module.
        scoped: list[tuple[ast.AST, dict[str, str]]] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                visible = {**module_fixtures, **_fixture_sources(node, source)}
                for item in ast.walk(node):
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        scoped.append((item, visible))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                scoped.append((node, module_fixtures))

        for node, fixtures in scoped:
            if not node.name.startswith("test_"):
                continue
            if not _stubs_nonempty_scan(node):
                continue

            body = ast.get_source_segment(source, node) or ""
            # The transport may be served in the test itself, or by any
            # fixture the test requests (possibly via a fixture chain).
            scopes = [body]
            pending = [a.arg for a in node.args.args if a.arg != "self"]
            seen: set[str] = set()
            while pending:
                name = pending.pop()
                if name in seen or name not in fixtures:
                    continue
                seen.add(name)
                scopes.append(fixtures[name])
                fixture_node = ast.parse(fixtures[name]).body[0]
                if isinstance(fixture_node, ast.FunctionDef | ast.AsyncFunctionDef):
                    pending.extend(a.arg for a in fixture_node.args.args if a.arg != "self")

            if not any(marker in scope for scope in scopes for marker in _WIRED_MARKERS):
                found.append(f"{path.name}::{node.name} (line {node.lineno})")
    return found


def test_listing_tests_serve_the_batched_transport():
    """A telemetry test feeding a non-empty scan must also serve MGET."""
    violations = _violations()
    assert not violations, (
        "These tests stub a non-empty scan_iter but never serve mget, so the "
        "listing raises 'Mock object is not iterable' into its own except "
        "handler and returns empty — any emptiness assertion passes "
        "vacuously.\n  " + "\n  ".join(violations) + "\n\n"
        "Fix: call serve_mget_from_get(mock_client) after setting up get(), "
        "or use CountingClient. Do not relax this gate."
    )


def test_gate_detects_a_planted_violation(tmp_path):
    """The gate must actually fire — a green run should mean a clean tree."""
    (tmp_path / "test_planted_vacuous.py").write_text(
        "from unittest.mock import Mock\n\n\n"
        "def test_planted():\n"
        "    c = Mock()\n"
        '    c.scan_iter.return_value = [b"k:1"]\n'
        "    c.get.return_value = None\n",
        encoding="utf-8",
    )

    assert any("test_planted_vacuous.py" in v for v in _violations(tmp_path))


def test_gate_accepts_a_wired_test(tmp_path):
    """The counterpart: serving the transport clears the violation."""
    (tmp_path / "test_planted_wired.py").write_text(
        "from unittest.mock import Mock\n\n"
        "from tests.unit.telemetry.conftest import serve_mget_from_get\n\n\n"
        "def test_planted():\n"
        "    c = Mock()\n"
        '    c.scan_iter.return_value = [b"k:1"]\n'
        "    c.get.return_value = None\n"
        "    serve_mget_from_get(c)\n",
        encoding="utf-8",
    )

    assert _violations(tmp_path) == []
