"""CLI for Socratic Workflow Builder

Provides command-line interface for:
- Starting interactive Socratic sessions
- Listing and resuming sessions
- Generating workflows from sessions
- Managing blueprints

Commands:
    empathy socratic start [--goal "..."]
    empathy socratic resume <session_id>
    empathy socratic list [--state completed|in_progress]
    empathy socratic generate <session_id>
    empathy socratic blueprints [--domain security]
    empathy socratic run <blueprint_id> [--input file.json]

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import json
import sys

from .cli_console import (
    Console,  # noqa: F401 - re-exported
    _input_boolean,  # noqa: F401 - re-exported
    _input_multi_select,  # noqa: F401 - re-exported
    _input_single_select,  # noqa: F401 - re-exported
    _input_text,  # noqa: F401 - re-exported
    _input_text_area,  # noqa: F401 - re-exported
    console,
    render_form_interactive,
)
from .engine import SocraticWorkflowBuilder
from .session import SessionState
from .storage import get_default_storage

# Use the module-level console instance from cli_console


# =============================================================================
# CLI COMMANDS
# =============================================================================


def cmd_start(args: argparse.Namespace) -> int:
    """Start a new Socratic session."""
    storage = get_default_storage()
    builder = SocraticWorkflowBuilder()

    console.header("SOCRATIC WORKFLOW BUILDER")

    # Start session
    session = builder.start_session()
    console.info(f"Session ID: {session.session_id[:8]}...")

    # Get initial goal
    if args.goal:
        goal = args.goal
        console.info(f"Goal: {goal}")
    else:
        initial_form = builder.get_initial_form()
        answers = render_form_interactive(initial_form, console)
        goal = answers.get("goal", "")

    if not goal:
        console.error("No goal provided")
        return 1

    # Set goal and analyze
    session = builder.set_goal(session, goal)
    storage.save_session(session)

    # Show analysis
    if session.goal_analysis:
        console.subheader("Goal Analysis")
        print(f"  Domain: {session.goal_analysis.domain}")
        print(f"  Confidence: {session.goal_analysis.confidence:.0%}")

        if session.goal_analysis.ambiguities:
            print()
            console.warning("Ambiguities detected:")
            for amb in session.goal_analysis.ambiguities:
                print(f"    \u2022 {amb}")

    # Interactive questioning loop
    while not builder.is_ready_to_generate(session):
        form = builder.get_next_questions(session)
        if not form:
            break

        answers = render_form_interactive(form, console)
        session = builder.submit_answers(session, answers)
        storage.save_session(session)

        # Show progress
        summary = builder.get_session_summary(session)
        console.info(f"Requirements completeness: {summary['requirements_completeness']:.0%}")

    # Generate workflow
    if builder.is_ready_to_generate(session):
        console.subheader("Generating Workflow")

        workflow = builder.generate_workflow(session)
        storage.save_session(session)

        if session.blueprint:
            storage.save_blueprint(session.blueprint)

        console.success("Workflow generated!")
        print()
        print(workflow.describe())

        if session.blueprint:
            console.info(f"Blueprint ID: {session.blueprint.id[:8]}...")

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume an existing session."""
    storage = get_default_storage()
    builder = SocraticWorkflowBuilder()

    # Find session
    session = storage.load_session(args.session_id)

    # Try partial match
    if not session:
        sessions = storage.list_sessions()
        matches = [s for s in sessions if s["session_id"].startswith(args.session_id)]
        if len(matches) == 1:
            session = storage.load_session(matches[0]["session_id"])
        elif len(matches) > 1:
            console.error(f"Multiple sessions match '{args.session_id}':")
            for m in matches:
                print(f"  - {m['session_id'][:8]}... ({m['state']})")
            return 1

    if not session:
        console.error(f"Session not found: {args.session_id}")
        return 1

    console.header(f"RESUMING SESSION {session.session_id[:8]}...")
    console.info(f"Goal: {session.goal[:80]}...")
    console.info(f"State: {session.state.value}")

    # Rebuild builder state
    if session.goal:
        builder._sessions[session.session_id] = session

    # Continue questioning or generate
    if session.state == SessionState.COMPLETED:
        console.success("Session already completed")
        return 0

    while not builder.is_ready_to_generate(session):
        form = builder.get_next_questions(session)
        if not form:
            break

        answers = render_form_interactive(form, console)
        session = builder.submit_answers(session, answers)
        storage.save_session(session)

    if builder.is_ready_to_generate(session):
        console.subheader("Generating Workflow")

        workflow = builder.generate_workflow(session)
        storage.save_session(session)

        if session.blueprint:
            storage.save_blueprint(session.blueprint)

        console.success("Workflow generated!")
        print()
        print(workflow.describe())

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List sessions."""
    storage = get_default_storage()

    state = None
    if args.state:
        try:
            state = SessionState(args.state)
        except ValueError:
            console.error(f"Invalid state: {args.state}")
            return 1

    sessions = storage.list_sessions(state=state, limit=args.limit)

    if not sessions:
        console.info("No sessions found")
        return 0

    console.header("SOCRATIC SESSIONS")

    headers = ["ID", "State", "Goal", "Updated"]
    rows = []
    for s in sessions:
        rows.append(
            [
                s["session_id"][:8],
                s["state"],
                (
                    (s.get("goal") or "")[:40] + "..."
                    if len(s.get("goal") or "") > 40
                    else s.get("goal") or ""
                ),
                s.get("updated_at", "")[:16],
            ],
        )

    console.table(headers, rows)
    return 0


def cmd_blueprints(args: argparse.Namespace) -> int:
    """List blueprints."""
    storage = get_default_storage()

    blueprints = storage.list_blueprints(domain=args.domain, limit=args.limit)

    if not blueprints:
        console.info("No blueprints found")
        return 0

    console.header("WORKFLOW BLUEPRINTS")

    headers = ["ID", "Name", "Domain", "Agents", "Generated"]
    rows = []
    for b in blueprints:
        rows.append(
            [
                b["id"][:8] if b.get("id") else "?",
                b.get("name", "")[:30],
                b.get("domain", ""),
                str(b.get("agents_count", 0)),
                (b.get("generated_at") or "")[:16],
            ],
        )

    console.table(headers, rows)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show details of a session or blueprint."""
    storage = get_default_storage()

    # Try as session first
    session = storage.load_session(args.id)
    if session:
        console.header(f"SESSION: {session.session_id[:8]}...")

        print(f"State: {session.state.value}")
        print(f"Goal: {session.goal}")
        print(f"Created: {session.created_at}")
        print(f"Updated: {session.updated_at}")

        if session.goal_analysis:
            console.subheader("Analysis")
            print(f"Domain: {session.goal_analysis.domain}")
            print(f"Confidence: {session.goal_analysis.confidence:.0%}")
            print(f"Intent: {session.goal_analysis.intent}")

        if session.requirements.must_have:
            console.subheader("Requirements")
            for req in session.requirements.must_have:
                print(f"  \u2022 {req}")

        return 0

    # Try as blueprint
    blueprint = storage.load_blueprint(args.id)
    if blueprint:
        console.header(f"BLUEPRINT: {blueprint.name}")

        print(f"ID: {blueprint.id}")
        print(f"Domain: {blueprint.domain}")
        print(f"Languages: {', '.join(blueprint.supported_languages)}")
        print(f"Quality Focus: {', '.join(blueprint.quality_focus)}")

        console.subheader("Agents")
        for agent in blueprint.agents:
            print(f"  \u2022 {agent.spec.name} ({agent.spec.role.value})")
            print(f"    Goal: {agent.spec.goal[:60]}...")

        console.subheader("Stages")
        for stage in blueprint.stages:
            parallel = "(parallel)" if stage.parallel else "(sequential)"
            print(f"  \u2022 {stage.name} {parallel}")
            print(f"    Agents: {', '.join(stage.agent_ids)}")

        return 0

    console.error(f"Not found: {args.id}")
    return 1


