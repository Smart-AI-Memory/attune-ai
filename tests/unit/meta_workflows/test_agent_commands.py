"""Unit tests for attune.meta_workflows.cli_commands.agent_commands.

Covers create_agent and create_team CLI commands.
Uses Typer's CliRunner with the app declared in cli_commands/__init__.py,
mirroring the pattern in test_workflow_commands.py.

KNOWN PRODUCTION BUG (documented, not fixed, by design -- see
docs/COVERAGE_BUG_LOG.md): `create_agent`'s final two lines split a Rich
markup `[dim]...[/dim]` span across two separate `console.print()` calls:

    console.print(f"\\n[dim]Agent tier '{tier}' will cost approximately:")
    console.print(f"   {costs.get(tier, costs['capable'])} per execution[/dim]\\n")

Rich parses markup independently per `console.print()` call, so the second
call's lone `[/dim]` has no matching open tag and raises
`rich.errors.MarkupError`. This means `create-agent` crashes on EVERY
successful invocation (both interactive and quick mode) -- it has never
completed cleanly. `create-team`'s analogous final line is a single
`console.print()` call and does not share this bug. Tests below assert
the command's REAL (buggy) behavior: exit_code == 1 with a MarkupError,
after all prior output (including the JSON spec and any file save) has
already been emitted.
"""

from __future__ import annotations

import json

import pytest
from rich.errors import MarkupError
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app


@pytest.fixture
def runner():
    return CliRunner()


def _run(runner, args, input_text=None):
    return runner.invoke(meta_workflow_app, args, input=input_text)


def _assert_crashes_on_cost_display(result):
    """Shared assertion for the known create-agent MarkupError crash."""
    assert result.exit_code == 1
    assert isinstance(result.exception, MarkupError)
    assert "closing tag" in str(result.exception)
    assert "[/dim]" in str(result.exception)


# ---------------------------------------------------------------------------
# create_agent -- quick mode validation
# ---------------------------------------------------------------------------


class TestCreateAgentQuickModeValidation:
    def test_missing_both_name_and_role(self, runner):
        result = _run(runner, ["create-agent", "-q"])
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "--name and --role required in quick mode" in result.output
        assert "Use --interactive for guided creation" in result.output
        assert "Agent Specification Created" not in result.output

    def test_missing_role_only(self, runner):
        result = _run(runner, ["create-agent", "-q", "-n", "X"])
        assert result.exit_code == 1
        assert "--name and --role required in quick mode" in result.output

    def test_missing_name_only(self, runner):
        result = _run(runner, ["create-agent", "-q", "-r", "Y"])
        assert result.exit_code == 1
        assert "--name and --role required in quick mode" in result.output


# ---------------------------------------------------------------------------
# create_agent -- quick mode success (crashes on cost display -- see module
# docstring). Coverage of the tier/cost dict branches is still exercised:
# the f-string evaluates costs.get(...) before console.print() raises.
# ---------------------------------------------------------------------------


class TestCreateAgentQuickModeSuccess:
    def test_default_tier_builds_expected_spec(self, runner):
        result = _run(runner, ["create-agent", "-q", "-n", "Foo", "-r", "Do the thing"])
        _assert_crashes_on_cost_display(result)
        assert "Agent Specification Created" in result.output
        assert '"name": "Foo"' in result.output
        assert '"role": "Do the thing"' in result.output
        assert '"tier": "capable"' in result.output
        assert '"tools": []' in result.output
        assert '"success_criteria": "Task completed successfully"' in result.output
        assert '"base_template": "generic"' in result.output
        assert "Next Steps:" in result.output
        assert "Agent tier 'capable' will cost approximately:" in result.output

    def test_cheap_tier(self, runner):
        result = _run(runner, ["create-agent", "-q", "-n", "CheapBot", "-r", "role", "-t", "cheap"])
        _assert_crashes_on_cost_display(result)
        assert '"tier": "cheap"' in result.output
        assert "Agent tier 'cheap' will cost approximately:" in result.output

    def test_premium_tier(self, runner):
        result = _run(
            runner, ["create-agent", "-q", "-n", "PremBot", "-r", "role", "-t", "premium"]
        )
        _assert_crashes_on_cost_display(result)
        assert '"tier": "premium"' in result.output
        assert "Agent tier 'premium' will cost approximately:" in result.output

    def test_unknown_tier_falls_back_to_capable_cost_lookup(self, runner):
        """costs.get(tier, costs['capable']) fallback branch for an
        unrecognized tier string -- the tier itself is stored as-is
        (unvalidated), only the cost lookup falls back."""
        result = _run(runner, ["create-agent", "-q", "-n", "UnkBot", "-r", "role", "-t", "turbo"])
        _assert_crashes_on_cost_display(result)
        assert '"tier": "turbo"' in result.output
        assert "Agent tier 'turbo' will cost approximately:" in result.output

    def test_output_file_is_saved_despite_downstream_crash(self, runner, tmp_path):
        out_path = tmp_path / "spec.json"
        result = _run(
            runner,
            [
                "create-agent",
                "-q",
                "-n",
                "Saver",
                "-r",
                "Save role",
                "-o",
                str(out_path),
            ],
        )
        _assert_crashes_on_cost_display(result)
        assert out_path.exists()
        saved = json.loads(out_path.read_text())
        assert saved == {
            "name": "Saver",
            "role": "Save role",
            "tier": "capable",
            "tools": [],
            "success_criteria": "Task completed successfully",
            "base_template": "generic",
        }
        assert "Saved to:" in result.output
        # Rich soft-wraps long paths across lines at the terminal width;
        # strip newlines before checking the full path is present.
        assert str(out_path) in result.output.replace("\n", "")


