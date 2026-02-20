"""Socratic Router Patterns - Intent detection keyword patterns.

Contains the INTENT_PATTERNS dictionary that maps IntentCategory
values to their keyword lists and workflow options.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

from attune.socratic_router_models import IntentCategory, WorkflowOption

# Intent detection patterns
INTENT_PATTERNS: dict[IntentCategory, dict[str, Any]] = {
    IntentCategory.FIX: {
        "keywords": [
            "fix",
            "bug",
            "error",
            "broken",
            "crash",
            "fail",
            "issue",
            "problem",
            "debug",
            "wrong",
            "doesn't work",
            "not working",
            "exception",
            "traceback",
        ],
        "question": "What kind of issue are you dealing with?",
        "options": [
            WorkflowOption(
                label="Debug an error",
                description="Investigate exceptions, trace execution, find root cause",
                skill="dev",
                args="debug",
            ),
            WorkflowOption(
                label="Fix failing tests",
                description="Analyze test failures and fix the underlying code",
                skill="testing",
                args="run",
            ),
            WorkflowOption(
                label="Review for bugs",
                description="Code review focused on finding potential bugs",
                skill="dev",
                args="review",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe your specific issue",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.IMPROVE: {
        "keywords": [
            "refactor",
            "improve",
            "clean",
            "optimize",
            "simplify",
            "better",
            "performance",
            "speed",
            "faster",
            "memory",
            "too long",
            "complex",
            "messy",
            "ugly",
        ],
        "question": "What would you like to improve?",
        "options": [
            WorkflowOption(
                label="Refactor code",
                description="Improve structure, extract functions, simplify logic",
                skill="dev",
                args="refactor",
            ),
            WorkflowOption(
                label="Optimize performance",
                description="Find bottlenecks, improve speed and memory usage",
                skill="workflows",
                args="run perf-audit",
            ),
            WorkflowOption(
                label="Code review",
                description="Get feedback on code quality and patterns",
                skill="dev",
                args="review",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe what you want to improve",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.VALIDATE: {
        "keywords": [
            "test",
            "coverage",
            "security",
            "audit",
            "check",
            "verify",
            "validate",
            "review",
            "safe",
            "secure",
            "vulnerability",
        ],
        "question": "What would you like to validate?",
        "options": [
            WorkflowOption(
                label="Run tests",
                description="Execute test suite and see results",
                skill="testing",
                args="run",
            ),
            WorkflowOption(
                label="Check coverage",
                description="Analyze test coverage and identify gaps",
                skill="testing",
                args="coverage",
            ),
            WorkflowOption(
                label="Security audit",
                description="Scan for vulnerabilities and security issues",
                skill="workflows",
                args="run security-audit",
            ),
            WorkflowOption(
                label="Code review",
                description="Quality and pattern analysis",
                skill="dev",
                args="review",
            ),
        ],
    },
    IntentCategory.SHIP: {
        "keywords": [
            "commit",
            "push",
            "pr",
            "pull request",
            "merge",
            "release",
            "deploy",
            "ship",
            "publish",
            "done",
            "ready",
            "finished",
        ],
        "question": "What stage are you at?",
        "options": [
            WorkflowOption(
                label="Create commit",
                description="Stage changes and create a commit with message",
                skill="dev",
                args="commit",
            ),
            WorkflowOption(
                label="Create PR",
                description="Push branch and create pull request",
                skill="dev",
                args="pr",
            ),
            WorkflowOption(
                label="Prepare release",
                description="Version bump, changelog, security checks",
                skill="release",
                args="prep",
            ),
            WorkflowOption(
                label="Just push",
                description="Push current commits to remote",
                skill="dev",
                args="push",
            ),
        ],
    },
    IntentCategory.UNDERSTAND: {
        "keywords": [
            "explain",
            "understand",
            "how",
            "what",
            "why",
            "document",
            "docs",
            "readme",
            "learn",
            "show",
            "describe",
            "overview",
        ],
        "question": "What would you like to understand?",
        "options": [
            WorkflowOption(
                label="Explain code",
                description="Understand how specific code works",
                skill="docs",
                args="explain",
            ),
            WorkflowOption(
                label="Project overview",
                description="High-level architecture and structure",
                skill="docs",
                args="overview",
            ),
            WorkflowOption(
                label="Generate docs",
                description="Create or update documentation",
                skill="docs",
                args="generate",
            ),
            WorkflowOption(
                label="Something specific",
                description="Ask about a specific part of the codebase",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.CREATE: {
        "keywords": [
            "create",
            "build",
            "new",
            "define",
            "custom",
            "wizard",
            "agent",
            "team",
            "scaffold",
            "generate agent",
            "make a",
            "set up",
        ],
        "question": "What would you like to create?",
        "options": [
            WorkflowOption(
                label="Create a wizard",
                description="Define a new custom guided workflow (YAML-based)",
                skill="wizard",
                args="create",
            ),
            WorkflowOption(
                label="Create an agent",
                description="Define a new specialized AI agent with role and tools",
                skill="agent",
                args="create",
            ),
            WorkflowOption(
                label="Create an agent team",
                description="Build a multi-agent collaboration pipeline",
                skill="agent",
                args="create-team",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe what you want to create",
                skill="attune",
                args="",
            ),
        ],
    },
}
