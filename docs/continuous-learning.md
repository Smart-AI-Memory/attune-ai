---
description: Continuous Learning: Extract and apply patterns from collaboration sessions for improved interactions.
---

# Continuous Learning

Extract and apply patterns from collaboration sessions for improved interactions.

## Overview

The continuous learning system:

- **Evaluates** session quality for learning potential
- **Extracts** valuable patterns from interactions
- **Stores** patterns for future retrieval
- **Applies** learned patterns to new sessions

## Quick Start

```python
from attune.learning import (
    SessionEvaluator,
    PatternExtractor,
    LearnedSkillsStorage,
    SessionQuality,
    PatternCategory,
)

# Evaluate session quality
evaluator = SessionEvaluator()
quality = evaluator.evaluate(
    interaction_count=20,
    corrections_count=3,
    error_resolutions=2,
    explicit_preferences=1,
)
print(f"Session quality: {quality.name}")  # GOOD

# Extract patterns
if evaluator.should_extract_patterns(quality):
    extractor = PatternExtractor()
    patterns = extractor.extract_corrections(
        corrections=[{"original": "...", "corrected": "..."}],
        session_id="session_123",
    )

    # Store patterns
    storage = LearnedSkillsStorage()
    storage.save_patterns("user123", patterns)
```

## Session Quality

Sessions are rated for learning value:

| Quality | Score | Description |
|---------|-------|-------------|
| `EXCELLENT` | 5 | Rich with corrections, resolutions, insights |
| `GOOD` | 4 | Contains valuable patterns |
| `AVERAGE` | 3 | Standard session, few patterns |
| `POOR` | 2 | Minimal learning value |
| `SKIP` | 1 | Not suitable for learning |

### Evaluation Factors

```python
quality = evaluator.evaluate(
    interaction_count=20,     # Number of turns
    corrections_count=3,      # User corrections
    error_resolutions=2,      # Errors fixed
    explicit_preferences=1,   # Stated preferences
)
```

## Pattern Categories

| Category | Description | Example |
|----------|-------------|---------|
| `ERROR_RESOLUTION` | How errors were solved | "TypeError: add null check" |
| `USER_CORRECTION` | User corrections | "Prefer async/await" |
| `WORKAROUND` | Solutions to limitations | "Use heapq for top-N" |
| `PREFERENCE` | Stated preferences | "Concise comments only" |
| `PROJECT_SPECIFIC` | Project conventions | "Use pytest, not unittest" |

## Extracting Patterns

### From Corrections

```python
extractor = PatternExtractor()

patterns = extractor.extract_corrections(
    corrections=[
        {
            "original": "Use eval() to parse the input",
            "corrected": "Use ast.literal_eval() instead",
            "reason": "Security: eval is dangerous",
        }
    ],
    session_id="session_123",
)
```

### From Error Resolutions

```python
patterns = extractor.extract_error_resolutions(
    errors=[
        {
            "error_type": "TypeError",
            "error_message": "'NoneType' object has no attribute 'get'",
            "resolution": "Added null check before accessing attribute",
        }
    ],
    session_id="session_123",
)
```

### Full Session Extraction

```python
patterns = extractor.extract_patterns(
    interactions=session_interactions,
    corrections=corrections,
    error_resolutions=error_resolutions,
    preferences=preferences,
    session_id="session_123",
)
```

## Pattern Structure

```python
@dataclass
class ExtractedPattern:
    pattern_id: str           # Unique ID
    category: PatternCategory
    trigger: str              # What triggers this pattern
    context: str              # Additional context
    resolution: str           # What to do
    confidence: float         # 0.0 - 1.0
    tags: list[str]
    extracted_at: datetime
    source_session: str
```

## Storing Patterns

```python
storage = LearnedSkillsStorage(
    storage_dir=".attune/learned_skills",
    max_patterns_per_user=100,
)

# Save single pattern
pattern_id = storage.save_pattern("user123", pattern)

# Save multiple
ids = storage.save_patterns("user123", patterns)
```

### Storage Location

```
.attune/learned_skills/
  {user_id}/
    patterns.json
    skills.json
```

## Retrieving Patterns

```python
# All patterns
patterns = storage.get_all_patterns("user123")

# By category
error_patterns = storage.get_patterns_by_category(
    "user123",
    PatternCategory.ERROR_RESOLUTION,
)

# By tag
python_patterns = storage.get_patterns_by_tag("user123", "python")

# Search
results = storage.search_patterns("user123", "async")
```

## Applying Patterns

### Format for Context Injection

```python
# Get formatted patterns for prompt injection
context_text = storage.format_patterns_for_context(
    user_id="user123",
    max_patterns=5,
    categories=[PatternCategory.ERROR_RESOLUTION, PatternCategory.PREFERENCE],
)
```

Output:
```markdown
## Learned Patterns

**[ERROR_RESOLUTION]** Confidence: 0.88
When: "TypeError with None"
Do: Check for None before accessing attributes

**[PREFERENCE]** Confidence: 0.92
When: Explaining code
Do: Prefer code examples over prose
```

