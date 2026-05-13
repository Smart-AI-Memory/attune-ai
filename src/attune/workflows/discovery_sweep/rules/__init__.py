"""Rule registry for the discovery-sweep verification engine."""

from __future__ import annotations

from ..verification import VerificationRule
from .known_false_positives import (
    DirsSliceAssignmentRule,
    IntentionalBroadExceptRule,
    JsRegexExecRule,
    SecretsPragmaRule,
    StructlogKwargsRule,
    SubprocessExecRule,
    SubprocessInFuzzTargetRule,
    WriteTextEvalFixtureRule,
)


def default_rules() -> list[VerificationRule]:
    """Return the ordered default rule list for the engine.

    REJECT rules come first. Phase 1 ships with no ACCEPT rules —
    everything that survives the denylist falls through to UNSURE
    and lands in the questions file for human review.

    Rule order is significant: rules with stricter guards run
    before rules with broader matchers so the more-precise rule
    wins.
    """
    return [
        DirsSliceAssignmentRule(),
        JsRegexExecRule(),
        WriteTextEvalFixtureRule(),
        SubprocessExecRule(),
        SubprocessInFuzzTargetRule(),
        IntentionalBroadExceptRule(),
        StructlogKwargsRule(),
        SecretsPragmaRule(),
    ]


__all__ = [
    "DirsSliceAssignmentRule",
    "IntentionalBroadExceptRule",
    "JsRegexExecRule",
    "SecretsPragmaRule",
    "StructlogKwargsRule",
    "SubprocessExecRule",
    "SubprocessInFuzzTargetRule",
    "WriteTextEvalFixtureRule",
    "default_rules",
]
