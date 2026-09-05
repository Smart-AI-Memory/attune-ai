"""Gate: the consumer must not read what no producer emits (class C10).

The phantom read: a producer and consumer disagree on a dict key or a
channel name, the consumer's read path degrades silently (``.get()``
default, empty entry-point group), and the output renders well-formed
and WRONG — zeroed findings, always-passing gates, never-loaded
plugins. The defining property is that the failure mode satisfies the
healthy-path assertions, so tests and probes stay green (seven
registered instances, 2026-08-23/24; register entry C10).

Two calibrated rules from ``attune.classes.rules``:

- **R8** (``scan_result_key_contract``): an MCP ``_workflow_response``
  field pick must read a key its workflow can emit — plain-dict
  ``final_output`` keys, or (adapter-built producers) the findings- and
  score-like names ``_report_fields`` serves. Any other pick can only
  return its static default. Calibrated 2026-08-24: fires on the
  registered #2213 instance at ``ac47cfb21^``; 9 hits on the then-
  current tree, all hand-triaged real, zero false positives.
- **R9** (``scan_entry_point_channels``): entry-point channel identity
  in both directions — every group src/ reads is registered in
  pyproject or legacy-marked; every group pyproject registers is read
  or externally consumed. Calibrated 2026-08-24: 3/3 facets of the
  #2259 instance fire at ``c7c94f33e^``; zero hits, zero false
  positives on the fixed tree (8 reads, 4 registered groups).

R8 shipped with a 9-entry baseline (mechanization comes BEFORE
sweep-fix in the class pipeline); the 2026-08-24 sweep-fix emptied it.
The #2213 residual closed by serving declared
``from_agent_output(metadata={...})`` keys through
``_workflow_response`` — R8 counts those keys servable on adapter
producers, so the scanner and the runtime moved in the same PR (the
2026-08-21 allowlist-ratchet lesson: a new safe idiom the scanner
cannot see is a recall regression). The baseline stays shrink-only
and empty: new phantom picks are blocked outright.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0

Register-Class: C10
"""

from __future__ import annotations

from pathlib import Path

