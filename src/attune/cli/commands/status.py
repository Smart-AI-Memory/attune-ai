"""Status and health check commands for the CLI.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio


def cmd_status(args):
    """Session status assistant - prioritized project status report.

    Collects and displays project status including patterns, git context,
    and health metrics with priority scoring.

    Args:
        args: Namespace object from argparse with attributes:
            - patterns_dir (str): Path to patterns directory (default: ./patterns).
            - project_root (str): Project root directory (default: .).
            - inactivity (int): Minutes of inactivity before showing status.
            - full (bool): If True, show all items without limit.
            - json (bool): If True, output as JSON format.
            - select (int | None): Select specific item for action prompt.
            - force (bool): If True, show status even with recent activity.

    Returns:
        None: Prints prioritized status report or JSON output.
    """
    from attune_llm.session_status import SessionStatusCollector

    config = {"inactivity_minutes": args.inactivity}
    collector = SessionStatusCollector(
        patterns_dir=args.patterns_dir,
        project_root=args.project_root,
        config=config,
    )

    # Check if should show (unless forced)
    if not args.force and not collector.should_show():
        print("No status update needed (recent activity detected).")
        print("Use --force to show status anyway.")
        return

    # Collect status
    status = collector.collect()

    # Handle selection
    if args.select:
        prompt = collector.get_action_prompt(status, args.select)
        if prompt:
            print(f"\nAction prompt for selection {args.select}:\n")
            print(prompt)
        else:
            print(f"Invalid selection: {args.select}")
        return

    # Output
    if args.json:
        print(collector.format_json(status))
    else:
        max_items = None if args.full else 5
        print()
        print(collector.format_output(status, max_items=max_items))
        print()

    # Record interaction
    collector.record_interaction()


def cmd_review(args):
    """Pattern-based code review against historical bugs.

    Note: This command has been deprecated. The underlying workflow module
    has been removed. Use 'attune workflow run bug-predict' instead.

    Args:
        args: Namespace object from argparse.

    Returns:
        None: Prints deprecation message.
    """
    print("⚠️  The 'review' command has been deprecated.")
    print()
    print("The CodeReviewWorkflow module has been removed.")
    print("Please use one of these alternatives:")
    print()
    print("  attune workflow run bug-predict    # Scan for risky patterns")
    print("  ruff check <files>                  # Fast linting")
    print("  bandit -r <path>                    # Security scanning")
    print()


def cmd_health(args):
    """Code health assistant - run health checks and auto-fix issues.

    Runs comprehensive health checks including linting, type checking,
    and formatting with optional auto-fix capability.

    Args:
        args: Namespace object from argparse with attributes:
            - check (str | None): Specific check to run (lint/type/format/test).
            - deep (bool): If True, run comprehensive checks.
            - fix (bool): If True, auto-fix issues where possible.
            - threshold (str): Severity threshold for issues.
            - project_root (str): Project root directory.
            - patterns_dir (str): Path to patterns directory.
            - details (bool): If True, show detailed issue list.
            - compare (str | None): Compare against historical baseline.
            - export (str | None): Export results to file.
            - json (bool): If True, output as JSON format.

    Returns:
        None: Prints health check results and optionally fixes issues.
    """
    from attune_llm.code_health import (
        AutoFixer,
        CheckCategory,
        HealthCheckRunner,
        HealthTrendTracker,
        format_health_output,
    )

    runner = HealthCheckRunner(
        project_root=args.project_root,
    )

    # Determine what checks to run
    if args.check:
        # Run specific check
        try:
            category = CheckCategory(args.check)
            report_future = runner.run_check(category)
            result = asyncio.run(report_future)
            # Create a minimal report with just this result
            from attune_llm.code_health import HealthReport

            report = HealthReport(project_root=args.project_root)
            report.add_result(result)
        except ValueError:
            print(f"Unknown check category: {args.check}")
            print(f"Available: {', '.join(c.value for c in CheckCategory)}")
            return
    elif args.deep:
        # Run all checks
        print("Running comprehensive health check...\n")
        report = asyncio.run(runner.run_all())
    else:
        # Run quick checks (default)
        report = asyncio.run(runner.run_quick())

    # Handle fix mode
    if args.fix:
        fixer = AutoFixer()

        if args.dry_run:
            # Preview only
            fixes = fixer.preview_fixes(report)
            if fixes:
                print("Would fix the following issues:\n")
                for fix in fixes:
                    safe_indicator = " (safe)" if fix["safe"] else " (needs confirmation)"
                    print(f"  [{fix['category']}] {fix['file']}")
                    print(f"    {fix['issue']}")
                    print(f"    Command: {fix['fix_command']}{safe_indicator}")
                    print()
            else:
                print("No auto-fixable issues found.")
            return

        # Apply fixes
        if args.check:
            try:
                category = CheckCategory(args.check)
                result = asyncio.run(fixer.fix_category(report, category))
            except ValueError:
                result = {"fixed": [], "skipped": [], "failed": []}
        else:
            result = asyncio.run(fixer.fix_all(report, interactive=args.interactive))

        # Report fix results
        if result["fixed"]:
            print(f"✓ Fixed {len(result['fixed'])} issue(s)")
            for fix in result["fixed"][:5]:
                print(f"  - {fix['file_path']}: {fix['message']}")
            if len(result["fixed"]) > 5:
                print(f"  ... and {len(result['fixed']) - 5} more")

        if result["skipped"]:
            if args.interactive:
                print(f"\n⚠ Skipped {len(result['skipped'])} issue(s) (could not auto-fix)")
            else:
                print(
                    f"\n⚠ Skipped {len(result['skipped'])} issue(s) (use --interactive to review)",
                )

        if result["failed"]:
            print(f"\n✗ Failed to fix {len(result['failed'])} issue(s)")

        return

    # Handle trends
    if args.trends:
        tracker = HealthTrendTracker(project_root=args.project_root)
        trends = tracker.get_trends(days=args.trends)

        print(f"📈 Health Trends ({trends['period_days']} days)\n")
        print(f"Average Score: {trends['average_score']}/100")
        print(f"Trend: {trends['trend_direction']} ({trends['score_change']:+d})")

        if trends["data_points"]:
            print("\nRecent scores:")
            for point in trends["data_points"][:7]:
                print(f"  {point['date']}: {point['score']}/100")

        hotspots = tracker.identify_hotspots()
        if hotspots:
            print("\n🔥 Hotspots (files with recurring issues):")
            for spot in hotspots[:5]:
                print(f"  {spot['file']}: {spot['issue_count']} issues")

        return

    # Output report
    if args.json:
        import json

        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        level = 3 if args.full else (2 if args.details else 1)
        print(format_health_output(report, level=level))

    # Record to trend history
    if not args.check:  # Only record full runs
        tracker = HealthTrendTracker(project_root=args.project_root)
        tracker.record_check(report)
