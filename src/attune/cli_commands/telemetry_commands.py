"""Telemetry CLI commands.

Commands for viewing usage, cost savings, model performance,
agent status, and coordination signals.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

logger = logging.getLogger(__name__)


def cmd_telemetry_show(args: Namespace) -> int:
    """Display usage summary."""
    try:
        from attune.models.telemetry import TelemetryStore

        store = TelemetryStore()

        print("\n📊 Telemetry Summary\n")
        print("-" * 60)
        print(f"  Period:         Last {args.days} days")

        # Use single-pass aggregation for efficiency with large datasets
        summary = store.get_summary()

        if summary["source"] == "workflows":
            print(f"  Workflow runs:  {summary['workflow_count']:,}")
            print(f"  Total tokens:   {summary['total_tokens']:,}")
            print(f"  Total cost:     ${summary['total_cost']:.2f}")
        elif summary["source"] == "calls":
            print(f"  API calls:      {summary['call_count']:,}")
            print(f"  Total tokens:   {summary['total_tokens']:,}")
            print(f"  Total cost:     ${summary['total_cost']:.2f}")
        else:
            print("  No telemetry data found.")

        print("-" * 60)
        return 0

    except ImportError:
        print("❌ Telemetry module not available")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Telemetry error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_savings(args: Namespace) -> int:
    """Show cost savings from tier routing."""
    try:
        from attune.models.telemetry import TelemetryStore

        store = TelemetryStore()

        print("\n💰 Cost Savings Report\n")
        print("-" * 60)
        print(f"  Period:              Last {args.days} days")

        # Calculate savings from workflow runs
        records = store.get_workflows(limit=1000)
        if records:
            actual_cost = sum(r.total_cost for r in records)
            total_tokens = sum(r.total_input_tokens + r.total_output_tokens for r in records)

            # Calculate what premium-only pricing would cost
            # Using Claude Opus pricing as premium baseline: ~$15/1M input, ~$75/1M output
            # Simplified: ~$45/1M tokens average (blended input/output)
            premium_rate_per_token = 45.0 / 1_000_000
            baseline_cost = total_tokens * premium_rate_per_token

            # Only show savings if we actually routed to cheaper models
            if baseline_cost > actual_cost:
                savings = baseline_cost - actual_cost
                savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

                print(f"  Actual cost:         ${actual_cost:.2f}")
                print(f"  Premium-only cost:   ${baseline_cost:.2f} (estimated)")
                print(f"  Savings:             ${savings:.2f}")
                print(f"  Savings percentage:  {savings_pct:.1f}%")
            else:
                print(f"  Total cost:          ${actual_cost:.2f}")
                print(f"  Total tokens:        {total_tokens:,}")
                print("\n  Note: No savings detected (may already be optimized)")

            print("\n  * Premium baseline assumes Claude Opus pricing (~$45/1M tokens)")
        else:
            print("  No telemetry data found.")

        print("-" * 60)
        return 0

    except ImportError:
        print("❌ Telemetry module not available")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Telemetry error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_export(args: Namespace) -> int:
    """Export telemetry data to file."""
    from attune.security.path_validation import _validate_file_path

    try:
        from attune.models.telemetry import TelemetryStore

        store = TelemetryStore()
        records = store.get_workflows(limit=10000)

        # Convert to exportable format
        data = [
            {
                "run_id": r.run_id,
                "workflow_name": r.workflow_name,
                "timestamp": r.started_at,
                "total_cost": r.total_cost,
                "input_tokens": r.total_input_tokens,
                "output_tokens": r.total_output_tokens,
                "success": r.success,
            }
            for r in records
        ]

        # Validate output path
        output_path = _validate_file_path(args.output)

        if args.format == "csv":
            import csv

            with output_path.open("w", newline="", encoding="utf-8") as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            print(f"✅ Exported {len(data)} entries to {output_path}")

        elif args.format == "json":
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✅ Exported {len(data)} entries to {output_path}")

        return 0

    except ImportError:
        print("❌ Telemetry module not available")
        return 1
    except ValueError as e:
        print(f"❌ Invalid path: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Export error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_routing_stats(args: Namespace) -> int:
    """Show adaptive routing statistics."""
    try:
        from attune.models import AdaptiveModelRouter
        from attune.telemetry import UsageTracker

        tracker = UsageTracker.get_instance()
        router = AdaptiveModelRouter(telemetry=tracker)

        workflow = getattr(args, "workflow", None)
        stage = getattr(args, "stage", None)
        days = getattr(args, "days", 7)

        print("\n📊 Adaptive Routing Statistics\n")
        print("-" * 70)

        if workflow:
            # Show stats for specific workflow
            stats = router.get_routing_stats(workflow=workflow, stage=stage, days=days)

            if stats["total_calls"] == 0:
                print(f"\n  No data found for workflow: {workflow}")
                if stage:
                    print(f"  Stage: {stage}")
                return 0

            print(f"\n  Workflow:      {stats['workflow']}")
            if stage:
                print(f"  Stage:         {stage}")
            print(f"  Period:        Last {days} days")
            print(f"  Total calls:   {stats['total_calls']}")
            print(f"  Avg cost:      ${stats['avg_cost']:.4f}")
            print(f"  Success rate:  {stats['avg_success_rate']:.1%}")

            print(f"\n  Models used:   {', '.join(stats['models_used'])}")

            if stats["performance_by_model"]:
                print("\n  Per-Model Performance:")
                for model, perf in sorted(
                    stats["performance_by_model"].items(),
                    key=lambda x: x[1]["quality_score"],
                    reverse=True,
                ):
                    print(f"\n    {model}:")
                    print(f"      Calls:         {perf['calls']}")
                    print(f"      Success rate:  {perf['success_rate']:.1%}")
                    print(f"      Avg cost:      ${perf['avg_cost']:.4f}")
                    print(f"      Avg latency:   {perf['avg_latency_ms']:.0f}ms")
                    print(f"      Quality score: {perf['quality_score']:.2f}")

        else:
            # Show overall statistics
            stats = tracker.get_stats(days=days)

            if stats["total_calls"] == 0:
                print("\n  No telemetry data found.")
                return 0

            print(f"\n  Period:          Last {days} days")
            print(f"  Total calls:     {stats['total_calls']:,}")
            print(f"  Total cost:      ${stats['total_cost']:.2f}")
            print(f"  Cache hit rate:  {stats['cache_hit_rate']:.1f}%")

            print("\n  Cost by Tier:")
            for tier, cost in sorted(stats["by_tier"].items(), key=lambda x: x[1], reverse=True):
                pct = (cost / stats["total_cost"] * 100) if stats["total_cost"] > 0 else 0
                print(f"    {tier:8s}: ${cost:6.2f} ({pct:5.1f}%)")

            print("\n  Top Workflows:")
            for workflow_name, cost in list(stats["by_workflow"].items())[:5]:
                pct = (cost / stats["total_cost"] * 100) if stats["total_cost"] > 0 else 0
                print(f"    {workflow_name:30s}: ${cost:6.2f} ({pct:5.1f}%)")

        print("\n" + "-" * 70)
        return 0

    except ImportError as e:
        print(f"❌ Adaptive routing not available: {e}")
        print("   Ensure attune-ai is installed with telemetry support")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Routing stats error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_routing_check(args: Namespace) -> int:
    """Check for tier upgrade recommendations."""
    try:
        from attune.models import AdaptiveModelRouter
        from attune.telemetry import UsageTracker

        tracker = UsageTracker.get_instance()
        router = AdaptiveModelRouter(telemetry=tracker)

        workflow = getattr(args, "workflow", None)
        check_all = getattr(args, "all", False)

        print("\n🔍 Adaptive Routing Tier Upgrade Checks\n")
        print("-" * 70)

        if check_all:
            # Check all workflows
            stats = tracker.get_stats(days=7)
            workflows = list(stats["by_workflow"].keys())

            if not workflows:
                print("\n  No workflow data found.")
                return 0

            recommendations = []

            for wf_name in workflows:
                try:
                    should_upgrade, reason = router.recommend_tier_upgrade(
                        workflow=wf_name,
                        stage=None,
                    )

                    if should_upgrade:
                        recommendations.append(
                            {
                                "workflow": wf_name,
                                "reason": reason,
                            },
                        )
                except Exception:  # noqa: BLE001
                    # INTENTIONAL: Skip workflows without enough data
                    continue

            if recommendations:
                print("\n  ⚠️  Tier Upgrade Recommendations:\n")
                for rec in recommendations:
                    print(f"    Workflow: {rec['workflow']}")
                    print(f"    Reason:   {rec['reason']}")
                    print()
            else:
                print("\n  ✅ All workflows performing well - no upgrades needed.\n")

        elif workflow:
            # Check specific workflow
            should_upgrade, reason = router.recommend_tier_upgrade(workflow=workflow, stage=None)

            print(f"\n  Workflow: {workflow}")

            if should_upgrade:
                print("  Status:   ⚠️  UPGRADE RECOMMENDED")
                print(f"  Reason:   {reason}")
                print("\n  Action: Consider upgrading from CHEAP → CAPABLE or CAPABLE → PREMIUM")
            else:
                print("  Status:   ✅ Performing well")
                print(f"  Reason:   {reason}")

        else:
            print("\n  Error: Specify --workflow <name> or --all")
            return 1

        print("\n" + "-" * 70)
        return 0

    except ImportError as e:
        print(f"❌ Adaptive routing not available: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Routing check error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_models(args: Namespace) -> int:
    """Show model performance by provider."""
    try:
        from attune.telemetry import UsageTracker

        tracker = UsageTracker.get_instance()
        provider = getattr(args, "provider", None)
        days = getattr(args, "days", 7)

        stats = tracker.get_stats(days=days)

        if stats["total_calls"] == 0:
            print("\n  No telemetry data found.")
            return 0

        print("\n📊 Model Performance\n")
        print("-" * 70)
        print(f"\n  Period: Last {days} days")

        # Get entries for analysis
        entries = tracker.get_recent_entries(limit=10000, days=days)

        # Group by provider and model
        model_stats: dict[str, dict[str, dict]] = {}

        for entry in entries:
            entry_provider = entry.get("provider", "unknown")
            if provider and entry_provider != provider:
                continue

            model = entry.get("model", "unknown")
            cost = entry.get("cost", 0.0)
            success = entry.get("success", True)
            duration = entry.get("duration_ms", 0)

            if entry_provider not in model_stats:
                model_stats[entry_provider] = {}

            if model not in model_stats[entry_provider]:
                model_stats[entry_provider][model] = {
                    "calls": 0,
                    "total_cost": 0.0,
                    "successes": 0,
                    "total_duration": 0,
                }

            model_stats[entry_provider][model]["calls"] += 1
            model_stats[entry_provider][model]["total_cost"] += cost
            if success:
                model_stats[entry_provider][model]["successes"] += 1
            model_stats[entry_provider][model]["total_duration"] += duration

        # Display by provider
        for prov, models in sorted(model_stats.items()):
            print(f"\n  Provider: {prov.upper()}")

            for model_name, mstats in sorted(
                models.items(),
                key=lambda x: x[1]["total_cost"],
                reverse=True,
            ):
                calls = mstats["calls"]
                avg_cost = mstats["total_cost"] / calls if calls > 0 else 0
                success_rate = (mstats["successes"] / calls * 100) if calls > 0 else 0
                avg_duration = mstats["total_duration"] / calls if calls > 0 else 0

                print(f"\n    {model_name}:")
                print(f"      Calls:        {calls:,}")
                print(f"      Total cost:   ${mstats['total_cost']:.2f}")
                print(f"      Avg cost:     ${avg_cost:.4f}")
                print(f"      Success rate: {success_rate:.1f}%")
                print(f"      Avg duration: {avg_duration:.0f}ms")

        print("\n" + "-" * 70)
        return 0

    except ImportError as e:
        print(f"❌ Telemetry not available: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Models error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_agents(args: Namespace) -> int:
    """Show active agents and their status."""
    try:
        from attune.telemetry import HeartbeatCoordinator

        coordinator = HeartbeatCoordinator()
        active_agents = coordinator.get_active_agents()

        print("\n🤖 Active Agents\n")
        print("-" * 70)

        if not active_agents:
            print("\n  No active agents found.")
            print("  (Agents must use HeartbeatCoordinator to be tracked)")
            return 0

        print(f"\n  Found {len(active_agents)} active agent(s):\n")

        for agent in sorted(active_agents, key=lambda a: a.last_beat, reverse=True):
            # Calculate time since last beat
            # Ensure both datetimes are UTC-aware for comparison
            now = datetime.now(timezone.utc)
            last_beat = (
                agent.last_beat
                if agent.last_beat.tzinfo
                else agent.last_beat.replace(tzinfo=timezone.utc)
            )
            time_since = (now - last_beat).total_seconds()

            # Status indicator
            if agent.status in ("completed", "failed", "cancelled"):
                status_icon = "✅" if agent.status == "completed" else "❌"
            elif time_since > 30:
                status_icon = "⚠️"  # Stale
            else:
                status_icon = "🟢"  # Active

            print(f"  {status_icon} {agent.agent_id}")
            print(f"      Status:       {agent.status}")
            print(f"      Progress:     {agent.progress*100:.1f}%")
            print(f"      Task:         {agent.current_task}")
            print(f"      Last beat:    {time_since:.1f}s ago")

            # Show metadata if present
            if agent.metadata:
                workflow = agent.metadata.get("workflow", "")
                if workflow:
                    print(f"      Workflow:     {workflow}")
            print()

        print("-" * 70)
        return 0

    except ImportError as e:
        print(f"❌ Agent tracking not available: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Agents error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_signals(args: Namespace) -> int:
    """Show coordination signals."""
    try:
        from attune.telemetry import CoordinationSignals

        agent_id = getattr(args, "agent", None)

        if not agent_id:
            print("❌ Error: --agent <id> required to view signals")
            return 1

        coordinator = CoordinationSignals(agent_id=agent_id)
        signals = coordinator.get_pending_signals()

        print(f"\n📡 Coordination Signals for {agent_id}\n")
        print("-" * 70)

        if not signals:
            print("\n  No pending signals.")
            return 0

        print(f"\n  Found {len(signals)} pending signal(s):\n")

        for signal in sorted(signals, key=lambda s: s.timestamp, reverse=True):
            # Calculate age
            now = datetime.now(timezone.utc)
            ts = (
                signal.timestamp
                if signal.timestamp.tzinfo
                else signal.timestamp.replace(tzinfo=timezone.utc)
            )
            age = (now - ts).total_seconds()

            # Signal type indicator
            type_icons = {
                "task_complete": "✅",
                "abort": "🛑",
                "ready": "🟢",
                "checkpoint": "🔄",
                "error": "❌",
            }
            icon = type_icons.get(signal.signal_type, "📨")

            print(f"  {icon} {signal.signal_type}")
            print(f"      From:         {signal.source_agent}")
            print(f"      Target:       {signal.target_agent or '* (broadcast)'}")
            print(f"      Age:          {age:.1f}s")
            print(f"      Expires in:   {signal.ttl_seconds - age:.1f}s")

            # Show payload summary
            if signal.payload:
                payload_str = str(signal.payload)
                if len(payload_str) > 60:
                    payload_str = payload_str[:57] + "..."
                print(f"      Payload:      {payload_str}")
            print()

        print("-" * 70)
        return 0

    except ImportError as e:
        print(f"❌ Coordination signals not available: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Signals error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_status(args: Namespace) -> int:
    """Show opt-in usage-ping status and the exact payload that is sent."""
    try:
        from attune.config.loader import ConfigLoader
        from attune.telemetry import usage_ping

        config = ConfigLoader().load()
        tele = config.telemetry
        enabled = usage_ping.is_enabled(tele.usage_ping)
        endpoint = usage_ping.resolve_endpoint() or "(not configured — Phase 2b)"

        print("\n📡 Usage Ping (anonymous, opt-in)\n")
        print("-" * 60)
        print(f"  Enabled:        {'yes' if enabled else 'no'}")
        print(f"  Config flag:    {tele.usage_ping}")
        print(f"  Consented:      {tele.usage_ping_consented}")
        print(f"  Install ID:     {tele.install_id or '(none — minted on opt-in)'}")
        print(f"  Endpoint:       {endpoint}")
        print("-" * 60)
        print("  Exactly this is sent per workflow run (nothing else):\n")
        print(json.dumps(usage_ping.example_payload(config), indent=2))
        print("-" * 60)
        print("  Enable:  attune telemetry enable")
        print("  Disable: attune telemetry disable")
        print("  DO_NOT_TRACK / ATTUNE_USAGE_PING env vars override this.\n")
        return 0
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Usage-ping status error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_enable(args: Namespace) -> int:
    """Opt in to anonymous usage pinging."""
    try:
        from attune.telemetry import usage_ping

        install_id = usage_ping.enable()
        print("\n✅ Usage ping enabled. Thank you — this helps prioritize work.")
        print(f"   Anonymous install ID: {install_id}")
        print("   Only the workflow name, version, OS, and Python version are sent.")
        print("   Never code, paths, prompts, or arguments.")
        print("   Opt out anytime: attune telemetry disable\n")
        return 0
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Usage-ping enable error: %s", e)
        print(f"❌ Error: {e}")
        return 1


def cmd_telemetry_disable(args: Namespace) -> int:
    """Opt out of anonymous usage pinging."""
    try:
        from attune.telemetry import usage_ping

        usage_ping.disable()
        print("\n✅ Usage ping disabled. Nothing will be transmitted.\n")
        return 0
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception("Usage-ping disable error: %s", e)
        print(f"❌ Error: {e}")
        return 1
