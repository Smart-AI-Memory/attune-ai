"""Focused tests for the capability count projector.

Covers (roundtable q-capability-count-projector-001, required
verification): the three independent derivations; deliberately unequal
registered/core totals; every locator/format type; read-only default and
``--check``; drift diagnostics and exit codes; write repair and
second-write idempotence; missing, duplicate, renamed, malformed,
ambiguous, and wrong-type targets; fail-before-write when one target is
invalid; preservation of unrelated text and files; subprocess CLI exit
codes; and the independence of the existing drift gates.

The fixture manifest here is intentionally tiny and distinct from the
real ``MANIFEST``; ``test_real_manifest_repairs_bumped_values_on_copies``
exercises the real manifest against copies of the real governed files.
"""

from __future__ import annotations

import glob
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import project_capabilities as proj

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "project_capabilities.py"

# Deliberately UNEQUAL registered/core totals: interchanging them in any
# target mapping must be visible in every fixture assertion.
VALUES = {
    "skill_count": 7,
    "mcp_registered_tool_count": 55,
    "mcp_core_schema_tool_count": 49,
}

PAGE_MD = (
    "Intro line.\n\n"
    "Ships <!-- cap:skill_count -->3 auto skills<!-- /cap --> and "
    "<!-- cap:mcp_registered_tool_count -->4 shiny tools<!-- /cap -->.\n"
)
META_JSON = json.dumps(
    {"metadata": {"description": "Has 3 auto skills — really."}}, indent=2, ensure_ascii=False
)
FEATURES_TS = "export const CAPABILITIES = {\n  workflows: 20,\n  mcpTools: 9,\n} as const;\n"


def std_manifest() -> tuple:
    return (
        proj.MarkedFragmentTarget("page.md", "skills claim", "skill_count", "{n} auto skills"),
        proj.MarkedFragmentTarget(
            "page.md", "tools claim", "mcp_registered_tool_count", "{n} shiny tools"
        ),
        proj.JsonFieldTarget(
            "meta.json",
            "metadata description",
            "skill_count",
            json_path=("metadata", "description"),
            fragment="{n} auto skills",
        ),
        proj.TsCapabilityTarget(
            "features.ts",
            "CAPABILITIES.mcpTools",
            "mcp_core_schema_tool_count",
            ts_field="mcpTools",
        ),
    )