def cmd_delete(args: argparse.Namespace) -> int:
    """Delete a session."""
    storage = get_default_storage()

    if not args.force:
        response = input(f"Delete session {args.session_id}? (y/N): ").strip().lower()
        if response != "y":
            console.info("Cancelled")
            return 0

    if storage.delete_session(args.session_id):
        console.success(f"Deleted session {args.session_id}")
        return 0
    console.error(f"Session not found: {args.session_id}")
    return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Export a blueprint to JSON."""
    storage = get_default_storage()

    blueprint = storage.load_blueprint(args.blueprint_id)
    if not blueprint:
        console.error(f"Blueprint not found: {args.blueprint_id}")
        return 1

    data = blueprint.to_dict()

    if args.output:
        from attune.security.path_validation import _validate_file_path

        validated = _validate_file_path(args.output)
        with validated.open("w") as f:
            json.dump(data, f, indent=2, default=str)
        console.success(f"Exported to {validated}")
    else:
        print(json.dumps(data, indent=2, default=str))

    return 0


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="attune socratic",
        description="Socratic Workflow Builder - Generate agent workflows through guided questioning",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # start
    start_parser = subparsers.add_parser("start", help="Start a new Socratic session")
    start_parser.add_argument("--goal", "-g", help="Initial goal (skip first question)")
    start_parser.add_argument("--non-interactive", action="store_true", help="Non-interactive mode")

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume an existing session")
    resume_parser.add_argument("session_id", help="Session ID (can be partial)")

    # list
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument(
        "--state",
        "-s",
        choices=[
            "awaiting_goal",
            "awaiting_answers",
            "ready_to_generate",
            "completed",
            "cancelled",
        ],
    )
    list_parser.add_argument("--limit", "-n", type=int, default=20)

    # blueprints
    bp_parser = subparsers.add_parser("blueprints", help="List workflow blueprints")
    bp_parser.add_argument("--domain", "-d", help="Filter by domain")
    bp_parser.add_argument("--limit", "-n", type=int, default=20)

    # show
    show_parser = subparsers.add_parser("show", help="Show session or blueprint details")
    show_parser.add_argument("id", help="Session or blueprint ID")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a session")
    delete_parser.add_argument("session_id", help="Session ID")
    delete_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")

    # export
    export_parser = subparsers.add_parser("export", help="Export blueprint to JSON")
    export_parser.add_argument("blueprint_id", help="Blueprint ID")
    export_parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "start": cmd_start,
        "resume": cmd_resume,
        "list": cmd_list,
        "blueprints": cmd_blueprints,
        "show": cmd_show,
        "delete": cmd_delete,
        "export": cmd_export,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            return cmd_func(args)
        except KeyboardInterrupt:
            print()
            console.info("Interrupted")
            return 130
        except Exception as e:  # noqa: BLE001
            console.error(f"Error: {e}")
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