from attune.classes.rules import (
    Hit,
    scan_entry_point_channels,
    scan_result_key_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Known phantom picks, keyed ``<handler>:<response_key><-<source_key>``.
#: EMPTY since the 2026-08-24 sweep-fix (class C10 Sweep-fix → Close):
#: the 9 calibration-era sites were fixed — test-gen's picks now serve
#: the truthful ``from_agent_output(metadata={...})`` keys (#2250 idiom,
#: served by ``_workflow_response`` and understood by R8),
#: research-synthesis' key_insights rerouted to the report findings,
#: and the never-emitted picks (code-review feedback, release-notes
#: approved/recommendation, doc-gen document/sections) were dropped.
#: Shrink-only ratchet: new phantom picks are blocked outright — do
#: NOT re-seed this set.
_KNOWN_PHANTOM_PICKS: frozenset[str] = frozenset()


def _identity(hit: Hit) -> str:
    """The stable ``handler:key<-src`` token of an R8 hit."""
    return hit.detail.split(" ")[0]


def test_no_phantom_reads() -> None:
    """R9 must be clean; R8 must not fire outside the known baseline."""
    r9 = scan_entry_point_channels(REPO_ROOT)
    assert not r9, "Entry-point channel drift (class C10):\n  " + "\n  ".join(
        f"{h.path}:{h.line}  {h.detail}" for h in r9
    )

    r8 = scan_result_key_contract(REPO_ROOT)
    new = [h for h in r8 if _identity(h) not in _KNOWN_PHANTOM_PICKS]
    assert not new, (
        "Phantom result-key reads outside the recorded baseline (class C10):\n  "
        + "\n  ".join(f"{h.path}:{h.line}  {h.detail}" for h in new)
        + "\n\nThe pick's source key is not in the producer's plain-dict "
        "final_output and is not a findings-/score-like name an adapter-built "
        "report can serve — the response field will always carry its static "
        "default while rendering healthy. Emit the key, reroute the pick, or "
        "drop it; do NOT add a baseline entry for new code."
    )

    stale = _KNOWN_PHANTOM_PICKS - {_identity(h) for h in r8}
    assert not stale, (
        f"Baseline entries no longer reported: {sorted(stale)}.\n"
        "If you FIXED these sites, delete the entries (shrink-only ratchet). "
        "If you only refactored nearby code, suspect the scanner lost sight "
        "of the site before trusting the improvement — see the 2026-08-21 "
        "allowlist-ratchet lesson."
    )


# --------------------------------------------------------------------------
# R8 fixtures — the canonical shape and each calibration discriminator
# --------------------------------------------------------------------------


def _r8_repo(tmp_path: Path, workflow_src: str, handler_src: str) -> Path:
    (tmp_path / "workflows").mkdir(parents=True)
    (tmp_path / "workflows" / "wf.py").write_text(workflow_src, encoding="utf-8")
    (tmp_path / "handlers.py").write_text(handler_src, encoding="utf-8")
    return tmp_path


def _r8_scan(repo: Path) -> list[Hit]:
    return scan_result_key_contract(
        repo,
        handler_paths=(Path("handlers.py"),),
        workflows_root=Path("workflows"),
    )


_ADAPTER_WORKFLOW = (
    "class W:\n"
    "    def run(self):\n"
    "        return AgentSDKResultAdapter.from_agent_output(result_text='x')\n"
)

_HANDLER_TEMPLATE = (
    "async def handler(self, args):\n"
    "    from attune.workflows.wf import W\n"
    "    result = await W().run()\n"
    "    return _workflow_response(result, {picks})\n"
)


def test_rule_flags_the_canonical_phantom_pick(tmp_path: Path) -> None:
    """The #2213 shape: adapter producer, pick of an unserved key."""
    repo = _r8_repo(
        tmp_path,
        _ADAPTER_WORKFLOW,
        _HANDLER_TEMPLATE.format(picks="tests_generated=('tests_generated', 0)"),
    )
    hits = _r8_scan(repo)
    assert [h.detail.split(" ")[0] for h in hits] == [
        "handler:tests_generated<-tests_generated"
    ], "rule missed the canonical C10 shape"


def test_rule_clears_a_dict_literal_servable_pick(tmp_path: Path) -> None:
    """A pick of a key the producer's plain dict actually emits."""
    repo = _r8_repo(
        tmp_path,
        (
            "class W:\n"
            "    def run(self):\n"
            "        data = {'completed': 1}\n"
            "        data['generated_files'] = []\n"
            "        return WorkflowResult(True, [], data)\n"
        ),
        _HANDLER_TEMPLATE.format(picks="completed='completed', generated_files='generated_files'"),
    )
    assert _r8_scan(repo) == []


def test_rule_clears_findings_and_score_picks_on_adapter_producers(tmp_path: Path) -> None:
    """The calibration discriminator that kept report-path picks real.

    ``_report_fields`` serves findings-like (findings/predictions/
    checks) and score-like (score, ``*_score``) picks from the parsed
    report — on either side of the pick mapping. Without this
    discriminator every adapter-built workflow's handler would be a
    false positive (13 of the 22 picks examined at calibration).
    """
    repo = _r8_repo(
        tmp_path,
        _ADAPTER_WORKFLOW,
        _HANDLER_TEMPLATE.format(
            picks="findings=('checks', []), score='health_score', predictions='predictions'"
        ),
    )
    assert _r8_scan(repo) == []


def test_rule_skips_an_unresolvable_producer(tmp_path: Path) -> None:
    """No dict literal and no adapter: unknown contract, never judged."""
    repo = _r8_repo(
        tmp_path,
        (
            "class W:\n"
            "    def run(self, data):\n"
            "        return WorkflowResult(True, [], data)\n"
        ),
        _HANDLER_TEMPLATE.format(picks="anything='anything'"),
    )
    assert _r8_scan(repo) == []


def test_rule_ignores_control_kwargs(tmp_path: Path) -> None:
    """raw_output/include_provider are response controls, not picks."""
    repo = _r8_repo(
        tmp_path,
        _ADAPTER_WORKFLOW,
        _HANDLER_TEMPLATE.format(picks="raw_output=True, include_provider=True"),
    )
    assert _r8_scan(repo) == []


def test_rule_clears_declared_metadata_key_picks(tmp_path: Path) -> None:
    """A pick of a key the adapter call declares in its metadata literal.

    The #2250 idiom: an adapter-built workflow puts truthful values in
    ``from_agent_output(metadata={...})`` and ``_workflow_response``
    serves them as the pick fallback. The scanner must know this
    vocabulary — otherwise the sweep-fix's rerouted picks would be
    false positives, and (worse) a later migration TO the idiom would
    silently drop sites off the scan (2026-08-21 allowlist-ratchet
    lesson).
    """
    repo = _r8_repo(
        tmp_path,
        (
            "class W:\n"
            "    def run(self):\n"
            "        return AgentSDKResultAdapter.from_agent_output(\n"
            "            result_text='x',\n"
            "            metadata={'tests_generated': 3, 'output_path': 'tests/'},\n"
            "        )\n"
        ),
        _HANDLER_TEMPLATE.format(
            picks="tests_generated=('tests_generated', 0), output_path='output_path'"
        ),
    )
    assert _r8_scan(repo) == []


def test_rule_still_flags_picks_outside_the_declared_metadata(tmp_path: Path) -> None:
    """Declaring SOME metadata keys must not launder every other pick."""
    repo = _r8_repo(
        tmp_path,
        (
            "class W:\n"
            "    def run(self):\n"
            "        return AgentSDKResultAdapter.from_agent_output(\n"
            "            result_text='x',\n"
            "            metadata={'output_path': 'tests/'},\n"
            "        )\n"
        ),
        _HANDLER_TEMPLATE.format(picks="document='document'"),
    )
    hits = _r8_scan(repo)
    assert [h.detail.split(" ")[0] for h in hits] == ["handler:document<-document"]


def test_rule_sees_a_module_level_workflow_import(tmp_path: Path) -> None:
    """A handler importing its workflow at module scope is still judged.

    Codex cross-review finding on #2271: nested-import discovery alone
    let module-level imports evade the seam. Top-level imports count
    for every handler in the file — and only DIRECT body statements do,
    so one handler's nested import never leaks into another's contract.
    """
    repo = _r8_repo(
        tmp_path,
        _ADAPTER_WORKFLOW,
        (
            "from attune.workflows.wf import W\n"
            "async def handler(self, args):\n"
            "    result = await W().run()\n"
            "    return _workflow_response(result, tests_generated='tests_generated')\n"
        ),
    )
    hits = _r8_scan(repo)
    assert [h.detail.split(" ")[0] for h in hits] == ["handler:tests_generated<-tests_generated"]


def test_rule_degrades_on_unreadable_inputs(tmp_path: Path) -> None:
    """Broken files skip; missing modules and dynamic picks are unjudged."""
    repo = _r8_repo(
        tmp_path,
        "def broken(:\n",  # unparseable producer -> unresolvable, skipped
        _HANDLER_TEMPLATE.format(picks="anything='anything'"),
    )
    assert _r8_scan(repo) == []
    # missing handler file: scan is empty, never raises
    assert scan_result_key_contract(repo, handler_paths=(Path("nope.py"),)) == []
    # dynamic pick source (a Name, not a literal) is unjudged
    repo2 = _r8_repo(
        tmp_path / "r2",
        _ADAPTER_WORKFLOW,
        "KEY = 'k'\n" + _HANDLER_TEMPLATE.format(picks="anything=KEY"),
    )
    assert _r8_scan(repo2) == []


# --------------------------------------------------------------------------
# R9 fixtures — both directions and every accepted marker form
# --------------------------------------------------------------------------


def _r9_repo(tmp_path: Path, module_src: str, pyproject: str) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(module_src, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return tmp_path


def test_rule_flags_an_unregistered_unmarked_read(tmp_path: Path) -> None:
    """The #2259 read facet: only the wrong channel is consulted."""
    repo = _r9_repo(
        tmp_path,
        "eps = entry_points(group='empathy.workflows')\n",
        '[project.entry-points."attune.workflows"]\n',
    )
    hits = scan_entry_point_channels(repo)
    assert len(hits) == 2  # the unmarked read AND the unread registration
    assert any("empathy.workflows" in h.detail and h.path == "src/mod.py" for h in hits)
    assert any("attune.workflows" in h.detail and h.path == "pyproject.toml" for h in hits)


def test_rule_flags_a_registered_group_nothing_reads(tmp_path: Path) -> None:
    """The #2259 write facet: registered channel with no consumer."""
    repo = _r9_repo(
        tmp_path,
        "eps = entry_points(group='attune.plugins')\n",
        '[project.entry-points."attune.plugins"]\n'
        '[project.entry-points."empathy_framework.plugins"]\n',
    )
    hits = scan_entry_point_channels(repo)
    assert [h.path for h in hits] == ["pyproject.toml"]
    assert "empathy_framework.plugins" in hits[0].detail


def test_rule_clears_every_marker_form(tmp_path: Path) -> None:
    """LEGACY constant, legacy=True call, pyproject comment, external.

    Each accepted marker was a hand-triaged true negative at
    calibration (8 reads / 4 registrations, zero hits on the fixed
    tree); a later simplification that drops one flips a deliberate
    legacy or third-party channel into a false positive.
    """
    repo = _r9_repo(
        tmp_path,
        (
            "_LEGACY_GROUP = 'empathy.wizards'\n"
            "_GROUP = 'attune.wizards'\n"
            "eps = entry_points(group=_GROUP)\n"
            "more = load_entry_point_group('empathy.workflows', legacy=True)\n"
            "third = entry_points(group='attune.workflows')\n"
        ),
        (
            "[project.entry-points.pytest11]\n"
            '[project.entry-points."attune.wizards"]\n'
            "# Third-party packages register theirs under\n"
            '# [project.entry-points."attune.workflows"].\n'
        ),
    )
    assert scan_entry_point_channels(repo) == []


def test_rule_ignores_non_group_string_literals(tmp_path: Path) -> None:
    """Dotted-path literals outside entry-point calls never match."""
    repo = _r9_repo(
        tmp_path,
        (
            "import importlib\n"
            "entry_points = None  # module mentions entry_points\n"
            "mod = importlib.import_module('attune.workflows.base')\n"
            "LOG_NAME = 'attune.mcp.server'\n"
        ),
        "",
    )
    assert scan_entry_point_channels(repo) == []


def test_rule_prefilter_matches_singular_helper_calls(tmp_path: Path) -> None:
    """A file whose only entry-point surface is a singular-named helper.

    Codex cross-review finding on #2271: the prefilter demanded the
    plural ``entry_points`` substring while the collector matches
    helpers like ``load_entry_point_group`` — such a file evaded the
    scan entirely.
    """
    repo = _r9_repo(
        tmp_path,
        "eps = load_entry_point_group('vendor.workflows')\n",
        "",
    )
    hits = scan_entry_point_channels(repo)
    assert len(hits) == 1 and "vendor.workflows" in hits[0].detail


def test_rule_degrades_on_unparseable_src(tmp_path: Path) -> None:
    """A broken src file is skipped, never fatal to the scan."""
    repo = _r9_repo(tmp_path, "def broken(:\n    entry_points\n", "")
    assert scan_entry_point_channels(repo) == []
