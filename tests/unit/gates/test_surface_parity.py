"""Gate: surface-producer discovery and the reviewed producer baseline.

host-surface-parity Task 1B (R2), increment 1 of the task: every
in-tree surface producer is discovered mechanically — renderer calls
into the attune-forms registry, package host envelopes, manifest-
registered hooks with their event-qualified envelope signatures, and
Markdown commands — and the result must equal the reviewed
``docs/specs/host-surface-parity/producer_baseline.json`` fixture.

The mutation receipts here are the evidence that the scanner is not
vacuous: an unregistered projection call in each syntax, a helper-
indirected call, an envelope on the wrong event, an unresolvable
envelope mapping, an unknown manifest variable, a path escape, a
permuted registration order, and a new command each produce the exact
anchor or identity the design names.

Later increments add the parity registry, the receipts ledger, the
routing policy and the receipt store; this increment gates discovery
only and claims nothing about parity.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path

import pytest

from attune.elicitation import surface_inventory as si

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "docs" / "specs" / "host-surface-parity" / "producer_baseline.json"

REGEN = (
    'regenerate with: python -c "from pathlib import Path; from attune.elicitation.'
    "surface_inventory import write_baseline; write_baseline(Path('.'), Path('docs/specs/"
    "host-surface-parity/producer_baseline.json'))\" — then REVIEW the diff: every new "
    "anchor is a producer that needs a subject record."
)


@pytest.fixture(scope="module")
def live() -> si.ProducerBaseline:
    return si.scan_repository(REPO)


@pytest.fixture(scope="module")
def reviewed() -> si.ProducerBaseline:
    return si.load_baseline(FIXTURE)


# --- the reviewed baseline ---------------------------------------------------


def test_scan_matches_the_reviewed_baseline(live, reviewed) -> None:
    for name in (
        "shipped_roots",
        "registrations",
        "artifacts",
        "renderer_call_anchors",
        "package_host_envelope_anchors",
        "hook_envelope_anchors",
        "helper_edges",
        "problems",
    ):
        assert getattr(live, name) == getattr(reviewed, name), f"{name} drifted — {REGEN}"


def test_scan_has_no_unresolved_problems(live) -> None:
    assert live.problems == ()


def test_baseline_reproduces_the_design_renderer_anchor_fixture(reviewed) -> None:
    """Design R2 names six anchors / seven sites; the scan must find exactly those."""
    sites = {(a.anchor, a.target.rsplit(".", 1)[1]) for a in reviewed.renderer_call_anchors}
    assert sites == {
        ("src/attune/memory/recall_digest.py:render_digest_html", "form_to_widget_html"),
        (
            "src/attune/elicitation/command_workspace.py:CommandWorkspaceHost._render",
            "workspace_to_widget_html",
        ),
        (
            "src/attune/elicitation/command_workspace.py:CommandWorkspaceHost._render",
            "workspace_to_markdown",
        ),
        ("src/attune/elicitation/ask_payload.py:form_to_ask_payload", "form_to_askuserquestion"),
        (
            "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_form",
            "form_to_askuserquestion",
        ),
        (
            "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_widget",
            "form_to_widget_html",
        ),
        (
            "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_ask",
            "form_to_elicitation_schema",
        ),
    }
    assert len({a.anchor for a in reviewed.renderer_call_anchors}) == 6


def test_baseline_keeps_the_d6_hook_envelope_findings(reviewed) -> None:
    """D6's probe found three additional_context producers; a broader scanner keeps them."""
    ac = {
        (a.anchor.split(":")[0], a.event)
        for a in reviewed.hook_envelope_anchors
        if a.signature == "additional_context"
    }
    assert ac == {
        ("plugin/hooks/jit_recall.py", "PreToolUse"),
        ("plugin/hooks/lesson_recall.py", "UserPromptSubmit"),
        ("plugin/hooks/session_stash.py", "Stop"),
    }
    assert not any(a.signature == "system_message" for a in reviewed.hook_envelope_anchors)