# ---------------------------------------------------------------------------
# create_agent -- interactive mode
# ---------------------------------------------------------------------------


class TestCreateAgentInteractive:
    def test_default_name_derived_from_purpose(self, runner):
        """No --name given: name = purpose.split()[0].title() + 'Agent'.
        Also covers tasks/tools comma-split-and-strip."""
        answers = (
            "\n".join(
                [
                    "fix bugs fast",  # purpose
                    "write tests, review code",  # tasks
                    "cheap",  # tier
                    "file_read, code_exec",  # tools
                    "all bugs fixed",  # success
                ]
            )
            + "\n"
        )
        result = _run(runner, ["create-agent"], answers)
        _assert_crashes_on_cost_display(result)
        assert '"name": "FixAgent"' in result.output
        assert '"role": "fix bugs fast"' in result.output
        assert '"tasks": [' in result.output
        assert '"write tests",' in result.output
        assert '"review code"' in result.output
        assert '"tier": "cheap"' in result.output
        assert '"tools": [' in result.output
        assert '"file_read",' in result.output
        assert '"code_exec"' in result.output
        assert '"success_criteria": "all bugs fixed"' in result.output

    def test_cli_name_preserved_and_cli_tier_overwritten_by_prompt(self, runner):
        """When --name is passed, the interactive branch keeps it (does NOT
        derive from purpose). But --tier is unconditionally overwritten by
        the tier prompt regardless of the CLI value -- a blank tier answer
        falls back to the prompt's own default ('capable'), not the
        --tier CLI value ('premium'). Also covers the 'none' tools default
        (blank input) -> tools == []."""
        answers = (
            "\n".join(
                [
                    "some purpose text",  # purpose
                    "task1, task2",  # tasks
                    "",  # tier blank -> prompt default "capable"
                    "",  # tools blank -> prompt default "none" -> []
                    "success crit",  # success
                ]
            )
            + "\n"
        )
        result = _run(
            runner,
            ["create-agent", "--name", "CustomBot", "--tier", "premium"],
            answers,
        )
        _assert_crashes_on_cost_display(result)
        assert '"name": "CustomBot"' in result.output
        assert '"tier": "capable"' in result.output
        assert '"premium"' not in result.output
        assert '"tools": []' in result.output


# ---------------------------------------------------------------------------
# create_team -- quick mode validation
# ---------------------------------------------------------------------------


class TestCreateTeamQuickModeValidation:
    def test_missing_both_name_and_goal(self, runner):
        result = _run(runner, ["create-team", "-q"])
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "--name and --goal required in quick mode" in result.output
        assert "Use --interactive for guided creation" in result.output
        assert "Agent Team Template Created" not in result.output

    def test_missing_goal_only(self, runner):
        result = _run(runner, ["create-team", "-q", "-n", "X"])
        assert result.exit_code == 1
        assert "--name and --goal required in quick mode" in result.output

    def test_missing_name_only(self, runner):
        result = _run(runner, ["create-team", "-q", "-g", "Y"])
        assert result.exit_code == 1
        assert "--name and --goal required in quick mode" in result.output


# ---------------------------------------------------------------------------
# create_team -- quick mode success (no crash -- create_team's final print
# is a single console.print() call, so its [dim]...[/dim] span is matched).
# ---------------------------------------------------------------------------


