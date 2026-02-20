"""Domain Detection for Socratic Engine

Detects user intent domain from goal text using keyword and phrase matching.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DomainPattern:
    """Pattern for detecting user intent domain."""

    domain: str
    keywords: list[str]
    phrases: list[str]
    weight: float = 1.0


DOMAIN_PATTERNS = [
    DomainPattern(
        domain="code_review",
        keywords=["review", "pr", "pull request", "merge", "diff", "changes"],
        phrases=["code review", "review code", "check my code", "review my"],
        weight=1.0,
    ),
    DomainPattern(
        domain="security",
        keywords=["security", "vulnerability", "secure", "exploit", "attack", "owasp"],
        phrases=["security audit", "find vulnerabilities", "security check", "penetration"],
        weight=1.2,
    ),
    DomainPattern(
        domain="testing",
        keywords=["test", "coverage", "unit test", "integration", "pytest", "jest"],
        phrases=["write tests", "generate tests", "test coverage", "increase coverage"],
        weight=1.0,
    ),
    DomainPattern(
        domain="documentation",
        keywords=["document", "docstring", "readme", "api docs", "comment"],
        phrases=["write documentation", "generate docs", "add docstrings"],
        weight=0.9,
    ),
    DomainPattern(
        domain="performance",
        keywords=["performance", "optimize", "speed", "slow", "memory", "efficient"],
        phrases=["improve performance", "optimize code", "make faster", "reduce memory"],
        weight=1.0,
    ),
    DomainPattern(
        domain="refactoring",
        keywords=["refactor", "clean", "restructure", "simplify", "modular"],
        phrases=["refactor code", "clean up", "improve structure"],
        weight=0.9,
    ),
]


def detect_domain(goal: str) -> tuple[str, float]:
    """Detect the domain from goal text.

    Args:
        goal: User's goal statement

    Returns:
        Tuple of (domain, confidence)
    """
    goal_lower = goal.lower()
    scores: dict[str, float] = {}

    for pattern in DOMAIN_PATTERNS:
        score = 0.0

        # Check keywords
        for keyword in pattern.keywords:
            if keyword in goal_lower:
                score += 1.0 * pattern.weight

        # Check phrases (higher weight)
        for phrase in pattern.phrases:
            if phrase in goal_lower:
                score += 2.0 * pattern.weight

        if score > 0:
            scores[pattern.domain] = score

    if not scores:
        return "general", 0.5

    best_domain = max(scores, key=lambda k: scores[k])
    max_score = scores[best_domain]

    # Normalize confidence (cap at 1.0)
    confidence = min(max_score / 5.0, 1.0)

    return best_domain, confidence


def extract_keywords(goal: str) -> list[str]:
    """Extract important keywords from goal.

    Args:
        goal: User's goal statement

    Returns:
        List of unique keywords preserving order
    """
    # Remove common words
    stop_words = {
        "i",
        "want",
        "to",
        "the",
        "a",
        "an",
        "my",
        "our",
        "for",
        "with",
        "that",
        "this",
        "is",
        "are",
        "be",
        "will",
        "would",
        "could",
        "should",
        "can",
        "help",
        "me",
        "us",
        "please",
        "need",
        "like",
    }

    # Extract words
    words = re.findall(r"\b\w+\b", goal.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Return unique keywords preserving order
    return list(dict.fromkeys(keywords))


def identify_ambiguities(goal: str, domain: str) -> list[str]:
    """Identify ambiguities in the goal that need clarification.

    Args:
        goal: User's goal statement
        domain: Detected domain

    Returns:
        List of ambiguity descriptions
    """
    ambiguities = []

    # Check for missing specifics
    if not any(
        lang in goal.lower()
        for lang in ["python", "javascript", "typescript", "java", "go", "rust"]
    ):
        ambiguities.append("Programming language not specified")

    # Check for vague scope
    vague_terms = ["some", "various", "different", "several", "multiple"]
    for term in vague_terms:
        if term in goal.lower():
            ambiguities.append(f"Vague scope indicator: '{term}'")
            break

    # Domain-specific ambiguities
    if domain == "code_review":
        if "security" not in goal.lower() and "style" not in goal.lower():
            ambiguities.append("Review focus areas not specified")

    if domain == "testing":
        if "unit" not in goal.lower() and "integration" not in goal.lower():
            ambiguities.append("Test type not specified")

    return ambiguities


def identify_assumptions(goal: str, domain: str) -> list[str]:
    """Identify assumptions we're making from the goal.

    Args:
        goal: User's goal statement
        domain: Detected domain

    Returns:
        List of assumption descriptions
    """
    assumptions = []

    # Common assumptions
    if domain == "code_review":
        assumptions.append("Assuming code is version-controlled (git)")
        assumptions.append("Assuming PR/diff-based review workflow")

    if domain == "testing":
        assumptions.append("Assuming existing test framework in project")

    if domain == "security":
        assumptions.append("Assuming standard web application security model")

    return assumptions