def test_registrations_resolve_and_paths_are_path_aware(reviewed) -> None:
    assert reviewed.registrations and all(r.error is None for r in reviewed.registrations)
    manifests = {r.manifest_path for r in reviewed.registrations}
    assert manifests == set(si.MANIFESTS)
    paths = set(reviewed.unique_resolved_paths)
    # distinct same-basename files under both roots stay distinct
    assert {"plugin/hooks/security_guard.py", "src/attune/hooks/scripts/security_guard.py"} <= paths
    assert {"plugin/hooks/format_on_save.py", "src/attune/hooks/scripts/format_on_save.py"} <= paths
    assert len(paths) > len({Path(p).name for p in paths})


def test_handoff_command_is_an_artifact_with_its_resolved_implementation(reviewed) -> None:
    assert reviewed.artifacts == (
        si.Artifact("artifact:plugin/commands/handoff.md", "plugin/hooks/_handoff_cli.py", None),
    )
    assert "plugin/hooks/_handoff_cli.py" in reviewed.unique_resolved_paths


def test_shipped_roots_come_from_packaging_metadata(reviewed) -> None:
    assert "src/attune" in reviewed.shipped_roots
    assert "attune_redis" in reviewed.shipped_roots  # entry-point-derived, top-level package


def test_helper_edges_carry_root_provenance(reviewed) -> None:
    for edge in reviewed.helper_edges:
        assert edge.root_anchor.endswith(":<module>")
        assert edge.root_anchor.split(":")[0] == edge.helper_anchor.split(":")[0]


def test_fixture_round_trips(reviewed) -> None:
    assert si.ProducerBaseline.from_dict(json.loads(json.dumps(reviewed.to_dict()))) == reviewed


# --- the closed shell resolver -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        (
            'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/welcome.py"',
            "launcher prefix is not the shipped form",
        ),
        (
            si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/hooks/welcome.py --flag",
            "expected exactly one path token, got 2",
        ),
        (
            si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/hooks/welcome.py | tee x",
            "shell operator",
        ),
        (si.HOOK_LAUNCHER_PREFIX + " $(echo x)/welcome.py", "shell operator"),
        (si.HOOK_LAUNCHER_PREFIX + " ${HOME}/welcome.py", "unknown variable"),
        (si.HOOK_LAUNCHER_PREFIX + " /usr/bin/welcome.py", "absolute path"),
        (
            si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/../plugin/hooks/welcome.py",
            "path escape",
        ),
        (
            si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/hooks/welcome.sh",
            "not a Python entrypoint",
        ),
        (
            si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/hooks/nope.py",
            "missing file plugin/hooks/nope.py",
        ),
        (
            si.HOOK_LAUNCHER_PREFIX + ' "${CLAUDE_PLUGIN_ROOT}/hooks/unterminated.py',
            "unparseable command tail",
        ),
    ],
)
def test_resolver_fails_closed_with_the_reason(raw, error) -> None:
    resolved, problem = si.resolve_launcher(raw, REPO, si.HOOK_LAUNCHER_PREFIX)
    assert resolved is None
    assert problem is not None and problem.startswith(error), problem


def test_resolver_accepts_every_current_wrapper_form() -> None:
    a, e = si.resolve_launcher(
        si.HOOK_LAUNCHER_PREFIX + " ${CLAUDE_PLUGIN_ROOT}/hooks/welcome.py",
        REPO,
        si.HOOK_LAUNCHER_PREFIX,
    )
    b, f = si.resolve_launcher(
        si.HOOK_LAUNCHER_PREFIX + ' "$CLAUDE_PROJECT_DIR/plugin/hooks/welcome.py"',
        REPO,
        si.HOOK_LAUNCHER_PREFIX,
    )
    assert (a, e) == ("plugin/hooks/welcome.py", None)
    assert (b, f) == ("plugin/hooks/welcome.py", None)


# --- synthetic repository for mutation receipts --------------------------------

