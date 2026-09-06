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

Increment 2 also gates the subject registry, executed package receipts,
explicit pending runtime obligations and synthetic lifecycle/experiment
mutations. Inventory success is not complete production parity. Increment 3
owns runtime routing, the receipt store and missing local evidence.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from attune.elicitation import surface_inventory as si
from attune.elicitation import surface_registry as sr

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


def _baseline_pin(baseline: dict) -> dict:
    return {
        "path": sr.BASELINE_PATH,
        "schema_version": baseline["schema_version"],
        "digest": sr.canonical_digest(baseline),
    }


_SYNTHETIC_BASELINE = {
    "schema_version": sr.BASELINE_SCHEMA,
    "shipped_roots": ["src/attune", "attune_redis"],
}


# Registry semantics use a deliberately small synthetic inventory. These
# receipts test the validator; they are NEVER production parity evidence.


@pytest.fixture
def small_registry() -> dict:
    targets = [{"id": s.lower(), "surface": s} for s in ("RICH", "PORTABLE", "HEADLESS")]
    registry = {
        "renderers": [{"id": "renderer", "targets": copy.deepcopy(targets)}],
        "subjects": [
            {
                "id": "workspace",
                "subject_kind": "interactive_workspace",
                "targets": copy.deepcopy(targets),
                "cold_routes": ["PORTABLE", "HEADLESS"],
                "warm_routes": ["RICH", "PORTABLE", "HEADLESS"],
            },
            {
                "id": "form",
                "subject_kind": "interactive_form",
                "targets": copy.deepcopy(targets),
                "cold_routes": ["mcp-native:native", "PORTABLE", "HEADLESS"],
                "warm_routes": ["RICH", "mcp-native:native", "PORTABLE", "HEADLESS"],
                "route_transport_refs": {
                    r: {"kind": "subject", "id": "transport"}
                    for r in ("RICH", "PORTABLE", "HEADLESS", "mcp-native:native")
                },
            },
            {
                "id": "transport",
                "subject_kind": "interaction_transport",
                "transport_id": "native",
                "form_subject_ids": ["form"],
            },
            {
                "id": "notice",
                "subject_kind": "informational_delivery",
                "delivery_routes": [
                    {
                        "id": "start",
                        "event": "SessionStart",
                        "matcher": "",
                        "signature": "context_stdout",
                        "sink": "print",
                        "destination": "model_context",
                    }
                ],
            },
            {
                "id": "command",
                "subject_kind": "informational_artifact",
                "delivery_routes": [
                    {
                        "id": "command",
                        "event": "command",
                        "matcher": "",
                        "signature": "markdown",
                        "sink": "artifact",
                        "destination": "host",
                    }
                ],
            },
        ],
        "host_profiles": [],
        "producer_baseline": _baseline_pin(_SYNTHETIC_BASELINE),
        "receipts": [],
        "experiments": [],
        "experiment_history": [],
        "experiment_exceptions": [],
    }

    for subject in registry["subjects"]:
        for route in subject.get("delivery_routes", []):
            route["id"] = sr.canonical_digest({k: v for k, v in route.items() if k != "id"})[:16]
    return registry


def _synthetic_evidence(registry: dict) -> dict:
    evidence = {}
    for key, identity in sr.required_obligations(registry).items():
        rid = key.replace(":", ".")
        observed = {
            name: sr.canonical_digest([key, name])
            for name in (
                "implementation_digest",
                "fixture_digest",
                "record_digest",
                "normalization_digest",
                "result_digest",
            )
        }
        observed.update(
            evidence_mode="synthetic", fixture="test_surface_parity._synthetic_evidence"
        )
        registry["receipts"].append({"id": rid, "key": key, **identity, **observed})
        evidence[rid] = observed
    return evidence


def test_complete_synthetic_registry_has_exact_discriminated_receipts(small_registry) -> None:
    evidence = _synthetic_evidence(small_registry)
    obligations = sr.required_obligations(small_registry)
    assert "lifecycle:subject:form:accept" in obligations
    assert "lifecycle:subject:form:timeout" not in obligations
    assert "lifecycle:subject:transport:timeout" in obligations
    assert "delivery:command:148bc24e5b8bafa0:render" in obligations
    assert "delivery:notice:b73d9cfc43e85698:render" not in obligations
    sr.validate_receipts(
        small_registry, obligations, evidence, today=date(2026, 9, 6), baseline=_SYNTHETIC_BASELINE
    )


@pytest.mark.parametrize("owner", ["renderers", "subjects"])
@pytest.mark.parametrize("surface", ["PORTABLE", "HEADLESS"])
def test_deleting_twin_names_exact_owner_and_shortfall(small_registry, owner, surface) -> None:
    subject = small_registry[owner][0]
    subject["targets"] = [t for t in subject["targets"] if t["surface"] != surface]
    with pytest.raises(sr.SurfaceRegistryError, match=f"{subject['id']}.*missing {surface}"):
        sr.required_obligations(small_registry)


