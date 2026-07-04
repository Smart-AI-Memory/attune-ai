"""Guards for website version/accuracy claims.

Lives flat in tests/unit/ (NOT tests/unit/website/) because pytest.ini's
``norecursedirs`` excludes any ``website`` directory — a subdir there
would be silently uncollected (caught by test_workflow_yaml's
norecursedirs guard).

Three layers:

1. **Deterministic version sync, network-free** — the attune-ai version
   claimed in ``website/lib/features.ts`` (and the homepage badge) MUST
   equal this repo's own ``pyproject.toml`` version. This is the guard
   that prevents the exact drift caught 2026-06-28 (website stuck at
   8.7.0 while the package shipped 9.1.0). It runs in the normal suite —
   so any release that advances pyproject past the website turns this red.

2. **Hermetic tests of the PyPI audit script** —
   ``scripts/audit_website_versions.py`` parses the PRODUCTS list and
   compares every package (incl. external attune-help/-author) to PyPI;
   here its parse + compare logic is exercised with an injected fetch
   (no network).

3. **Deterministic count sync, network-free** — every field of
   ``features.ts`` ``CAPABILITIES`` MUST equal the live Python registry
   it claims to mirror (skills → ``plugin/skills/`` dirs; workflows →
   multi-stage ``list_workflows()``; wizards → ``list_wizards()``;
   mcpTools → ``tool_schemas`` ``get_*_tools()`` total; templateKinds →
   ``attune_author.generator._ALL_TEMPLATE_NAMES``). This closes the
   blind spot that let the website advertise 17 skills while the plugin
   shipped 23: the version-only guard (Layer 1) was green the whole time
   because it never looked at the counts.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FEATURES = REPO / "website" / "lib" / "features.ts"
HOMEPAGE = REPO / "website" / "app" / "page.tsx"
PYPROJECT = REPO / "pyproject.toml"

SCRIPT_PATH = REPO / "scripts" / "audit_website_versions.py"


def _pkg_version() -> str:
    match = re.search(r'^version = "(\d+\.\d+\.\d+)"', PYPROJECT.read_text(encoding="utf-8"), re.M)
    assert match, 'pyproject.toml: no `version = "X.Y.Z"` line'
    return match.group(1)


# --- Layer 1: deterministic self-version guard ------------------------


@pytest.mark.skipif(not FEATURES.is_file(), reason="website/ not present")
class TestFeaturesVersionSync:
    def test_attune_ai_product_versions_match_package(self):
        pkg = _pkg_version()
        text = FEATURES.read_text(encoding="utf-8")
        pairs = re.findall(r'pypiName:\s*"([^"]+)",\s+version:\s*"([^"]+)"', text)
        attune = {v for name, v in pairs if name == "attune-ai"}
        assert attune, "no attune-ai product entry found in features.ts"
        assert attune == {pkg}, (
            f"features.ts attune-ai version(s) {attune} != package {pkg} — "
            "bump website/lib/features.ts on release"
        )

    @pytest.mark.skipif(not HOMEPAGE.is_file(), reason="homepage not present")
    def test_homepage_badge_includes_package_version(self):
        pkg = _pkg_version()
        found = set(re.findall(r"v(\d+\.\d+\.\d+)", HOMEPAGE.read_text(encoding="utf-8")))
        assert pkg in found, (
            f"homepage badge versions {found} do not include package {pkg} — "
            "update the <span>vX.Y.Z</span> badge in website/app/page.tsx"
        )


# --- Layer 2: hermetic tests of the PyPI audit script -----------------


@pytest.fixture(scope="module")
def audit_module():
    spec = importlib.util.spec_from_file_location("_audit_website_versions", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE = """
