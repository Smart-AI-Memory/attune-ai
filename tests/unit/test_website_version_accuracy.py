"""Guards for website version/accuracy claims.

Lives flat in tests/unit/ (NOT tests/unit/website/) because pytest.ini's
``norecursedirs`` excludes any ``website`` directory — a subdir there
would be silently uncollected (caught by test_workflow_yaml's
norecursedirs guard).

Two layers:

1. **Deterministic, network-free** — the attune-ai version claimed in
   ``website/lib/features.ts`` (and the homepage badge) MUST equal this
   repo's own ``pyproject.toml`` version. This is the guard that prevents
   the exact drift caught 2026-06-28 (website stuck at 8.7.0 while the
   package shipped 9.1.0). It runs in the normal suite — so any release
   that advances pyproject past the website turns this red.

2. **Hermetic tests of the PyPI audit script** —
   ``scripts/audit_website_versions.py`` parses the PRODUCTS list and
   compares every package (incl. external attune-help/-author) to PyPI;
   here its parse + compare logic is exercised with an injected fetch
   (no network).
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
