"""Performance Audit Patterns and Constants

Constants, anti-pattern definitions, and step configurations
for the performance audit workflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .step_config import WorkflowStepConfig

# Define step configurations for executor-based execution
PERF_AUDIT_STEPS = {
    "optimize": WorkflowStepConfig(
        name="optimize",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Generate performance optimization recommendations",
        max_tokens=3000,
    ),
}

# Performance anti-patterns to detect
PERF_PATTERNS = {
    "n_plus_one": {
        "patterns": [
            r"for\s+\w+\s+in\s+\w+:.*?\.get\(",
            r"for\s+\w+\s+in\s+\w+:.*?\.query\(",
            r"for\s+\w+\s+in\s+\w+:.*?\.fetch\(",
        ],
        "description": "Potential N+1 query pattern",
        "impact": "high",
    },
    "sync_in_async": {
        "patterns": [
            r"async\s+def.*?time\.sleep\(",
            r"async\s+def.*?requests\.get\(",
            r"async\s+def.*?open\([^)]+\)\.read\(",
        ],
        "description": "Synchronous operation in async context",
        "impact": "high",
    },
    "list_comprehension_in_loop": {
        "patterns": [
            r"for\s+\w+\s+in\s+\[.*for.*\]:",
        ],
        "description": "List comprehension recreated in loop",
        "impact": "medium",
    },
    "string_concat_loop": {
        "patterns": [
            # Match: for x in y: \n    str += "..." (actual loop,
            # not generator expression)
            # Exclude: any(... for x in ...) by requiring
            # standalone for statement
            r'^[ \t]*for\s+\w+\s+in\s+[^:]+:\s*\n[ \t]+\w+\s*\+=\s*["\']',
        ],
        "description": "String concatenation in loop (use join)",
        "impact": "medium",
    },
    "global_import": {
        "patterns": [
            r"^from\s+\w+\s+import\s+\*",
        ],
        "description": "Wildcard import may slow startup",
        "impact": "low",
    },
    # REMOVED: large_list_copy - too many false positives
    # - list(x) is often intentional defensive copying or
    #   type conversion
    # - dirs[:] is REQUIRED for os.walk directory filtering
    #   (see os-walk-dirs-pattern.md)
    # - Low impact even when not intentional
    # See: .claude/rules/attune/list-copy-guidelines.md
    "repeated_regex": {
        "patterns": [
            r're\.(search|match|findall)\s*\(["\'][^"\']+["\']',
        ],
        "description": "Regex pattern not pre-compiled",
        "impact": "medium",
    },
    "nested_loops": {
        "patterns": [
            r"for\s+\w+\s+in\s+\w+:\s*\n\s+for\s+\w+\s+in\s+\w+:\s*\n\s+for",
        ],
        "description": "Triple nested loop (O(n^3) complexity)",
        "impact": "high",
    },
}

# Known false positives - patterns that match but aren't
# performance issues. These are documented for transparency;
# the regex-based detection has limitations.
#
# IMPROVED: string_concat_loop
#   - Pattern now requires line to START with 'for'
#     (excludes generator expressions)
#   - Previously matched: any(x for x in y) followed by
#     += on next line
#   - Now correctly excludes: generator expressions inside
#     any(), all(), etc.
#   - Sequential string building (code += "line1";
#     code += "line2") correctly ignored
#
# REMOVED: large_list_copy (v2.1.0)
#   - list(x) or x[:] used for defensive copying or
#     type conversion
#   - dirs[:] is REQUIRED for os.walk directory filtering
#   - Often intentional to avoid mutating original data
#   - Verdict: REMOVED - too many false positives, low
#     impact even when real
#   - See: .claude/rules/attune/list-copy-guidelines.md
#   - See: .claude/rules/attune/os-walk-dirs-pattern.md
#
# FALSE POSITIVE: repeated_regex (edge cases)
#   - Single-use regex in rarely-called functions
#   - Verdict: OK - pre-compilation only matters for
#     hot paths

# Optimization action definitions for each concern type
OPTIMIZATION_ACTIONS: dict[str, dict[str, str]] = {
    "n_plus_one": {
        "action": "Batch database queries",
        "description": ("Use prefetch_related/select_related or batch queries"),
        "estimated_impact": "high",
    },
    "sync_in_async": {
        "action": "Use async alternatives",
        "description": ("Replace sync operations with async versions"),
        "estimated_impact": "high",
    },
    "string_concat_loop": {
        "action": "Use str.join()",
        "description": ("Build list of strings and join at the end instead of concatenating"),
        "estimated_impact": "medium",
    },
    "repeated_regex": {
        "action": "Pre-compile regex",
        "description": ("Use re.compile() and reuse the compiled pattern"),
        "estimated_impact": "medium",
    },
    "nested_loops": {
        "action": "Optimize algorithm",
        "description": ("Consider using sets, dicts, or itertools to reduce complexity"),
        "estimated_impact": "high",
    },
    "list_comprehension_in_loop": {
        "action": "Move comprehension outside loop",
        "description": "Create the list once before the loop",
        "estimated_impact": "medium",
    },
    # large_list_copy removed - too many false positives
    "global_import": {
        "action": "Use specific imports",
        "description": ("Import only needed names to reduce memory and startup time"),
        "estimated_impact": "low",
    },
}