@pytest.mark.parametrize(
    "key",
    [
        "subject:workspace:surface:RICH",
        "lifecycle:subject:form:accept",
        "lifecycle:subject:transport:timeout",
        "lifecycle:subject:transport:validation_feedback_delivery",
        "delivery:command:148bc24e5b8bafa0:render",
        "delivery:notice:b73d9cfc43e85698:delivery",
    ],
)
def test_deleting_one_receipt_fails_its_exact_obligation(small_registry, key) -> None:
    evidence = _synthetic_evidence(small_registry)
    small_registry["receipts"] = [r for r in small_registry["receipts"] if r["key"] != key]
    with pytest.raises(sr.SurfaceRegistryError, match=f"{key}: missing receipt"):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.mark.parametrize(
    "digest",
    [
        "implementation_digest",
        "fixture_digest",
        "record_digest",
        "normalization_digest",
        "result_digest",
    ],
)
def test_changed_evidence_invalidates_existing_receipt(small_registry, digest) -> None:
    evidence = _synthetic_evidence(small_registry)
    receipt = small_registry["receipts"][0]
    evidence[receipt["id"]][digest] = "0" * 64
    with pytest.raises(sr.SurfaceRegistryError, match=f"{receipt['key']}: stale/missing {digest}"):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ("missing", "route_transport_refs"),
        ("extra", "route_transport_refs"),
        ("wrong_kind", "wrong interaction transport"),
        ("wrong_transport", "transport mismatch"),
        ("one_way", "one-way"),
        ("orphan", "orphan"),
        ("foreign_field", "invalid typed reference"),
    ],
)
def test_form_transport_associations_fail_closed(small_registry, mutation, expected) -> None:
    form, transport = small_registry["subjects"][1:3]
    refs = form["route_transport_refs"]
    if mutation == "missing":
        del refs["RICH"]
    elif mutation == "extra":
        refs["UNKNOWN"] = refs["RICH"]
    elif mutation == "wrong_kind":
        refs["RICH"] = {"kind": "host_profile", "id": "transport"}
    elif mutation == "wrong_transport":
        transport["transport_id"] = "other"
    elif mutation == "one_way":
        transport["form_subject_ids"] = ["other-form"]
    elif mutation == "orphan":
        transport["form_subject_ids"].append("other-form")
    else:
        refs["RICH"]["untrusted"] = True
    with pytest.raises(sr.SurfaceRegistryError, match=expected):
        sr.required_obligations(small_registry)


def test_host_profile_ref_requires_matching_profile_and_lifecycle(small_registry) -> None:
    form = small_registry["subjects"][1]
    form["warm_routes"].append("host-native:trusted")
    form["route_transport_refs"]["host-native:trusted"] = {"kind": "host_profile", "id": "trusted"}
    with pytest.raises(sr.SurfaceRegistryError, match="wrong host profile"):
        sr.required_obligations(small_registry)
    small_registry["host_profiles"] = [{"id": "trusted"}]
    obligations = sr.required_obligations(small_registry)
    assert {k for k in obligations if "host_profile" in k} == {
        f"lifecycle:host_profile:trusted:{s}" for s in sr.TRANSPORT_STATES
    }
    evidence = _synthetic_evidence(small_registry)
    sr.validate_receipts(
        small_registry, obligations, evidence, today=date(2026, 9, 6), baseline=_SYNTHETIC_BASELINE
    )


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ("duplicate", "duplicate obligation"),
        ("orphan", "orphan"),
        ("wrong_kind", "wrong discriminated"),
        ("extra_fk", "wrong discriminated"),
        ("unexecuted", "not executed"),
        ("duplicate_id", "duplicate receipt id"),
    ],
)
def test_receipts_cannot_borrow_or_invent_evidence(small_registry, mutation, expected) -> None:
    evidence = _synthetic_evidence(small_registry)
    receipt = small_registry["receipts"][0]
    if mutation == "duplicate":
        small_registry["receipts"].append({**receipt, "id": "another"})
    elif mutation == "orphan":
        receipt["key"] = "missing"
    elif mutation == "wrong_kind":
        receipt["kind"] = "lifecycle"
    elif mutation == "extra_fk":
        receipt["subject_id"] = "form"
    elif mutation == "unexecuted":
        del evidence[receipt["id"]]
    else:
        small_registry["receipts"].append(dict(receipt))
    with pytest.raises(sr.SurfaceRegistryError, match=expected):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


def _experiment(registry: dict, **updates) -> dict:
    experiment = {
        "id": "trial",
        "obligation_key": "subject:workspace:surface:RICH",
        "root_anchor": "experiments/surface-parity/trial.py:render",
        "started_on": "2026-09-01",
        "expires_on": "2026-09-15",
        "owner": "surface-parity",
        "reason": "controlled unshipped trial",
        "implementation_digest": "a" * 64,
        **updates,
    }
    registry["experiments"] = [experiment]
    registry["experiment_history"] = [copy.deepcopy(experiment)]
    return experiment


@pytest.mark.parametrize("end", ["2026-09-15", "2026-10-01"])
def test_active_experiment_waives_only_named_parity_key(small_registry, end) -> None:
    experiment = _experiment(small_registry, expires_on=end)
    assert sr.validate_experiments(
        small_registry,
        sr.required_obligations(small_registry),
        date(2026, 9, 6),
        baseline=_SYNTHETIC_BASELINE,
    ) == {experiment["obligation_key"]}


@pytest.mark.parametrize(
    "updates, today, expected",
    [
        ({"expires_on": "2026-09-14"}, date(2026, 9, 6), "14–30"),
        ({"expires_on": "2026-10-02"}, date(2026, 9, 6), "14–30"),
        ({}, date(2026, 8, 31), "future-start"),
        ({}, date(2026, 9, 15), "expired"),
        ({"started_on": "bad"}, date(2026, 9, 6), "invalid UTC"),
        ({"root_anchor": "src/attune/trial.py:render"}, date(2026, 9, 6), "package-excluded"),
        (
            {"root_anchor": "experiments/surface-parity/../bad.py"},
            date(2026, 9, 6),
            "package-excluded",
        ),
        ({"owner": ""}, date(2026, 9, 6), "owner/reason"),
        (
            {"obligation_key": "lifecycle:subject:workspace:accept"},
            date(2026, 9, 6),
            "unknown parity",
        ),
    ],
)
def test_invalid_experiment_fails_exactly(small_registry, updates, today, expected) -> None:
    _experiment(small_registry, **updates)
    with pytest.raises(sr.SurfaceRegistryError, match=expected):
        sr.validate_experiments(
            small_registry,
            sr.required_obligations(small_registry),
            today,
            baseline=_SYNTHETIC_BASELINE,
        )