def write(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def std_repo(tmp_path: Path) -> Path:
    write(tmp_path, "page.md", PAGE_MD)
    write(tmp_path, "meta.json", META_JSON)
    write(tmp_path, "features.ts", FEATURES_TS)
    return tmp_path


def read_all(repo: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in repo.rglob("*") if p.is_file()}


# --- The three derivations, independently recomputed -------------------


class TestDerivations:
    @pytest.fixture(scope="class")
    def derived(self) -> dict[str, int]:
        return proj.derive_values(REPO_ROOT)

    def test_skill_count_matches_independent_glob(self, derived):
        live = len(glob.glob(str(REPO_ROOT / "plugin" / "skills" / "*" / "SKILL.md")))
        assert derived["skill_count"] == live > 10

    def test_registered_count_matches_server_tools(self, derived):
        from attune.mcp.server import EmpathyMCPServer

        assert derived["mcp_registered_tool_count"] == len(set(EmpathyMCPServer().tools)) > 20

    def test_core_schema_count_matches_getter_sum(self, derived):
        from attune.mcp import tool_schemas as ts

        names: set[str] = set()
        for attr in dir(ts):
            if attr.startswith("get_") and attr.endswith("_tools"):
                names |= set(getattr(ts, attr)())
        assert derived["mcp_core_schema_tool_count"] == len(names) > 20

    def test_registered_and_core_totals_are_distinct_live(self, derived):
        # The regression premise: the two totals are semantically
        # different and must never be interchangeable. Live, bundled
        # plugin tools make registered a strict superset.
        assert derived["mcp_registered_tool_count"] > derived["mcp_core_schema_tool_count"]

    def test_missing_skills_dir_fails_closed(self, tmp_path):
        with pytest.raises(proj.ProjectionError, match="refusing to publish 0"):
            proj.derive_values(tmp_path)


# --- Unequal totals cannot be interchanged ------------------------------


def test_unequal_totals_project_to_their_own_targets(tmp_path):
    repo = std_repo(tmp_path)
    plans = proj.build_plan(repo, VALUES, std_manifest())
    proj.apply_plan(repo, plans)
    page = (repo / "page.md").read_text(encoding="utf-8")
    ts = (repo / "features.ts").read_text(encoding="utf-8")
    assert "55 shiny tools" in page  # registered → markdown claim
    assert "mcpTools: 49" in ts  # core → CAPABILITIES field
    assert "49 shiny tools" not in page and "mcpTools: 55" not in ts


# --- Every locator/format type detects drift and is repaired -----------


def test_all_locator_types_drift_and_repair(tmp_path):
    repo = std_repo(tmp_path)
    plans = proj.build_plan(repo, VALUES, std_manifest())
    drift = proj.drift_lines(plans)
    assert len(drift) == 4  # every fixture target starts stale
    changed = proj.apply_plan(repo, plans)
    assert sorted(changed) == ["features.ts", "meta.json", "page.md"]
    replan = proj.build_plan(repo, VALUES, std_manifest())
    assert proj.drift_lines(replan) == []
    assert (
        json.loads((repo / "meta.json").read_text(encoding="utf-8"))["metadata"]["description"]
        == "Has 7 auto skills — really."
    )


def test_same_file_targets_compose_without_clobbering(tmp_path):
    # Two drifted targets in one file: both repairs must land.
    repo = std_repo(tmp_path)
    plans = proj.build_plan(repo, VALUES, std_manifest())
    proj.apply_plan(repo, plans)
    page = (repo / "page.md").read_text(encoding="utf-8")
    assert "7 auto skills" in page and "55 shiny tools" in page


# --- CLI flow (in-process, fixture repo) --------------------------------


@pytest.fixture
def cli_repo(tmp_path, monkeypatch) -> Path:
    repo = std_repo(tmp_path)
    monkeypatch.setattr(proj, "MANIFEST", std_manifest())
    monkeypatch.setattr(proj, "derive_values", lambda _repo: dict(VALUES))
    return repo


class TestCliFlow:
    @pytest.mark.parametrize("argv", [[], ["--check"]])
    def test_default_and_check_are_read_only(self, cli_repo, argv, capsys):
        before = read_all(cli_repo)
        assert proj.main(argv, repo=cli_repo) == 1
        assert read_all(cli_repo) == before
        err = capsys.readouterr().err
        # Diagnostics carry semantic value, target, expected + observed rendering.
        assert "page.md: skills claim publishes skill_count" in err
        assert "'7 auto skills'" in err and "'3 auto skills'" in err

    def test_check_exits_zero_when_synced(self, cli_repo, capsys):
        assert proj.main(["--write"], repo=cli_repo) == 0
        assert proj.main(["--check"], repo=cli_repo) == 0
        assert "all capability claims match" in capsys.readouterr().out

    def test_write_repairs_then_second_write_is_byte_idempotent(self, cli_repo, capsys):
        assert proj.main(["--write"], repo=cli_repo) == 0
        first = read_all(cli_repo)
        assert proj.main(["--write"], repo=cli_repo) == 0
        assert "nothing to write" in capsys.readouterr().out
        assert read_all(cli_repo) == first

    def test_derivation_failure_exits_2(self, cli_repo, monkeypatch, capsys):
        def boom(_repo):
            raise proj.ProjectionError("unstable")

        monkeypatch.setattr(proj, "derive_values", boom)
        assert proj.main(["--check"], repo=cli_repo) == 2
        assert "failed closed" in capsys.readouterr().err


# --- Structural failure modes fail closed -------------------------------


class TestFailClosed:
    def test_missing_target_file(self, tmp_path):
        repo = std_repo(tmp_path)
        (repo / "meta.json").unlink()
        with pytest.raises(proj.ProjectionError, match="target file missing"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_target_path_escaping_repo_root(self, tmp_path):
        repo = std_repo(tmp_path)
        bad = (proj.MarkedFragmentTarget("../page.md", "escape", "skill_count", "{n} auto skills"),)
        with pytest.raises(proj.ProjectionError, match="escapes the repository root"):
            proj.build_plan(repo, VALUES, bad)

    def test_missing_marker_span(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "page.md", "No markers at all.\n")
        with pytest.raises(proj.ProjectionError, match="0 marked span"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_duplicate_marker_span(self, tmp_path):
        repo = std_repo(tmp_path)
        write(
            repo, "page.md", PAGE_MD + "Again <!-- cap:skill_count -->9 auto skills<!-- /cap -->.\n"
        )
        with pytest.raises(proj.ProjectionError, match="2 marked span"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_renamed_marker_value_is_unclaimed(self, tmp_path):
        repo = std_repo(tmp_path)
        write(
            repo,
            "page.md",
            PAGE_MD.replace("cap:skill_count", "cap:legacy_skill_total"),
        )
        with pytest.raises(proj.ProjectionError, match="claimed by no manifest target"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_unclosed_marker_is_malformed(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "page.md", PAGE_MD + "Dangling <!-- cap:skill_count -->9 auto skills\n")
        with pytest.raises(proj.ProjectionError, match="malformed or unclosed"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_wrong_type_marked_content_is_unclaimed(self, tmp_path):
        repo = std_repo(tmp_path)
        write(
            repo,
            "page.md",
            PAGE_MD.replace("3 auto skills", "several auto skills"),
        )
        with pytest.raises(proj.ProjectionError, match="claimed by no manifest target"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_ambiguous_targets_for_one_span(self, tmp_path):
        repo = std_repo(tmp_path)
        manifest = std_manifest() + (
            proj.MarkedFragmentTarget("page.md", "twin claim", "skill_count", "{n} auto skills"),
        )
        with pytest.raises(proj.ProjectionError, match="ambiguous ownership"):
            proj.build_plan(repo, VALUES, manifest)

    def test_unknown_semantic_value_in_target(self, tmp_path):
        repo = std_repo(tmp_path)
        manifest = (
            proj.MarkedFragmentTarget("page.md", "bogus", "wizard_count", "{n} auto skills"),
        )
        with pytest.raises(proj.ProjectionError):
            proj.build_plan(repo, VALUES, manifest)

    def test_invalid_json_fails(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "meta.json", "{not json")
        with pytest.raises(proj.ProjectionError, match="invalid JSON"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_json_path_key_missing(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "meta.json", json.dumps({"metadata": {}}))
        with pytest.raises(proj.ProjectionError, match="not found"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_json_field_wrong_type(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "meta.json", json.dumps({"metadata": {"description": 3}}))
        with pytest.raises(proj.ProjectionError, match="expected string"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_json_fragment_absent_from_field(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "meta.json", json.dumps({"metadata": {"description": "no counts here"}}))
        with pytest.raises(proj.ProjectionError, match="matched 0 time"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_json_list_selector_cardinality(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "plugins.json", json.dumps({"plugins": [{"name": "a"}, {"name": "a"}]}))
        target = proj.JsonFieldTarget(
            "plugins.json",
            "dup selector",
            "skill_count",
            json_path=("plugins", ("name", "a"), "description"),
            fragment="{n} auto skills",
        )
        with pytest.raises(proj.ProjectionError, match="matched 2 entries"):
            proj.build_plan(repo, VALUES, (target,))

    def test_json_ambiguous_raw_encoding(self, tmp_path):
        repo = std_repo(tmp_path)
        # The owned field's encoded value appears twice in the raw file —
        # a raw-text rewrite would be ambiguous, so it must fail closed.
        write(
            repo,
            "meta.json",
            '{"metadata": {"description": "Has 3 auto skills — really."},'
            ' "copy": "Has 3 auto skills — really."}',
        )
        with pytest.raises(proj.ProjectionError, match="cannot rewrite unambiguously"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_ts_capabilities_block_missing(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "features.ts", "export const OTHER = {};\n")
        with pytest.raises(proj.ProjectionError, match="CAPABILITIES blocks"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_ts_field_missing(self, tmp_path):
        repo = std_repo(tmp_path)
        write(repo, "features.ts", "export const CAPABILITIES = {\n  workflows: 20,\n} as const;\n")
        with pytest.raises(proj.ProjectionError, match="matched 0 time"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_ts_field_duplicated(self, tmp_path):
        repo = std_repo(tmp_path)
        write(
            repo,
            "features.ts",
            "export const CAPABILITIES = {\n  mcpTools: 9,\n  mcpTools: 9,\n} as const;\n",
        )
        with pytest.raises(proj.ProjectionError, match="matched 2 time"):
            proj.build_plan(repo, VALUES, std_manifest())

    def test_bad_template_placeholder(self, tmp_path):
        repo = std_repo(tmp_path)
        target = proj.MarkedFragmentTarget("page.md", "no slot", "skill_count", "auto skills")
        with pytest.raises(proj.ProjectionError, match="exactly one"):
            proj.build_plan(repo, VALUES, (target,))


def test_one_invalid_target_prevents_every_write(tmp_path, monkeypatch):
    repo = std_repo(tmp_path)
    write(repo, "meta.json", "{broken")  # invalidates one target
    before = read_all(repo)
    monkeypatch.setattr(proj, "MANIFEST", std_manifest())
    monkeypatch.setattr(proj, "derive_values", lambda _repo: dict(VALUES))
    assert proj.main(["--write"], repo=repo) == 2
    assert read_all(repo) == before  # the drifted page.md was NOT repaired


# --- Preservation of unrelated content, newlines, and files -------------


def test_write_preserves_crlf_unicode_and_unrelated_files(tmp_path):
    repo = tmp_path
    crlf = (
        "Header — unrelated ünïcode.\r\n\r\n"
        "Ships <!-- cap:skill_count -->3 auto skills<!-- /cap --> today.  \r\n"
        "Trailing spaces above stay.\r\n"
    )
    write(repo, "page.md", crlf)
    bystander = write(repo, "bystander.md", "Never touched.\n")
    manifest = (
        proj.MarkedFragmentTarget("page.md", "skills claim", "skill_count", "{n} auto skills"),
    )
    plans = proj.build_plan(repo, VALUES, manifest)
    changed = proj.apply_plan(repo, plans)
    assert changed == ["page.md"]
    assert (repo / "page.md").read_bytes() == crlf.replace("3 auto skills", "7 auto skills").encode(
        "utf-8"
    )
    assert bystander.read_bytes() == b"Never touched.\n"
    assert not list(repo.glob("*.capproj-tmp"))  # atomic temp cleaned up


# --- The real manifest against copies of the real files -----------------


def test_real_manifest_repairs_bumped_values_on_copies(tmp_path):
    """Every governed target detects drift and is repaired by --write."""
    for target in proj.MANIFEST:
        src = REPO_ROOT / target.path
        dst = tmp_path / target.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copyfile(src, dst)
    baseline = proj.build_plan(tmp_path, proj.derive_values(REPO_ROOT))
    assert proj.drift_lines(baseline) == []  # repo claims are in sync
    bumped = {k: v + 1 for k, v in proj.derive_values(REPO_ROOT).items()}
    plans = proj.build_plan(tmp_path, bumped)
    assert len(proj.drift_lines(plans)) == len(proj.MANIFEST)  # all 13 drift
    proj.apply_plan(tmp_path, plans)
    json.loads((tmp_path / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    replan = proj.build_plan(tmp_path, bumped)
    assert proj.drift_lines(replan) == []


# --- Subprocess CLI: exit codes and diagnostics --------------------------


class TestSubprocessCli:
    def test_check_is_green_on_synced_repo(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        for name in proj.VALUE_NAMES:
            assert f"{name} = " in result.stdout

    def test_unknown_argument_fails_closed(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--frobnicate"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode == 2

    def test_check_and_write_together_fail_closed(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check", "--write"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode == 2
        assert "not allowed with" in result.stderr


# --- Gate independence ----------------------------------------------------


def test_independent_gates_do_not_import_projector():
    """The drift gates must keep their own derivation and locators."""
    for rel in (
        "tests/unit/gates/test_claim_drift.py",
        "tests/unit/test_website_version_accuracy.py",
    ):
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        imports = [
            line
            for line in source.splitlines()
            if line.lstrip().startswith(("import ", "from ")) and "project_capabilities" in line
        ]
        assert not imports, f"{rel} imports the projector: {imports}"