class TestCreateTeamQuickModeSuccess:
    def test_builds_fixed_three_agent_team(self, runner):
        result = _run(runner, ["create-team", "-q", "-n", "T1", "-g", "ship it"])
        assert result.exit_code == 0
        assert result.exception is None
        assert "Agent Team Template Created" in result.output
        assert '"id": "t1"' in result.output
        assert '"name": "T1"' in result.output
        assert '"description": "ship it"' in result.output
        assert '"collaboration_pattern": "sequential"' in result.output
        assert '"role": "Analyst"' in result.output
        assert '"purpose": "Analyze requirements"' in result.output
        assert '"role": "Executor"' in result.output
        assert '"role": "Validator"' in result.output
        assert '"min": 0.03' in result.output
        assert '"max": 0.45' in result.output
        assert "Estimated cost: $0.03 - $0.45 per execution" in result.output
        assert "empathy meta-workflow run t1" in result.output

    def test_output_file_is_saved(self, runner, tmp_path):
        out_path = tmp_path / "team.json"
        result = _run(
            runner,
            ["create-team", "-q", "-n", "T2", "-g", "ship it", "-o", str(out_path)],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        saved = json.loads(out_path.read_text())
        assert saved["id"] == "t2"
        assert saved["name"] == "T2"
        assert saved["description"] == "ship it"
        assert len(saved["agents"]) == 3
        assert saved["estimated_cost_range"] == {"min": 0.03, "max": 0.45}
        assert "Saved to:" in result.output
        # Rich soft-wraps long paths across lines at the terminal width;
        # strip newlines before checking the full path is present.
        assert str(out_path) in result.output.replace("\n", "")


# ---------------------------------------------------------------------------
# create_team -- interactive mode
# ---------------------------------------------------------------------------


class TestCreateTeamInteractive:
    def test_single_agent_all_explicit(self, runner):
        answers = (
            "\n".join(
                [
                    "ship a release",  # goal
                    "1",  # agent_count
                    "Analyst",  # agent1 role
                    "analyze requirements",  # agent1 purpose
                    "cheap",  # agent1 tier
                    "parallel",  # collaboration pattern
                    "Ship Team",  # team name
                ]
            )
            + "\n"
        )
        result = _run(runner, ["create-team"], answers)
        assert result.exit_code == 0
        assert '"id": "ship-team"' in result.output
        assert '"name": "Ship Team"' in result.output
        assert '"description": "ship a release"' in result.output
        assert '"collaboration_pattern": "parallel"' in result.output
        assert '"role": "Analyst"' in result.output
        assert '"purpose": "analyze requirements"' in result.output
        assert '"tier": "cheap"' in result.output
        assert '"min": 0.01' in result.output
        assert '"max": 0.15' in result.output
        assert "Estimated cost: $0.01 - $0.15 per execution" in result.output

    def test_cli_goal_overwritten_and_blank_answers_use_defaults(self, runner):
        """The goal prompt ALWAYS overwrites any --goal CLI value (unlike
        create_agent's name, there is no `if not goal` guard). Blank
        answers for tier/pattern/name fall through to their prompt
        defaults ('capable', 'sequential', and the goal-derived name)."""
        answers = (
            "\n".join(
                [
                    "prepare release notes",  # goal (overwrites --goal below)
                    "1",  # agent_count
                    "Reviewer",  # role
                    "review the notes",  # purpose
                    "",  # tier blank -> default "capable"
                    "",  # pattern blank -> default "sequential"
                    "",  # name blank -> default "PrepareTeam"
                ]
            )
            + "\n"
        )
        result = _run(
            runner,
            ["create-team", "--goal", "ignored goal case"],
            answers,
        )
        assert result.exit_code == 0
        assert '"description": "prepare release notes"' in result.output
        assert "ignored goal case" not in result.output
        assert '"tier": "capable"' in result.output
        assert '"collaboration_pattern": "sequential"' in result.output
        assert '"name": "PrepareTeam"' in result.output
        assert '"id": "prepareteam"' in result.output

    def test_multiple_agents_loop_preserves_order(self, runner):
        answers = (
            "\n".join(
                [
                    "build a bot",  # goal
                    "2",  # agent_count
                    "Builder",  # agent1 role
                    "build the thing",  # agent1 purpose
                    "capable",  # agent1 tier
                    "Tester",  # agent2 role
                    "test the thing",  # agent2 purpose
                    "cheap",  # agent2 tier
                    "sequential",  # pattern
                    "Bot Squad",  # name
                ]
            )
            + "\n"
        )
        result = _run(runner, ["create-team"], answers)
        assert result.exit_code == 0
        assert '"id": "bot-squad"' in result.output

        # Extract agents from the printed JSON panel for an exact structural
        # assertion (order matters -- Builder must precede Tester). Rich
        # draws box-drawing border chars ("│") at the start/end of each
        # panel line; strip them before parsing back to JSON.
        start = result.output.index("{")
        end = result.output.rindex("}") + 1
        raw_lines = result.output[start:end].splitlines()
        json_text = "\n".join(line.strip(" │") for line in raw_lines)
        data = json.loads(json_text)
        assert data["agents"] == [
            {
                "role": "Builder",
                "purpose": "build the thing",
                "tier": "capable",
                "base_template": "generic",
            },
            {
                "role": "Tester",
                "purpose": "test the thing",
                "tier": "cheap",
                "base_template": "generic",
            },
        ]
        assert data["estimated_cost_range"] == {"min": 0.02, "max": 0.3}