export const PRODUCTS = [
  {
    id: "attune-ai",
    pypiName: "attune-ai",
    version: "9.1.0",
  },
  {
    id: "attune-help",
    pypiName: "attune-help",
    version: "0.11.1",
  },
];
"""


class TestAuditScript:
    def test_parse_products_extracts_pairs_in_order(self, audit_module):
        pairs = audit_module.parse_products(SAMPLE)
        assert pairs == [("attune-ai", "9.1.0"), ("attune-help", "0.11.1")]

    def test_audit_flags_drift(self, audit_module):
        rows = audit_module.audit(SAMPLE, fetch=lambda pkg: "9.9.9")
        assert {r["package"]: r["status"] for r in rows} == {
            "attune-ai": "drift",
            "attune-help": "drift",
        }

    def test_audit_ok_when_matching(self, audit_module):
        latest = {"attune-ai": "9.1.0", "attune-help": "0.11.1"}
        rows = audit_module.audit(SAMPLE, fetch=lambda pkg: latest[pkg])
        assert all(r["status"] == "ok" for r in rows)

    def test_network_failure_is_unverified_not_drift(self, audit_module):
        rows = audit_module.audit(SAMPLE, fetch=lambda pkg: None)
        assert all(r["status"] == "unverified" for r in rows)

    def test_one_fetch_per_distinct_package(self, audit_module):
        calls = {"n": 0}

        def counting_fetch(pkg):
            calls["n"] += 1
            return "9.1.0"

        dup = SAMPLE + SAMPLE  # attune-ai + attune-help appear twice
        audit_module.audit(dup, fetch=counting_fetch)
        assert calls["n"] == 2  # cached: one lookup per distinct name

    def test_site_ahead_of_pypi_is_ahead_not_drift(self, audit_module):
        """Regression for the 9.6.0 release-prep collision: the prep PR
        bumps features.ts BEFORE publish, so site > PyPI is a release in
        flight — advisory ``ahead``, never a failing ``drift``. Site
        BEHIND PyPI (the 2026-06-28 staleness bug) must stay drift."""
        latest = {"attune-ai": "9.0.0", "attune-help": "0.11.0"}
        rows = audit_module.audit(SAMPLE, fetch=lambda pkg: latest[pkg])
        assert all(r["status"] == "ahead" for r in rows)

    def test_ahead_exits_zero_drift_exits_one(self, audit_module, tmp_path):
        import unittest.mock as mock

        features = tmp_path / "features.ts"
        features.write_text(SAMPLE, encoding="utf-8")
        # every site version AHEAD of PyPI -> advisory only -> exit 0
        ahead = {"attune-ai": "9.0.0", "attune-help": "0.11.0"}
        with mock.patch.object(audit_module, "pypi_latest", ahead.__getitem__):
            assert audit_module.main(["--features", str(features)]) == 0
        # every site version BEHIND PyPI -> staleness bug -> exit 1
        with mock.patch.object(audit_module, "pypi_latest", lambda pkg: "9.9.9"):
            assert audit_module.main(["--features", str(features)]) == 1

    def test_unparseable_pypi_version_stays_drift(self, audit_module):
        rows = audit_module.audit(SAMPLE, fetch=lambda pkg: "not-a-version")
        assert all(r["status"] == "drift" for r in rows)


# --- Layer 3: deterministic CAPABILITIES count sync -------------------


def _capabilities() -> dict[str, int]:
    """Parse the integer fields of features.ts ``CAPABILITIES``."""
    text = FEATURES.read_text(encoding="utf-8")
    block = re.search(r"export const CAPABILITIES = \{(.*?)\} as const;", text, re.S)
    assert block, "CAPABILITIES object not found in features.ts"
    caps = {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d+)", block.group(1))}
    assert caps, "CAPABILITIES parsed empty — check the object shape"
    return caps


def _live_skill_count() -> int:
    skills_dir = REPO / "plugin" / "skills"
    return sum(1 for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


@pytest.mark.skipif(not FEATURES.is_file(), reason="website/ not present")
class TestCapabilityCountsSync:
    """features.ts CAPABILITIES MUST equal the live registries it mirrors.

    The mapping is documented in the CAPABILITIES doc-comment in
    features.ts. Each field is checked independently so a drift names the
    exact count that went stale. Registries are imported lazily inside
    each test (no import cost at collection, no failure if an optional
    registry is absent).
    """

    def test_skills_count_matches_plugin_dir(self):
        assert _capabilities()["skills"] == _live_skill_count(), (
            "features.ts CAPABILITIES.skills != plugin/skills/ dir count — "
            "update website/lib/features.ts (and the prose on faq/docs/home). "
            "This is the exact drift caught 2026-06-28 (advertised 17, shipped 23)."
        )

    def test_workflows_count_matches_registry(self):
        from attune.workflows import list_workflows

        live = sum(1 for w in list_workflows() if w.get("stages"))
        assert _capabilities()["workflows"] == live, (
            f"CAPABILITIES.workflows != live multi-stage workflow count ({live}) — "
            "update website/lib/features.ts"
        )

    def test_wizards_count_matches_registry(self):
        from attune.wizards import list_wizards

        live = len(list_wizards())
        assert _capabilities()["wizards"] == live, (
            f"CAPABILITIES.wizards != live list_wizards() count ({live}) — "
            "update website/lib/features.ts"
        )

    def test_mcp_tools_count_matches_schemas(self):
        from attune.mcp import tool_schemas as ts

        getters = [getattr(ts, n) for n in dir(ts) if n.startswith("get_") and n.endswith("_tools")]
        live = sum(len(fn()) for fn in getters)
        assert _capabilities()["mcpTools"] == live, (
            f"CAPABILITIES.mcpTools != live get_*_tools() total ({live}) — "
            "update website/lib/features.ts"
        )

    def test_template_kinds_matches_generator(self):
        pytest.importorskip("attune_author", reason="attune_author not installed")
        from attune_author.generator import _ALL_TEMPLATE_NAMES

        live = len(_ALL_TEMPLATE_NAMES)
        assert _capabilities()["templateKinds"] == live, (
            f"CAPABILITIES.templateKinds != _ALL_TEMPLATE_NAMES length ({live}) — "
            "update website/lib/features.ts"
        )