def test_experiment_start_is_atomic_and_cannot_overlap_receipt(small_registry) -> None:
    evidence = _synthetic_evidence(small_registry)
    experiment = _experiment(small_registry)
    with pytest.raises(sr.SurfaceRegistryError, match="experiment_receipt_conflict"):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )
    small_registry["receipts"] = [
        r for r in small_registry["receipts"] if r["key"] != experiment["obligation_key"]
    ]
    sr.validate_receipts(
        small_registry,
        sr.required_obligations(small_registry),
        evidence,
        today=date(2026, 9, 6),
        baseline=_SYNTHETIC_BASELINE,
    )
    small_registry["experiment_history"] = []
    with pytest.raises(sr.SurfaceRegistryError, match="appended atomically"):
        sr.validate_experiments(
            small_registry,
            sr.required_obligations(small_registry),
            date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.mark.parametrize("prior_end", ["2026-09-01", "2026-09-02"])
def test_experiment_history_cannot_touch_or_overlap(small_registry, prior_end) -> None:
    experiment = _experiment(small_registry)
    small_registry["experiment_history"].append(
        {**experiment, "id": "previous", "started_on": "2026-08-18", "expires_on": prior_end}
    )
    with pytest.raises(sr.SurfaceRegistryError, match="overlapping/touching"):
        sr.validate_experiments(
            small_registry,
            sr.required_obligations(small_registry),
            date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


def test_rolling_cap_exception_binds_only_one_experiment(small_registry) -> None:
    experiment = _experiment(small_registry, expires_on="2026-09-21")
    small_registry["experiment_history"].append(
        {**experiment, "id": "old", "started_on": "2026-08-01", "expires_on": "2026-08-21"}
    )
    obligations = sr.required_obligations(small_registry)
    with pytest.raises(sr.SurfaceRegistryError, match="30 waiver days"):
        sr.validate_experiments(
            small_registry, obligations, date(2026, 9, 6), baseline=_SYNTHETIC_BASELINE
        )
    exception = {
        "id": "chair-exception",
        "experiment_id": "trial",
        "obligation_key": experiment["obligation_key"],
        "implementation_digest": experiment["implementation_digest"],
        "decision_ref": "decisions.md#test-ruling",
        "started_on": experiment["started_on"],
        "expires_on": experiment["expires_on"],
    }
    small_registry["experiment_exceptions"] = [exception]
    assert sr.validate_experiments(
        small_registry, obligations, date(2026, 9, 6), baseline=_SYNTHETIC_BASELINE
    ) == {experiment["obligation_key"]}
    exception["implementation_digest"] = "b" * 64
    with pytest.raises(sr.SurfaceRegistryError, match="binding mismatch"):
        sr.validate_experiments(
            small_registry, obligations, date(2026, 9, 6), baseline=_SYNTHETIC_BASELINE
        )


def test_root_subjects_preserve_shared_helpers_without_duplicate_interactions(
    reviewed, stored_registry
) -> None:
    baseline = reviewed.to_dict()
    roots = sr.producer_roots(baseline)
    subjects = copy.deepcopy(stored_registry["subjects"])
    sr.validate_producers(subjects, baseline)
    roots_with_helpers = {root: anchors for root, anchors in roots.items() if anchors != [root]}
    assert roots_with_helpers
    subject = next(s for s in subjects if s["root_anchor"] in roots_with_helpers)
    subject["producer_anchors"] = []
    with pytest.raises(sr.SurfaceRegistryError, match="producer provenance"):
        sr.validate_producers(subjects, baseline)


def test_json_normalization_does_not_hide_semantic_bindings() -> None:
    original = {
        "revision": 1,
        "event_sequence": 1,
        "action_nonce": "one",
        "contract_hash": "hash",
        "form_id": "form",
        "answers": {"choice": 1},
    }
    for key in original:
        changed = {**original, key: "changed"}
        assert sr.canonical_digest(original) != sr.canonical_digest(changed)
    assert sr.canonical_digest({"value": 1}) != sr.canonical_digest({"value": "1"})


def test_installed_renderer_evidence_replays_deterministically() -> None:
    from attune.elicitation.surface_evidence import installed_renderers, replay_renderer_evidence

    first, evidence = replay_renderer_evidence()
    second, again = replay_renderer_evidence()
    assert first == second and evidence == again
    registry = {
        "renderers": installed_renderers(),
        "producer_baseline": _baseline_pin(_SYNTHETIC_BASELINE),
        "subjects": [],
        "host_profiles": [],
        "receipts": first,
        "experiments": [],
        "experiment_history": [],
        "experiment_exceptions": [],
    }
    sr.validate_receipts(
        registry,
        sr.required_obligations(registry),
        evidence,
        today=date(2026, 9, 6),
        baseline=_SYNTHETIC_BASELINE,
    )


def test_compatibility_answer_comes_from_emitted_questions(monkeypatch) -> None:
    from attune_forms import FormValidationError
    from attune_forms import renderer_registry as rr

    from attune.elicitation.surface_evidence import replay_renderer_evidence

    original = rr.RendererTarget.resolve

    def altered(target):
        renderer = original(target)
        if target.status != "compatibility_only":
            return renderer

        def emit(form, **kwargs):
            batches = copy.deepcopy(renderer(form, **kwargs))
            batches[0][0]["options"] = ["not-in-the-canonical-form"]
            return batches

        return emit

    monkeypatch.setattr(rr.RendererTarget, "resolve", altered)
    with pytest.raises(FormValidationError):
        replay_renderer_evidence()


def test_route_active_target_cannot_reuse_compatibility_evidence(monkeypatch) -> None:
    from attune_forms import renderer_registry as rr

    from attune.elicitation.surface_evidence import replay_renderer_evidence

    form, workspace = rr.RENDERER_REGISTRY
    target = dataclasses.replace(
        form.targets[-1],
        status="route_active",
        evidence_mode="route_roundtrip",
        profile_id="new-profile",
        compatibility_contract_id="",
        compatibility_shape_digest="",
    )
    monkeypatch.setattr(
        rr,
        "RENDERER_REGISTRY",
        (dataclasses.replace(form, targets=(*form.targets[:-1], target)), workspace),
    )
    with pytest.raises(
        sr.SurfaceRegistryError, match="host-native:form.askuserquestion: route_roundtrip"
    ):
        replay_renderer_evidence()


def test_empty_renderer_result_cannot_be_receipted(monkeypatch) -> None:
    from attune_forms import renderer_registry as rr

    from attune.elicitation.surface_evidence import replay_renderer_evidence

    monkeypatch.setattr(rr.RendererTarget, "resolve", lambda target: lambda *a, **kw: "")
    with pytest.raises(sr.SurfaceRegistryError, match="form.rich: empty canonical projection"):
        replay_renderer_evidence()


def test_additional_host_native_target_creates_independent_obligation(small_registry) -> None:
    renderer = small_registry["renderers"][0]
    renderer["targets"].extend(
        [{"id": "host-one", "surface": "host-native"}, {"id": "host-two", "surface": "host-native"}]
    )
    evidence = _synthetic_evidence(small_registry)
    obligations = sr.required_obligations(small_registry)
    assert "renderer:renderer:host-native:host-one" in obligations
    assert "renderer:renderer:host-native:host-two" in obligations
    small_registry["receipts"] = [
        r
        for r in small_registry["receipts"]
        if r["key"] != "renderer:renderer:host-native:host-two"
    ]
    with pytest.raises(
        sr.SurfaceRegistryError, match="renderer:renderer:host-native:host-two: missing receipt"
    ):
        sr.validate_receipts(
            small_registry,
            obligations,
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.fixture(scope="module")
def stored_registry() -> dict:
    path = REPO / "docs/specs/host-surface-parity/parity-registry.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.fixture(scope="module")
def installed_evidence() -> dict:
    from attune.elicitation.surface_evidence import replay_renderer_evidence

    _, evidence = replay_renderer_evidence()
    return evidence


def test_live_inventory_is_accounted_but_does_not_claim_complete_parity(
    stored_registry, reviewed, installed_evidence
) -> None:
    report = sr.validate_inventory(
        stored_registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
    )
    assert report.pending_keys
    assert not report.complete
    assert report.required_keys == report.pending_keys | report.verified_keys
    assert all(key.startswith("renderer:") for key in report.verified_keys)
    with pytest.raises(sr.SurfaceRegistryError, match="missing receipt"):
        sr.validate_receipts(
            stored_registry,
            sr.required_obligations(stored_registry),
            installed_evidence,
            today=date(2026, 9, 6),
            baseline=reviewed.to_dict(),
        )


def test_live_registry_matches_installed_renderer_records(stored_registry) -> None:
    from attune.elicitation.surface_evidence import installed_renderers

    assert stored_registry["renderers"] == installed_renderers()


def test_live_registry_includes_two_unlisted_design_producers(stored_registry) -> None:
    records = {s["root_anchor"]: s for s in stored_registry["subjects"]}
    for anchor in (
        "src/attune/widgets/chart_widget_tool.py:render_chart_widget",
        "src/attune/mcp/workflow_handlers.py:_workflow_response",
    ):
        assert anchor in records
        assert records[anchor]["classification_basis"]
        assert records[anchor]["subject_kind"] == "informational_artifact"
        assert records[anchor]["evidence_status"] == "pending-local-receipts"


def test_all_declared_live_routes_remain_inadmissible_without_runtime_receipts(
    stored_registry, reviewed, installed_evidence
) -> None:
    report = sr.validate_inventory(
        stored_registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
    )
    checked = []
    for subject in stored_registry["subjects"]:
        for route in set(subject.get("cold_routes", [])) | set(subject.get("warm_routes", [])):
            missing = sr.route_evidence_missing(stored_registry, report, subject["id"], route)
            assert missing, (subject["id"], route)
            assert missing <= report.pending_keys
            checked.append((subject["id"], route))
    assert checked


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ("delete_pending", "unaccounted obligation"),
        ("duplicate_pending", "duplicate pending"),
        ("pending_package", "package-renderer pending"),
        ("unowned", "owner/reason"),
        ("false_complete", "cannot claim complete parity"),
        ("delete_subject", "exactly one subject"),
        ("duplicate_subject", "exactly one subject"),
        ("delete_portable", "chart-widget.*missing PORTABLE"),
        ("semantic_normalization", "semantic bindings"),
        ("wrong_event", "event-qualified"),
    ],
)
def test_live_inventory_mutations_fail_instead_of_becoming_exemptions(
    stored_registry, reviewed, installed_evidence, mutation, expected
) -> None:
    registry = copy.deepcopy(stored_registry)
    if mutation == "delete_pending":
        registry["pending_obligations"].pop()
    elif mutation == "duplicate_pending":
        registry["pending_obligations"].append(registry["pending_obligations"][0])
    elif mutation == "pending_package":
        receipt = registry["receipts"].pop()
        registry["pending_obligations"].append(
            {"key": receipt["key"], "owner": "owner", "reason": "cannot waive", "next_increment": 3}
        )
    elif mutation == "unowned":
        registry["pending_obligations"][0]["owner"] = ""
    elif mutation == "false_complete":
        registry["evidence_status"] = "complete"
    elif mutation == "delete_subject":
        registry["subjects"].pop(0)
    elif mutation == "duplicate_subject":
        registry["subjects"].append(registry["subjects"][0])
    elif mutation == "delete_portable":
        subject = next(s for s in registry["subjects"] if s["id"] == "chart-widget")
        subject["targets"] = [t for t in subject["targets"] if t["surface"] != "PORTABLE"]
    elif mutation == "semantic_normalization":
        registry["subjects"][0]["normalization_paths"] = [
            {"path": "revision", "rationale": "hide drift"}
        ]
    else:
        subject = next(
            s for s in registry["subjects"] if s["subject_kind"] == "informational_delivery"
        )
        subject["delivery_routes"][0]["event"] = "WrongEvent"
    with pytest.raises(sr.SurfaceRegistryError, match=expected):
        sr.validate_inventory(
            registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
        )


def test_route_evidence_requires_delegated_timeout_even_when_form_accept_passes(
    small_registry,
) -> None:
    keys = frozenset(sr.required_obligations(small_registry))
    missing = "lifecycle:subject:transport:timeout"
    report = sr.InventoryReport(
        keys,
        keys - {missing},
        frozenset({missing}),
        frozenset(),
        sr.canonical_digest(small_registry),
    )
    assert sr.route_evidence_missing(small_registry, report, "form", "PORTABLE") == {missing}
    complete = sr.InventoryReport(
        keys, keys, frozenset(), frozenset(), sr.canonical_digest(small_registry)
    )
    assert complete.complete
    assert not sr.route_evidence_missing(small_registry, complete, "form", "PORTABLE")
    with pytest.raises(sr.SurfaceRegistryError, match="undeclared route"):
        sr.route_evidence_missing(small_registry, complete, "form", "host-native:invented")


def test_experiment_waiver_does_not_make_route_admissible(small_registry) -> None:
    key = "subject:workspace:surface:RICH"
    keys = frozenset(sr.required_obligations(small_registry))
    report = sr.InventoryReport(
        keys, keys - {key}, frozenset(), frozenset({key}), sr.canonical_digest(small_registry)
    )
    assert not report.complete
    assert sr.route_evidence_missing(small_registry, report, "workspace", "RICH") == {key}


def test_compatibility_endpoints_remain_exact_fixed_shape_anchors(stored_registry) -> None:
    endpoints = {
        s["root_anchor"]: s
        for s in stored_registry["subjects"]
        if s["subject_kind"] == "compatibility_endpoint"
    }
    assert set(endpoints) == {
        "src/attune/elicitation/ask_payload.py:form_to_ask_payload",
        "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_form",
    }
    assert {s["compatibility_contract"]["response_shape"] for s in endpoints.values()} == {
        "questions+metadata.source",
        "success+title+description+batches+optional_surface_note",
    }
    assert all(
        s["compatibility_contract"]["status"] == "compatibility_only" for s in endpoints.values()
    )
    assert all(not any(k in s for k in ("cold_routes", "warm_routes")) for s in endpoints.values())


def test_declared_context_orders_match_the_scoped_design(stored_registry) -> None:
    for subject in stored_registry["subjects"]:
        kind = subject["subject_kind"]
        if kind == "interactive_workspace":
            assert subject["cold_routes"] == ["PORTABLE", "HEADLESS"]
            assert subject["warm_routes"] == ["RICH", "PORTABLE", "HEADLESS"]
        elif kind == "interactive_form":
            if subject["id"] == "server-handle-elicitation-ask":
                assert (
                    subject["cold_routes"]
                    == subject["warm_routes"]
                    == ["mcp-native:native-elicitation"]
                )
            else:
                assert subject["cold_routes"] == [
                    "mcp-native:native-elicitation",
                    "PORTABLE",
                    "HEADLESS",
                ]
                assert subject["warm_routes"] == [
                    "RICH",
                    "mcp-native:native-elicitation",
                    "PORTABLE",
                    "HEADLESS",
                ]
        elif kind.startswith("informational_"):
            assert "cold_routes" not in subject and "warm_routes" not in subject


def test_stale_inventory_report_cannot_admit_route_after_evidence_changes(small_registry) -> None:
    keys = frozenset(sr.required_obligations(small_registry))
    report = sr.InventoryReport(
        keys, keys, frozenset(), frozenset(), sr.canonical_digest(small_registry)
    )
    small_registry["subjects"][0]["implementation_digest"] = "changed"
    with pytest.raises(sr.SurfaceRegistryError, match="stale inventory report"):
        sr.route_evidence_missing(small_registry, report, "workspace", "RICH")


def test_contract_surface_enforcer_is_scoped_to_inventory_not_complete_runtime() -> None:
    text = " ".join(
        (REPO / "content/collaboration/contract.md").read_text(encoding="utf-8").split()
    )
    assert "Surfaces enforcer: `tests/unit/gates/test_surface_parity.py`" in text
    assert "Inventory success is not complete parity" in text
    assert "pending obligations and experiments cannot satisfy route evidence requirements" in text


def test_live_experiment_activation_is_blocked_until_artifact_verification_exists(
    stored_registry, reviewed, installed_evidence
) -> None:
    registry = copy.deepcopy(stored_registry)
    _experiment(registry)
    with pytest.raises(
        sr.SurfaceRegistryError,
        match="live activation requires current artifact/decision verification",
    ):
        sr.validate_inventory(
            registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
        )


def test_stored_renderer_status_edit_cannot_reuse_installed_evidence(
    stored_registry, reviewed, installed_evidence
) -> None:
    registry = copy.deepcopy(stored_registry)
    target = next(
        t for r in registry["renderers"] for t in r["targets"] if t["id"] == "form.askuserquestion"
    )
    target["status"] = "route_active"
    target["evidence_mode"] = "route_roundtrip"
    with pytest.raises(
        sr.SurfaceRegistryError,
        match="renderer:standalone-form:host-native:form.askuserquestion: owning renderer record changed",
    ):
        sr.validate_inventory(
            registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
        )


def test_unrelated_renderer_target_does_not_change_existing_owning_slice(stored_registry) -> None:
    record = copy.deepcopy(stored_registry["renderers"][0])
    before = sr.renderer_record_digest(record, "form.rich")
    record["targets"].append({"id": "independent", "surface": "host-native", "profile_id": "new"})
    assert sr.renderer_record_digest(record, "form.rich") == before


def test_stored_receipts_equal_current_executed_declarations(stored_registry) -> None:
    from attune.elicitation.surface_evidence import replay_renderer_evidence

    declarations, _ = replay_renderer_evidence()
    assert stored_registry["receipts"] == declarations


def test_swapping_receipt_ids_and_digests_cannot_borrow_execution(small_registry) -> None:
    evidence = _synthetic_evidence(small_registry)
    first, second = small_registry["receipts"][:2]
    for key in [
        "id",
        "implementation_digest",
        "fixture_digest",
        "record_digest",
        "normalization_digest",
        "result_digest",
    ]:
        first[key], second[key] = second[key], first[key]
    with pytest.raises(sr.SurfaceRegistryError, match="identity must bind obligation"):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.mark.parametrize("mutation", ["retype", "remove_rich", "erase_targets_and_routes"])
def test_discovered_workspace_cannot_shed_obligations(stored_registry, reviewed, mutation) -> None:
    registry = copy.deepcopy(stored_registry)
    subject = next(s for s in registry["subjects"] if s["id"] == "command_workspace-render")
    if mutation == "retype":
        subject["subject_kind"] = "informational_artifact"
    elif mutation == "remove_rich":
        subject["targets"] = [t for t in subject["targets"] if t["surface"] != "RICH"]
    else:
        subject["targets"] = []
        subject["cold_routes"] = subject["warm_routes"] = []
    with pytest.raises(
        sr.SurfaceRegistryError, match="detected (subject kind changed|target footprint shrank)"
    ):
        sr.validate_producers(registry["subjects"], reviewed.to_dict())


def test_route_requires_its_own_projection_beyond_lifecycle(small_registry) -> None:
    keys = frozenset(sr.required_obligations(small_registry))
    missing = "route:form:HEADLESS:production_projection"
    report = sr.InventoryReport(
        keys,
        keys - {missing},
        frozenset({missing}),
        frozenset(),
        sr.canonical_digest(small_registry),
    )
    assert sr.route_evidence_missing(small_registry, report, "form", "HEADLESS") == {missing}
    assert not sr.route_evidence_missing(small_registry, report, "form", "PORTABLE")


def test_surface_route_without_target_is_rejected(small_registry) -> None:
    subject = small_registry["subjects"][0]
    subject["targets"] = [t for t in subject["targets"] if t["surface"] != "RICH"]
    with pytest.raises(sr.SurfaceRegistryError, match="surface route has no declared target"):
        sr.required_obligations(small_registry)
    report = sr.InventoryReport(
        frozenset(), frozenset(), frozenset(), frozenset(), sr.canonical_digest(small_registry)
    )
    with pytest.raises(sr.SurfaceRegistryError, match="surface route has no declared target"):
        sr.route_evidence_missing(small_registry, report, "workspace", "RICH")


@pytest.mark.parametrize("surface", ["portable", "headless"])
def test_projected_control_contract_mutation_fails(surface, monkeypatch) -> None:
    from attune_forms import renderer_registry as rr

    from attune.elicitation.surface_evidence import replay_renderer_evidence

    original = rr.RendererTarget.resolve

    def altered(target):
        if target.target_id == f"form.{surface}":
            return lambda *args, **kwargs: (
                "x"
                if surface == "portable"
                else {"type": "object", "properties": {"invented": {"type": "string"}}}
            )
        return original(target)

    monkeypatch.setattr(rr.RendererTarget, "resolve", altered)
    with pytest.raises(
        sr.SurfaceRegistryError,
        match="(missing canonical reply contract|projected reply field IDs differ)",
    ):
        replay_renderer_evidence()


def test_delivery_route_id_cannot_be_repointed(
    stored_registry, reviewed, installed_evidence
) -> None:
    registry = copy.deepcopy(stored_registry)
    subject = next(s for s in registry["subjects"] if s["id"] == "plugin-security_guard-module")
    first, second = subject["delivery_routes"][:2]
    first["id"], second["id"] = second["id"], first["id"]
    with pytest.raises(sr.SurfaceRegistryError, match="identity does not bind registration"):
        sr.validate_inventory(
            registry, reviewed.to_dict(), installed_evidence, today=date(2026, 9, 6)
        )


def test_compatibility_production_receipts_are_explicitly_pending(stored_registry) -> None:
    pending = {row["key"] for row in stored_registry["pending_obligations"]}
    assert {
        "compatibility:subject:ask-payload:production_response",
        "compatibility:subject:legacy-render-form:production_response",
    } <= pending


def test_registered_renderer_cannot_hide_in_hook_delivery(stored_registry, reviewed) -> None:
    baseline = copy.deepcopy(reviewed.to_dict())
    subject = next(
        s for s in stored_registry["subjects"] if s["subject_kind"] == "informational_delivery"
    )
    baseline["renderer_call_anchors"].append(
        {
            "anchor": subject["producer_anchors"][0],
            "target": "attune_forms.widget.form_to_widget_html",
            "syntax": "direct",
        }
    )
    with pytest.raises(sr.SurfaceRegistryError, match="registered renderer cannot hide"):
        sr.validate_producers(stored_registry["subjects"], baseline)


@pytest.mark.parametrize(
    "pin",
    [None, [], {}, _SYNTHETIC_BASELINE, {**_baseline_pin(_SYNTHETIC_BASELINE), "extra": []}],
)
def test_baseline_binding_requires_exact_pin_shape(small_registry, pin) -> None:
    small_registry["producer_baseline"] = pin
    with pytest.raises(
        sr.SurfaceRegistryError, match="expected exactly path, schema_version and digest"
    ):
        sr.validate_baseline_pin(small_registry, _SYNTHETIC_BASELINE)


@pytest.mark.parametrize("path", ["/tmp/baseline.json", "../producer_baseline.json", "other.json"])
def test_baseline_pin_cannot_select_another_fixture(small_registry, path) -> None:
    small_registry["producer_baseline"]["path"] = path
    with pytest.raises(sr.SurfaceRegistryError, match="unexpected fixture path"):
        sr.validate_baseline_pin(small_registry, _SYNTHETIC_BASELINE)


@pytest.mark.parametrize("mutation", ["pin", "fixture", "both"])
def test_baseline_pin_requires_supported_matching_schema(small_registry, mutation) -> None:
    baseline = copy.deepcopy(_SYNTHETIC_BASELINE)
    if mutation in {"pin", "both"}:
        small_registry["producer_baseline"]["schema_version"] = "future/2"
    if mutation in {"fixture", "both"}:
        baseline["schema_version"] = "future/2"
    with pytest.raises(
        sr.SurfaceRegistryError, match="unknown or mismatched fixture schema_version"
    ):
        sr.validate_baseline_pin(small_registry, baseline)


def test_baseline_content_drift_fails_before_report_with_actionable_diagnostic(
    stored_registry, reviewed
) -> None:
    baseline = reviewed.to_dict()
    # Same roots and semantic obligations: the full-content pin must still fail.
    call = baseline["renderer_call_anchors"][0]
    call["syntax"] = "qualified" if call["syntax"] != "qualified" else "direct"
    sr.validate_producers(stored_registry["subjects"], baseline)
    expected = stored_registry["producer_baseline"]["digest"]
    actual = sr.canonical_digest(baseline)
    assert expected != actual
    with pytest.raises(sr.SurfaceRegistryError, match="digest mismatch") as caught:
        sr.validate_inventory(stored_registry, baseline, {}, today=date(2026, 9, 6))
    message = str(caught.value)
    assert f"expected {expected}; actual {actual}" in message
    assert sr.BASELINE_REGEN in message
    assert "write_baseline" in message and "re-derive" in message and "review both diffs" in message


def test_pin_refresh_invalidates_previously_issued_inventory_report(
    stored_registry, reviewed, installed_evidence
) -> None:
    registry = copy.deepcopy(stored_registry)
    baseline = reviewed.to_dict()
    previous = sr.validate_inventory(registry, baseline, installed_evidence, today=date(2026, 9, 6))
    call = baseline["renderer_call_anchors"][0]
    call["syntax"] = "qualified" if call["syntax"] != "qualified" else "direct"
    registry["producer_baseline"] = _baseline_pin(baseline)
    current = sr.validate_inventory(registry, baseline, installed_evidence, today=date(2026, 9, 6))
    assert previous.required_keys == current.required_keys
    assert previous.registry_digest != current.registry_digest
    subject = next(s for s in registry["subjects"] if "RICH" in s.get("warm_routes", []))
    with pytest.raises(sr.SurfaceRegistryError, match="stale inventory report"):
        sr.route_evidence_missing(registry, previous, subject["id"], "RICH")


def test_baseline_pin_is_canonical_json_not_serialization_order(stored_registry, reviewed) -> None:
    baseline = reviewed.to_dict()
    reordered = json.loads(json.dumps(dict(reversed(list(baseline.items()))), indent=4))
    sr.validate_baseline_pin(stored_registry, reordered)


def test_experiment_uses_resolved_shipped_roots_and_rejects_stale_pin(small_registry) -> None:
    _experiment(small_registry)
    baseline = copy.deepcopy(_SYNTHETIC_BASELINE)
    baseline["shipped_roots"].append("experiments/surface-parity")
    obligations = sr.required_obligations(small_registry)
    with pytest.raises(sr.SurfaceRegistryError, match="digest mismatch"):
        sr.validate_experiments(small_registry, obligations, date(2026, 9, 6), baseline=baseline)
    small_registry["producer_baseline"] = _baseline_pin(baseline)
    with pytest.raises(sr.SurfaceRegistryError, match="shipped experiment root"):
        sr.validate_experiments(small_registry, obligations, date(2026, 9, 6), baseline=baseline)


@pytest.mark.parametrize(
    "path,event,matcher,signature,sink",
    [
        ("plugin/hooks/memory_backend_notice.py", "SessionStart", "", "context_stdout", "print"),
        (
            "src/attune/hooks/scripts/worktree_add_guard.py",
            "PreToolUse",
            "Bash",
            "exit2_stderr",
            "print(file=sys.stderr)",
        ),
    ],
)
def test_new_hook_subjects_have_qualified_delivery_obligations(
    stored_registry, reviewed, path, event, matcher, signature, sink
) -> None:
    root = f"{path}:<module>"
    subject = next(s for s in stored_registry["subjects"] if s["root_anchor"] == root)
    assert subject["subject_kind"] == "informational_delivery"
    assert subject["producer_anchors"] == [f"{path}:main"]
    assert len(subject["delivery_routes"]) == 1
    route = subject["delivery_routes"][0]
    assert (
        route["event"],
        route["matcher"],
        route["signature"],
        route["sink"],
        route["destination"],
    ) == (event, matcher, signature, sink, "model_context")
    pending = {row["key"] for row in stored_registry["pending_obligations"]}
    for dimension in ("content_schema", "destination", "delivery"):
        assert f"delivery:{subject['id']}:{route['id']}:{dimension}" in pending
    changed = copy.deepcopy(stored_registry["subjects"])
    changed.remove(next(s for s in changed if s["id"] == subject["id"]))
    with pytest.raises(sr.SurfaceRegistryError, match="exactly one subject") as caught:
        sr.validate_producers(changed, reviewed.to_dict())
    assert root in str(caught.value)


def test_refreshed_pin_does_not_hide_new_hook_signature_at_same_root(
    stored_registry, reviewed
) -> None:
    registry = copy.deepcopy(stored_registry)
    baseline = reviewed.to_dict()
    hook = next(
        h
        for h in baseline["hook_envelope_anchors"]
        if h["anchor"] == "src/attune/hooks/scripts/worktree_add_guard.py:main"
    )
    baseline["hook_envelope_anchors"].append(
        {**hook, "signature": "pretooluse_deny", "sink": "json_stdout"}
    )
    registry["producer_baseline"] = _baseline_pin(baseline)
    assert sr.producer_roots(baseline) == sr.producer_roots(reviewed.to_dict())
    sr.validate_producers(registry["subjects"], baseline)
    with pytest.raises(sr.SurfaceRegistryError, match="event-qualified delivery routes"):
        sr.validate_inventory(registry, baseline, {}, today=date(2026, 9, 6))


def test_renderer_reordering_cannot_change_receipt_controls(monkeypatch) -> None:
    from attune.elicitation import surface_evidence as se

    original, _ = se.replay_renderer_evidence()
    monkeypatch.setattr(se.rr, "RENDERER_REGISTRY", tuple(reversed(se.rr.RENDERER_REGISTRY)))
    reordered, _ = se.replay_renderer_evidence()
    assert {r["id"]: r for r in original} == {r["id"]: r for r in reordered}


@pytest.mark.parametrize("field", ["event", "matcher", "signature", "sink", "destination"])
def test_non_hook_route_content_invalidates_old_identity(small_registry, field) -> None:
    route = small_registry["subjects"][-1]["delivery_routes"][0]
    before = sr.required_obligations(small_registry)
    route[field] += "changed"
    with pytest.raises(
        sr.SurfaceRegistryError, match="delivery route identity does not bind content"
    ):
        sr.required_obligations(small_registry)
    route["id"] = sr.canonical_digest({k: v for k, v in route.items() if k != "id"})[:16]
    after = sr.required_obligations(small_registry)
    assert len(set(before) - set(after)) == 4
    assert len(set(after) - set(before)) == 4


def test_artifact_collision_preserves_helper_provenance(reviewed) -> None:
    baseline = reviewed.to_dict()
    before = sr.producer_roots(baseline)
    anchor = next(k for k, v in before.items() if v != [k])
    baseline["artifacts"].append({"anchor": anchor})
    assert set(sr.producer_roots(baseline)[anchor]) == set(before[anchor]) | {anchor}


@pytest.mark.parametrize("field", ["fixture", "evidence_mode"])
@pytest.mark.parametrize("value", [None, "", " ", 1])
def test_matching_absent_or_invalid_provenance_cannot_pass(small_registry, field, value) -> None:
    evidence = _synthetic_evidence(small_registry)
    receipt = small_registry["receipts"][0]
    for row in (receipt, evidence[receipt["id"]]):
        if value is None:
            row.pop(field)
        else:
            row[field] = value
    with pytest.raises(sr.SurfaceRegistryError, match=f"stale/missing {field}"):
        sr.validate_receipts(
            small_registry,
            sr.required_obligations(small_registry),
            evidence,
            today=date(2026, 9, 6),
            baseline=_SYNTHETIC_BASELINE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "subjects",
        "host_profiles",
        "renderers",
        "receipts",
        "pending_obligations",
        "experiments",
        "experiment_history",
        "experiment_exceptions",
    ],
)
def test_missing_registry_collection_has_keyed_failure(stored_registry, reviewed, field) -> None:
    registry = copy.deepcopy(stored_registry)
    del registry[field]
    with pytest.raises(sr.SurfaceRegistryError, match=f"{field}: missing or invalid collection"):
        sr.validate_inventory(registry, reviewed.to_dict(), {}, today=date(2026, 9, 6))