_PYPROJECT = """
[project]
name = "synthetic"
version = "0"
[project.scripts]
syn = "pkg.cli:main"
[project.entry-points."attune.memory_backends"]
redis = "attune_redis.memory:Backend"
[tool.setuptools.packages.find]
where = ["src", "."]
exclude = ["tests*", "docs*"]
"""

_HOOK_OK = """import json, sys

def main() -> int:
    payload = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "x"}}
    sys.stdout.write(json.dumps(payload))
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""


def _synthetic(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "src" / "attune" / "elicitation").mkdir(parents=True)
    (repo / "attune_redis").mkdir()
    (repo / "plugin" / "hooks").mkdir(parents=True)
    (repo / "plugin" / "commands").mkdir()
    (repo / ".claude").mkdir()
    (repo / "tests").mkdir()
    (repo / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    (repo / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "pkg" / "cli.py").write_text(
        "def main() -> int:\n    return 0\n", encoding="utf-8"
    )
    (repo / "src" / "attune" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "attune" / "elicitation" / "__init__.py").write_text(
        "from attune_forms import form_to_widget_html\n", encoding="utf-8"
    )
    (repo / "attune_redis" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "attune_redis" / "memory.py").write_text("class Backend: ...\n", encoding="utf-8")
    (repo / "tests" / "test_x.py").write_text(
        "from attune_forms import form_to_widget_html\ndef t(f):\n    return form_to_widget_html(f)\n",
        encoding="utf-8",
    )
    (repo / "plugin" / "hooks" / "hook_a.py").write_text(_HOOK_OK, encoding="utf-8")
    (repo / "plugin" / "hooks" / "_handoff_cli.py").write_text("print('x')\n", encoding="utf-8")
    _write_manifest(
        repo / "plugin" / "hooks" / "hooks.json",
        [("PreToolUse", "Bash", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py")],
    )
    _write_manifest(
        repo / ".claude" / "settings.json",
        [("SessionStart", "", '"$CLAUDE_PROJECT_DIR/plugin/hooks/hook_a.py"')],
    )
    (repo / "plugin" / "commands" / "handoff.md").write_text(
        '# handoff\n\n```bash\npython3 "${CLAUDE_PLUGIN_ROOT}/hooks/_handoff_cli.py"\n```\n',
        encoding="utf-8",
    )
    return repo


def _write_manifest(path: Path, rows: list[tuple[str, str, str]]) -> None:
    hooks: dict[str, list] = {}
    for event, matcher, tail in rows:
        group = {"hooks": [{"type": "command", "command": f"{si.HOOK_LAUNCHER_PREFIX} {tail}"}]}
        if matcher:
            group["matcher"] = matcher
        hooks.setdefault(event, []).append(group)
    path.write_text(json.dumps({"hooks": hooks}, indent=1), encoding="utf-8")


def _add(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_synthetic_repo_baseline_is_clean_and_derives_roots(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    b = si.scan_repository(repo)
    assert b.problems == ()
    assert b.shipped_roots == ("attune_redis", "src/attune", "src/pkg")
    assert b.renderer_call_anchors == ()  # tests/ is outside the inventory
    assert [(a.anchor, a.signature, a.event) for a in b.hook_envelope_anchors] == [
        ("plugin/hooks/hook_a.py:main", "additional_context", "PreToolUse"),
        ("plugin/hooks/hook_a.py:main", "context_stdout", "SessionStart"),
    ]
    assert b.artifacts[0].implementation == "plugin/hooks/_handoff_cli.py"
    assert (
        si.HelperEdge("plugin/hooks/hook_a.py:<module>", "plugin/hooks/hook_a.py:main")
        in b.helper_edges
    )


@pytest.mark.parametrize(
    ("source", "syntax"),
    [
        (
            "from attune_forms import form_to_widget_html\ndef render(f):\n    return form_to_widget_html(f)\n",
            "direct",
        ),
        (
            "from attune_forms.widget import form_to_widget_html as w\ndef render(f):\n    return w(f)\n",
            "direct",
        ),
        (
            "from attune.elicitation import form_to_widget_html\ndef render(f):\n    return form_to_widget_html(f)\n",
            "reexport",
        ),
        (
            "import attune_forms\ndef render(f):\n    return attune_forms.form_to_widget_html(f)\n",
            "qualified",
        ),
        (
            "import attune_forms.widget as w\ndef render(f):\n    return w.form_to_widget_html(f)\n",
            "qualified",
        ),
        (
            "from attune import elicitation\ndef render(f):\n    return elicitation.form_to_widget_html(f)\n",
            "qualified",
        ),
    ],
)
def test_unregistered_projection_call_is_discovered_in_every_syntax(
    tmp_path, source, syntax
) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "src/pkg/view.py", source)
    b = si.scan_repository(repo)
    assert b.renderer_call_anchors == (
        si.RendererCallAnchor(
            "src/pkg/view.py:render", "attune_forms.widget.form_to_widget_html", syntax
        ),
    )


def test_module_body_call_uses_the_reserved_module_anchor(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "src/pkg/boot.py",
        "from attune_forms import form_to_widget_html\nHTML = form_to_widget_html(None)\n",
    )
    b = si.scan_repository(repo)
    assert [a.anchor for a in b.renderer_call_anchors] == ["src/pkg/boot.py:<module>"]


def test_attune_redis_renderer_call_is_caught_via_entry_point_root(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "attune_redis/memory.py",
        "from attune_forms import form_to_markdown\nclass Backend:\n    def show(self, f):\n        return form_to_markdown(f)\n",
    )
    b = si.scan_repository(repo)
    assert [a.anchor for a in b.renderer_call_anchors] == ["attune_redis/memory.py:Backend.show"]


def test_helper_indirection_reports_root_arrow_helper(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/helpers.py",
        "from attune_forms import form_to_markdown\ndef emit(f):\n    return form_to_markdown(f)\n",
    )
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        "import sys\nfrom helpers import emit\ndef main():\n    return emit(None)\nsys.exit(main())\n",
    )
    b = si.scan_repository(repo)
    assert [a.anchor for a in b.renderer_call_anchors] == ["plugin/hooks/helpers.py:emit"]
    assert (
        si.HelperEdge("plugin/hooks/hook_a.py:<module>", "plugin/hooks/helpers.py:emit")
        in b.helper_edges
    )


def test_shared_helper_serves_two_roots_without_a_new_subject(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "plugin/hooks/hook_b.py", _HOOK_OK.replace("PreToolUse", "Stop"))
    _write_manifest(
        repo / "plugin" / "hooks" / "hooks.json",
        [
            ("PreToolUse", "Bash", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py"),
            ("Stop", "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_b.py"),
        ],
    )
    b = si.scan_repository(repo)
    roots = {e.root_anchor for e in b.helper_edges}
    assert roots == {"plugin/hooks/hook_a.py:<module>", "plugin/hooks/hook_b.py:<module>"}
    assert ("plugin/hooks/hook_b.py:main", "additional_context", "Stop") in {
        (a.anchor, a.signature, a.event) for a in b.hook_envelope_anchors
    }


def test_envelope_on_the_wrong_event_is_not_a_producer(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "plugin/hooks/hook_a.py", _HOOK_OK.replace('"PreToolUse"', '"Stop"'))
    b = si.scan_repository(repo)
    assert not any(a.signature == "additional_context" for a in b.hook_envelope_anchors)
    assert b.problems == ()


@pytest.mark.parametrize(
    ("body", "event", "signature", "destination"),
    [
        (
            'print(json.dumps({"systemMessage": "hi"}))',
            "PostToolUse",
            "system_message",
            "user_notice",
        ),
        (
            'print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": r}}))',
            "PreToolUse",
            "pretooluse_deny",
            "model_context",
        ),
        (
            'print(json.dumps({"decision": "block", "reason": r}))',
            "Stop",
            "stop_block",
            "model_context",
        ),
        ("print(r, file=sys.stderr); sys.exit(2)", "PreToolUse", "exit2_stderr", "model_context"),
        (
            "print(r, file=sys.stderr); raise SystemExit(2)",
            "PostToolUse",
            "exit2_stderr",
            "model_context",
        ),
        ("print(r)", "UserPromptSubmit", "context_stdout", "model_context"),
    ],
)
def test_each_closed_signature_classifies_to_its_kind_and_destination(
    tmp_path, body, event, signature, destination
) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        f"import json, sys\nr = 'why'\ndef main():\n    {body}\nmain()\n",
    )
    _write_manifest(
        repo / "plugin" / "hooks" / "hooks.json",
        [(event, "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py")],
    )
    _write_manifest(
        repo / ".claude" / "settings.json",
        [("Notification", "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py")],
    )
    b = si.scan_repository(repo)
    found = {(a.signature, a.event, a.destination, a.subject_kind) for a in b.hook_envelope_anchors}
    assert (signature, event, destination, "informational_delivery") in found
    if si.ENVELOPE_SIGNATURES[signature][2] is not None:
        assert not any(
            a.event == "Notification" for a in b.hook_envelope_anchors
        ), "control-plane on a non-qualifying event"


@pytest.mark.parametrize(
    ("body", "event"),
    [
        ("print(r, file=sys.stderr); sys.exit(2)", "SessionStart"),  # stderr not fed to the model
        ("print(r, file=sys.stderr); sys.exit(0)", "PreToolUse"),  # wrong exit code
        ("print(r)", "Stop"),  # stdout on a non-context event
        (
            'print(json.dumps({"decision": "block", "reason": r}))',
            "PreToolUse",
        ),  # stop_block on the wrong event
        ('print(json.dumps({"reason": r}))', "Stop"),  # bare control-plane key
    ],
)
def test_negative_mutations_stay_control_plane(tmp_path, body, event) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        f"import json, sys\nr = 'why'\ndef main():\n    {body}\nmain()\n",
    )
    _write_manifest(
        repo / "plugin" / "hooks" / "hooks.json",
        [(event, "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py")],
    )
    _write_manifest(
        repo / ".claude" / "settings.json", [(event, "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py")]
    )
    b = si.scan_repository(repo)
    assert b.hook_envelope_anchors == ()
    assert b.problems == ()


def test_unresolvable_envelope_mapping_fails_closed_with_its_anchor(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        "import json, sys\ndef main(extra):\n    payload = {'hookSpecificOutput': {**extra}}\n    sys.stdout.write(json.dumps(payload))\nmain({})\n",
    )
    b = si.scan_repository(repo)
    assert any(
        p.startswith("plugin/hooks/hook_a.py:main: ") and "fails closed" in p for p in b.problems
    ), b.problems


def test_dynamic_sink_fails_closed_only_when_a_recognized_key_is_in_play(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        "import json, sys\ndef main(stream):\n    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': 'x'}}), file=stream)\nmain(sys.stdout)\n",
    )
    b = si.scan_repository(repo)
    assert any("print(file=<dynamic>)" in p for p in b.problems)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        "def main():\n    out = {}\n    for k in ('a', 'b'):\n        out[k] = 1\n    return out\nmain()\n",
    )
    assert si.scan_repository(repo).problems == ()


def test_same_file_unrelated_function_cannot_transfer_credit(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "plugin/hooks/hook_a.py",
        "import json, sys\n"
        "def unused():\n    sys.stdout.write(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': 'x'}}))\n"
        "def main():\n    return 0\n"
        "sys.exit(main())\n",
    )
    b = si.scan_repository(repo)
    assert b.hook_envelope_anchors == ()


def test_registration_order_permutation_does_not_change_the_result(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "plugin/hooks/hook_b.py", _HOOK_OK.replace("PreToolUse", "UserPromptSubmit"))
    rows = [
        ("PreToolUse", "Bash", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_a.py"),
        ("UserPromptSubmit", "", "${CLAUDE_PLUGIN_ROOT}/hooks/hook_b.py"),
    ]
    _write_manifest(repo / "plugin" / "hooks" / "hooks.json", rows)
    first = si.scan_repository(repo)
    _write_manifest(repo / "plugin" / "hooks" / "hooks.json", list(reversed(rows)))
    second = si.scan_repository(repo)
    assert first.hook_envelope_anchors == second.hook_envelope_anchors
    assert first.helper_edges == second.helper_edges
    assert {r.json_pointer for r in first.registrations} == {
        r.json_pointer for r in second.registrations
    }


def test_new_markdown_command_is_discovered_as_an_artifact(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "plugin/commands/new.md", "# new\n\nNo command here.\n")
    b = si.scan_repository(repo)
    assert si.Artifact("artifact:plugin/commands/new.md", None, None) in b.artifacts


def test_command_with_two_fenced_commands_or_bad_launcher_fails_closed(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(repo, "plugin/commands/two.md", "```bash\npython3 a.py\npython3 b.py\n```\n")
    _add(repo, "plugin/commands/bad.md", "```bash\nbash run.sh\n```\n")
    b = si.scan_repository(repo)
    assert "artifact:plugin/commands/two.md: 2 fenced commands; expected one" in b.problems
    assert any(p.startswith("artifact:plugin/commands/bad.md: launcher prefix") for p in b.problems)


def test_manifest_problems_carry_registration_identity(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _write_manifest(
        repo / "plugin" / "hooks" / "hooks.json", [("PreToolUse", "", "${HOME}/hooks/hook_a.py")]
    )
    (repo / ".claude" / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
    b = si.scan_repository(repo)
    assert (
        "manifest:plugin/hooks/hooks.json#/hooks/PreToolUse/0/hooks/0/command: unknown variable in '${HOME}/hooks/hook_a.py'"
        in b.problems
    )
    assert "manifest:.claude/settings.json: yields no registration" in b.problems
    shutil.rmtree(repo / ".claude")
    assert "manifest:.claude/settings.json: missing" in si.scan_repository(repo).problems


def test_package_envelopes_and_workspace_render_are_detected(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    _add(
        repo,
        "src/pkg/server.py",
        "from attune_forms import mcp_app_result\n"
        "class S:\n"
        "    async def _handle_widget(self, args):\n        return {'success': True, 'html': '<x>'}\n"
        "    async def _handle_ask(self, session):\n        return await session.elicit_form('m', {}, 'r')\n"
        "    def _handle_open(self):\n        return {'mcp_app': mcp_app_result({})}\n"
        "    def _render(self, view):\n        return CommandWorkspaceRender(html='h', markdown='m')\n"
        "    def _batches(self):\n        return {'batches': []}\n",
    )
    b = si.scan_repository(repo)
    found = {(a.anchor.split(":")[1], a.signature) for a in b.package_host_envelope_anchors}
    assert found == {
        ("S._handle_widget", "html_response"),
        ("S._handle_ask", "native_elicit_form"),
        ("S._handle_open", "mcp_app_resource"),
        ("S._render", "workspace_render"),
        ("S._batches", "askuserquestion_batches"),
    }


def test_baseline_fields_are_separate_sets_not_one_count(reviewed) -> None:
    d = reviewed.to_dict()
    for key in (
        "renderer_call_anchors",
        "package_host_envelope_anchors",
        "hook_envelope_anchors",
        "helper_edges",
        "registrations",
    ):
        assert isinstance(d[key], list) and d[key]
    assert dataclasses.is_dataclass(reviewed)


def test_write_baseline_round_trips_and_stays_beneath_the_repo(tmp_path) -> None:
    repo = _synthetic(tmp_path)
    out = repo / "docs" / "producer_baseline.json"
    out.parent.mkdir()
    written = si.write_baseline(repo, out)
    assert si.load_baseline(out) == written
    with pytest.raises(ValueError):
        si.write_baseline(repo, tmp_path / "outside.json")


def test_load_baseline_rejects_a_non_object_document(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON object"):
        si.load_baseline(bad)
