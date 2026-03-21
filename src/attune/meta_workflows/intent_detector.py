"""Intent detection for automatic agent team creation.

Analyzes user requests and suggests appropriate meta-workflow templates.

Created: 2026-01-18
Purpose: Enable natural discovery of agent teams based on user intent
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from attune.meta_workflows.builtin_templates import BUILTIN_TEMPLATES

logger = logging.getLogger(__name__)


@dataclass
class IntentMatch:
    """A detected intent match with confidence score.

    Attributes:
        template_id: ID of matching template
        template_name: Human-readable name
        confidence: Match confidence (0.0 to 1.0)
        matched_keywords: Keywords that triggered the match
        description: What this template does
        cli_fallback: CLI command to run when no template exists

    """

    template_id: str
    template_name: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    description: str = ""
    cli_fallback: str = ""


# Intent patterns for each template
INTENT_PATTERNS = {
    "release-prep": {
        "keywords": [
            "release",
            "deploy",
            "publish",
            "ship",
            "launch",
            "ready",
            "readiness",
            "checklist",
            "preparation",
            "security scan",
            "vulnerability",
            "audit",
            "production",
            "go live",
            "version bump",
            "pre-release",
            "before release",
            "quality check",
            "code review",
            "final check",
        ],
        "phrases": [
            r"ready (for|to) (release|deploy|publish)",
            r"(check|verify|validate) (for )?release",
            r"(prepare|preparing) (for )?(a )?(release|deployment)",
            r"security (scan|check|audit)",
            r"(is|are) (we|it) ready",
            r"release (check|prep|preparation)",
            r"prepare for (a )?release",
            r"need to release",
            r"before (we )?(release|deploy|publish|ship|launch)",
            r"quality (check|audit|review)",
            r"ready to (ship|deploy|launch|publish)",
        ],
        "weight": 1.0,
    },
    "test-coverage-boost": {
        "keywords": [
            "test coverage",
            "coverage",
            "tests",
            "testing",
            "unit tests",
            "improve coverage",
            "boost coverage",
            "generate tests",
            "missing tests",
            "coverage gap",
            "80%",
            "90%",
            "percent coverage",
            "more tests",
            "add tests",
            "write tests",
            "create tests",
            "batch tests",
            "batch generation",
            "parallel tests",
            "bulk tests",
            "mass test generation",
            "rapidly generate",
            "quickly boost",
        ],
        "phrases": [
            r"(improve|increase|boost) (test )?coverage",
            r"(generate|create|write|add) (more )?tests",
            r"coverage (is )?(too )?low",
            r"(find|identify) (coverage )?gaps",
            r"(need|want) more tests",
            r"test generation",
            r"my (test )?coverage",
            r"improve.*coverage",
            r"(batch|bulk|mass) (test )?generation",
            r"generate tests (in )?(batch|parallel)",
            r"(rapidly|quickly) (generate|boost|improve)",
            r"parallel test (generation|creation)",
        ],
        "weight": 1.0,
    },
    "test-maintenance": {
        "keywords": [
            "test maintenance",
            "stale tests",
            "outdated tests",
            "flaky tests",
            "test health",
            "test cleanup",
            "test lifecycle",
            "maintain tests",
            "fix tests",
            "broken tests",
            "failing tests",
        ],
        "phrases": [
            r"(fix|update|maintain) tests",
            r"(stale|outdated|old) tests",
            r"test (maintenance|health|cleanup)",
            r"tests (are )?(failing|flaky|broken)",
            r"clean up tests",
            r"test.*broken",
            r"failing test",
        ],
        "weight": 1.0,
    },
    "manage-docs": {
        "keywords": [
            "documentation",
            "docs",
            "docstrings",
            "readme",
            "api docs",
            "missing docs",
            "update docs",
            "document",
            "documenting",
            "undocumented",
            "up to date",
            "sync",
            "stale docs",
            "outdated docs",
        ],
        "phrases": [
            r"(update|improve|fix|add) (the )?doc(s|umentation)?",
            r"missing (doc)?strings",
            r"(check|verify) documentation",
            r"(readme|api docs?) (is )?(outdated|stale|missing)",
            r"document (the )?(code|api|functions)",
            r"documentation.*(up to date|sync|current|fresh)",
            r"(is|are).*(doc|documentation).*(up to date|current|sync)",
            r"doc.*(stale|outdated|old)",
        ],
        "weight": 1.0,
    },
    "auth-strategy": {
        "keywords": [
            "authentication",
            "auth",
            "auth strategy",
            "auth mode",
            "api key",
            "subscription",
            "configure auth",
            "setup auth",
            "auth status",
            "check auth",
            "recommend auth",
            "authentication mode",
            "api mode",
            "subscription mode",
            "cost optimization",
            "auth config",
        ],
        "phrases": [
            r"(setup|configure) auth(entication)?",
            r"auth(entication)? (setup|config|status|mode)",
            r"(check|show|view) auth(entication)? (status|config|mode)",
            r"(what|which) auth(entication)? mode",
            r"recommend auth(entication)?",
            r"(api|subscription) (key|mode)",
            r"switch (to )?(api|subscription)",
            r"auth(entication)? (for|with)",
            r"reset auth(entication)?",
        ],
        "weight": 1.0,
        "cli_fallback": "uv run attune provider",
        "description": "Configure authentication and API provider settings",
    },
    "brainstorm": {
        "keywords": [
            "brainstorm",
            "think through",
            "figure out",
            "ideate",
            "explore idea",
            "new idea",
            "not sure how",
            "think about",
            "work through",
            "talk through",
            "help me think",
            "plan approach",
            "what if",
        ],
        "phrases": [
            r"(help me )?(think|figure) (through|out|about)",
            r"(let's|let me|I want to) brainstorm",
            r"(not sure|unsure) (how|what|where) to",
            r"(explore|consider|think about) (an? )?(idea|approach|option)",
            r"what if (we|I)",
            r"how should (I|we) (tackle|approach|handle|think about)",
            r"(need to|want to) (think|plan|figure)",
            r"I have an idea",
            r"(help me )?(work|talk) (through|out)",
        ],
        "weight": 1.0,
    },
}


class IntentDetector:
    """Detects user intent and suggests appropriate agent teams.

    Uses keyword matching and phrase patterns to identify what the user
    is trying to accomplish and maps it to available meta-workflow templates.
    """

    def __init__(self):
        """Initialize the intent detector."""
        self.patterns = INTENT_PATTERNS
        self.templates = BUILTIN_TEMPLATES

    def detect(self, user_input: str, threshold: float = 0.3) -> list[IntentMatch]:
        """Detect user intent from natural language input.

        Args:
            user_input: User's natural language request
            threshold: Minimum confidence score to include (default: 0.3)

        Returns:
            List of IntentMatch objects, sorted by confidence (highest first)

        """
        if not user_input or not isinstance(user_input, str):
            return []

        user_input_lower = user_input.lower().strip()
        matches = []

        for template_id, pattern_config in self.patterns.items():
            confidence, matched_keywords = self._calculate_match_score(
                user_input_lower,
                pattern_config,
            )

            if confidence >= threshold:
                template = self.templates.get(template_id)
                fallback_desc = pattern_config.get("description", "")
                matches.append(
                    IntentMatch(
                        template_id=template_id,
                        template_name=template.name if template else template_id,
                        confidence=confidence,
                        matched_keywords=matched_keywords,
                        description=template.description if template else fallback_desc,
                        cli_fallback=pattern_config.get("cli_fallback", ""),
                    ),
                )

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def _calculate_match_score(
        self,
        user_input: str,
        pattern_config: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Calculate match score for a template.

        Args:
            user_input: Lowercase user input
            pattern_config: Pattern configuration for a template

        Returns:
            Tuple of (confidence score, list of matched keywords)

        """
        keywords = pattern_config.get("keywords", [])
        phrases = pattern_config.get("phrases", [])
        weight = pattern_config.get("weight", 1.0)

        matched_keywords = []
        keyword_score = 0.0
        phrase_score = 0.0

        # Check keyword matches
        for keyword in keywords:
            if keyword.lower() in user_input:
                matched_keywords.append(keyword)
                # Longer keywords are weighted more
                keyword_score += len(keyword.split()) * 0.1

        # Check phrase matches (more specific, higher weight)
        for phrase in phrases:
            if re.search(phrase, user_input, re.IGNORECASE):
                phrase_score += 0.3
                # Extract matched text for debugging
                match = re.search(phrase, user_input, re.IGNORECASE)
                if match:
                    matched_keywords.append(f"[{match.group()}]")

        # Combine scores (cap at 1.0)
        total_score = min((keyword_score + phrase_score) * weight, 1.0)

        return total_score, matched_keywords

    def get_suggestion_text(self, matches: list[IntentMatch]) -> str:
        """Generate a user-friendly suggestion message.

        Args:
            matches: List of intent matches

        Returns:
            Formatted suggestion text

        """
        if not matches:
            return ""

        lines = ["I detected the following agent teams that might help:\n"]

        for i, match in enumerate(matches[:3], 1):  # Top 3 suggestions
            confidence_pct = int(match.confidence * 100)
            lines.append(f"  {i}. **{match.template_name}** ({confidence_pct}% match)")
            lines.append(f"     {match.description}")
            lines.append(f"     Run with: `attune workflow run {match.template_id}`")
            lines.append("")

        return "\n".join(lines)

    def should_suggest(self, user_input: str, min_confidence: float = 0.4) -> bool:
        """Check if we should suggest agent teams for this input.

        Args:
            user_input: User's input text
            min_confidence: Minimum confidence to trigger suggestion

        Returns:
            True if we should suggest agent teams

        """
        matches = self.detect(user_input, threshold=min_confidence)
        return len(matches) > 0

    def get_best_match(self, user_input: str) -> IntentMatch | None:
        """Get the best matching template for user input.

        Args:
            user_input: User's natural language request

        Returns:
            Best matching IntentMatch or None if no good match

        """
        matches = self.detect(user_input, threshold=0.4)
        return matches[0] if matches else None


def detect_and_suggest(user_input: str) -> str:
    """Convenience function to detect intent and return suggestion.

    Args:
        user_input: User's natural language request

    Returns:
        Suggestion text or empty string if no matches

    """
    detector = IntentDetector()
    matches = detector.detect(user_input)
    return detector.get_suggestion_text(matches)


def auto_detect_template(user_input: str) -> str | None:
    """Auto-detect the best template for a user request.

    Args:
        user_input: User's natural language request

    Returns:
        Template ID if confident match, None otherwise

    """
    detector = IntentDetector()
    match = detector.get_best_match(user_input)

    if match and match.confidence >= 0.6:
        logger.info(
            f"Auto-detected template: {match.template_id} (confidence: {match.confidence:.0%})",
        )
        return match.template_id

    return None