def test_workspace_cannot_inject_unvalidated_transport_ref(small_registry) -> None:
    small_registry["subjects"][0]["route_transport_refs"] = {
        "RICH": {"kind": "host_profile", "id": "missing"}
    }
    with pytest.raises(sr.SurfaceRegistryError, match="workspace owns its lifecycle"):
        sr.required_obligations(small_registry)


def test_relocated_ask_handler_loses_exact_anchor_exemption(reviewed, stored_registry) -> None:
    baseline = reviewed.to_dict()
    subjects = copy.deepcopy(stored_registry["subjects"])
    old = "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_ask"
    new = "src/attune/other.py:AttuneMCPServer._handle_elicitation_ask"
    subject = next(s for s in subjects if s["root_anchor"] == old)
    subject["root_anchor"] = new
    subject["producer_anchors"] = [new]
    for group in ("renderer_call_anchors", "package_host_envelope_anchors"):
        for row in baseline[group]:
            if row["anchor"] == old:
                row["anchor"] = new
    with pytest.raises(sr.SurfaceRegistryError, match="detected target footprint shrank"):
        sr.validate_producers(subjects, baseline)


@pytest.mark.parametrize(
    "surface,output",
    [
        ("headless", []),
        ("headless", {"type": "nonsense"}),
        ("headless", {"type": "string"}),
        ("portable", {}),
        ("portable", "```json\n[]\n```"),
        ("portable", "```json\n{\n```"),
        ("portable", '```json\n{"answers": []}\n```'),
    ],
)
def test_malformed_reply_contract_has_surface_key(surface, output) -> None:
    from attune.elicitation import surface_evidence as se

    with pytest.raises(sr.SurfaceRegistryError, match=f"(?i){surface}"):
        se._projected_answers(output, surface, {"answer": "value"})


@pytest.mark.parametrize("output", [{}, [1], [[{}]], [[{"question_id": "x", "options": 1}]]])
def test_malformed_specialized_questions_have_target_key(output) -> None:
    from attune.elicitation import surface_evidence as se

    record = next(r for r in se.rr.RENDERER_REGISTRY if r.family == "form")
    target = next(t for t in record.targets if t.status == "compatibility_only")
    with pytest.raises(sr.SurfaceRegistryError, match=target.target_id):
        se._form_collection(output, target, record)