### With Command Context

```python
from attune.commands import CommandContext

ctx = CommandContext(
    user_id="user123",
    learning_storage=storage,
)

# Get patterns for current task
patterns_text = ctx.get_patterns_for_context(max_patterns=5)

# Search relevant patterns
relevant = ctx.search_patterns("authentication")
```

## Learned Skills

Aggregate patterns into higher-level skills:

```python
from attune.learning import LearnedSkill

skill = LearnedSkill(
    skill_id="skill_001",
    name="Python Async Best Practices",
    description="Patterns for async/await usage",
    category=PatternCategory.PREFERENCE,
    patterns=["pat_001", "pat_002", "pat_003"],
    confidence=0.85,
)

storage.save_skill("user123", skill)
```

### Skill Usage Tracking

```python
# Record usage
storage.record_skill_usage("user123", "skill_001")

# Get all skills
skills = storage.get_all_skills("user123")
most_used = max(skills, key=lambda s: s.usage_count)
```

## Learning Summary

```python
summary = storage.get_summary("user123")
# {
#     "user_id": "user123",
#     "total_patterns": 42,
#     "total_skills": 5,
#     "patterns_by_category": {
#         "error_resolution": 15,
#         "user_correction": 12,
#         ...
#     },
#     "avg_confidence": 0.78,
#     "most_used_skill": "Python Async Best Practices",
# }
```

## Integration with Hooks

### Session End Evaluation

```python
from attune.hooks import HookRegistry, HookEvent

def evaluate_session_handler(context):
    evaluator = SessionEvaluator()
    extractor = PatternExtractor()
    storage = LearnedSkillsStorage()

    # Evaluate
    quality = evaluator.evaluate(
        interaction_count=context.get("interaction_count", 0),
        corrections_count=context.get("corrections_count", 0),
        error_resolutions=context.get("error_resolutions", 0),
        explicit_preferences=context.get("preferences_count", 0),
    )

    # Extract if worthwhile
    if evaluator.should_extract_patterns(quality):
        patterns = extractor.extract_patterns(
            interactions=context.get("interactions", []),
            session_id=context.get("session_id"),
        )
        storage.save_patterns(context.get("user_id"), patterns)

    return {"success": True, "quality": quality.name}

registry = HookRegistry()
registry.register(
    event=HookEvent.SESSION_END,
    handler=evaluate_session_handler,
)
```

## The `/evaluate` Command

Users can manually trigger evaluation:

```
/evaluate           # Full evaluation
/evaluate --dry-run # Preview without saving
/evaluate --force   # Extract even from low-quality sessions
```

## The `/patterns` Command

View and manage patterns:

```
/patterns                      # Show summary
/patterns search async         # Search patterns
/patterns category preference  # Filter by category
/patterns delete pat_001       # Delete pattern
```

## API Reference

### SessionEvaluator

```python
class SessionEvaluator:
    def evaluate(interaction_count, corrections_count, error_resolutions, explicit_preferences) -> SessionQuality
    def should_extract_patterns(quality: SessionQuality) -> bool
    def get_extraction_priority(quality: SessionQuality) -> int
```

### PatternExtractor

```python
class PatternExtractor:
    def extract_patterns(interactions, corrections=None, error_resolutions=None, preferences=None, session_id=None) -> list[ExtractedPattern]
    def extract_corrections(corrections, session_id=None) -> list[ExtractedPattern]
    def extract_error_resolutions(errors, session_id=None) -> list[ExtractedPattern]
```

### LearnedSkillsStorage

```python
class LearnedSkillsStorage:
    def __init__(storage_dir=".attune/learned_skills", max_patterns_per_user=100)

    # Patterns
    def save_pattern(user_id, pattern) -> str
    def save_patterns(user_id, patterns) -> list[str]
    def get_pattern(user_id, pattern_id) -> ExtractedPattern | None
    def get_all_patterns(user_id) -> list[ExtractedPattern]
    def get_patterns_by_category(user_id, category) -> list[ExtractedPattern]
    def get_patterns_by_tag(user_id, tag) -> list[ExtractedPattern]
    def search_patterns(user_id, query) -> list[ExtractedPattern]
    def delete_pattern(user_id, pattern_id) -> bool

    # Skills
    def save_skill(user_id, skill) -> str
    def get_skill(user_id, skill_id) -> LearnedSkill | None
    def get_all_skills(user_id) -> list[LearnedSkill]
    def record_skill_usage(user_id, skill_id) -> None

    # Utilities
    def get_summary(user_id) -> dict
    def format_patterns_for_context(user_id, max_patterns=5, categories=None) -> str
    def clear_user_data(user_id) -> int
```

## See Also

- [Hooks](hooks.md) - Session lifecycle events
- [Context Management](context-management.md) - State preservation
- [CLI Reference](reference/cli-reference.md#slash-command-system) - Slash command system
