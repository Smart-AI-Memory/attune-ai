"""Help text and documentation data for CLI commands.

This module contains static help content displayed by various CLI commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

CHEATSHEET = {
    "Getting Started": [
        ("attune init", "Create a new config file"),
        ("attune workflow", "Interactive setup workflow"),
        ("attune run", "Interactive REPL mode"),
    ],
    "Daily Workflow": [
        ("attune morning", "Start-of-day briefing"),
        ("attune status", "What needs attention now"),
        ("attune ship", "Pre-commit validation"),
    ],
    "Code Quality": [
        ("attune health", "Quick health check"),
        ("attune health --deep", "Comprehensive check"),
        ("attune health --fix", "Auto-fix issues"),
        ("attune fix-all", "Fix all lint/format issues"),
    ],
    "Pattern Learning": [
        ("attune learn --analyze 20", "Learn from last 20 commits"),
        ("attune sync-claude", "Sync patterns to Claude Code"),
        ("attune inspect patterns", "View learned patterns"),
    ],
    "Code Review": [
        ("attune review", "Review recent changes"),
        ("attune review --staged", "Review staged changes only"),
    ],
    "Memory & State": [
        ("attune inspect state", "View saved states"),
        ("attune inspect metrics --user-id X", "View user metrics"),
        ("attune export patterns.json", "Export patterns"),
    ],
    "Advanced": [
        ("attune costs", "View API cost tracking"),
        ("attune dashboard", "Launch visual dashboard"),
        ("Attune AIs", "List agent frameworks"),
        ("attune workflow list", "List multi-model workflows"),
        ("attune new <template>", "Create project from template"),
    ],
}

EXPLAIN_CONTENT = {
    "morning": """
HOW 'attune morning' WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
This command aggregates multiple data sources to give you a prioritized
start-of-day briefing:

1. PATTERNS ANALYSIS
   Reads ./patterns/*.json to find:
   - Unresolved bugs (status: investigating)
   - Recent security decisions
   - Tech debt trends

2. GIT CONTEXT
   Checks your recent git activity:
   - Commits from yesterday
   - Uncommitted changes
   - Branch status

3. HEALTH SNAPSHOT
   Runs quick health checks:
   - Lint issues count
   - Type errors
   - Test status

4. PRIORITY SCORING
   Items are scored and sorted by:
   - Age (older = higher priority)
   - Severity (critical > high > medium)
   - Your recent activity patterns

TIPS:
• Run this first thing each day
• Use 'attune morning --verbose' for details
• Pair with 'attune status --select N' to dive deeper
""",
    "ship": """
HOW 'attune ship' WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━
Pre-commit validation pipeline that ensures code quality before shipping:

1. HEALTH CHECKS
   - Runs lint checks (ruff/flake8)
   - Validates types (mypy/pyright)
   - Checks formatting (black/prettier)

2. PATTERN REVIEW
   - Compares changes against known bug patterns
   - Flags code that matches historical issues
   - Suggests fixes based on past resolutions

3. SECURITY SCAN
   - Checks for hardcoded secrets
   - Validates against security patterns
   - Reports potential vulnerabilities

4. PATTERN SYNC (optional)
   - Updates Claude Code rules
   - Syncs new patterns discovered
   - Skip with --skip-sync

EXIT CODES:
• 0 = All checks passed, safe to commit
• 1 = Issues found, review before committing

TIPS:
• Add to pre-commit hook: attune ship --skip-sync
• Use 'attune ship --verbose' to see all checks
""",
    "learn": """
HOW 'attune learn' WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━
Extracts patterns from your git history to teach Claude about your codebase:

1. COMMIT ANALYSIS
   Parses commit messages looking for:
   - fix: Bug fixes → debugging.json
   - security: decisions → security.json
   - TODO/FIXME in code → tech_debt.json

2. DIFF INSPECTION
   Analyzes code changes to:
   - Identify affected files
   - Extract error types
   - Record fix patterns

3. PATTERN STORAGE
   Saves to ./patterns/:
   - debugging.json: Bug patterns
   - security.json: Security decisions
   - tech_debt.json: Technical debt
   - inspection.json: Code review findings

4. SUMMARY GENERATION
   Creates .claude/patterns_summary.md:
   - Human-readable pattern overview
   - Loaded by Claude Code automatically

USAGE EXAMPLES:
• attune learn --analyze 10    # Last 10 commits
• attune learn --analyze 100   # Deeper history
• attune sync-claude           # Apply patterns to Claude

TIPS:
• Run weekly to keep patterns current
• Use good commit messages (fix:, feat:, etc.)
• Check ./patterns/ to see what was learned
""",
    "health": """
HOW 'attune health' WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━
Code health dashboard that runs multiple quality checks:

1. QUICK MODE (default)
   Fast checks that run in seconds:
   - Lint: ruff check or flake8
   - Format: black --check or prettier
   - Basic type checking

2. DEEP MODE (--deep)
   Comprehensive checks (slower):
   - Full type analysis (mypy --strict)
   - Test suite execution
   - Security scanning
   - Dependency audit

3. SCORING
   Health score 0-100 based on:
   - Lint issues (×2 penalty each)
   - Type errors (×5 penalty each)
   - Test failures (×10 penalty each)
   - Security issues (×20 penalty each)

4. AUTO-FIX (--fix)
   Can automatically fix:
   - Formatting issues
   - Import sorting
   - Simple lint errors

USAGE:
• attune health              # Quick check
• attune health --deep       # Full check
• attune health --fix        # Auto-fix issues
• attune health --trends 30  # 30-day trend

TIPS:
• Run quick checks before commits
• Run deep checks in CI/CD
• Track trends to catch regressions
""",
    "sync-claude": """
HOW 'attune sync-claude' WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Converts learned patterns into Claude Code rules:

1. READS PATTERNS
   Loads from ./patterns/:
   - debugging.json → Bug fix patterns
   - security.json → Security decisions
   - tech_debt.json → Known debt items

2. GENERATES RULES
   Creates .claude/rules/attune/:
   - debugging.md
   - security.md
   - tech_debt.md

3. CLAUDE CODE INTEGRATION
   Rules are automatically loaded when:
   - Claude Code starts in this directory
   - Combined with CLAUDE.md instructions

HOW CLAUDE USES THESE:
• Sees historical bugs before suggesting code
• Knows about accepted security patterns
• Understands existing tech debt

FILE STRUCTURE:
./patterns/             # Your pattern storage
  debugging.json
  security.json
.claude/
  CLAUDE.md             # Project instructions
  rules/
    attune/             # Generated rules
      debugging.md
      security.md

TIPS:
• Run after 'attune learn'
• Commit .claude/rules/ to share with team
• Weekly sync keeps Claude current
""",
}
