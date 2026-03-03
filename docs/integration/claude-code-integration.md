---
description: Claude Code Integration Guide integration guide. Connect external tools and services with Attune AI for enhanced AI capabilities.
---

# Claude Code Integration Guide

**Status:** ✅ Implemented
**Version:** 1.0
**Date:** January 29, 2026

---

## Overview

The Attune AI integrates with Claude Code to provide interactive agent team creation. When users choose `interactive=True`, the meta-orchestrator can prompt them with questions in the IDE.

---

## Architecture

### Three Integration Modes

The `AskUserQuestion` function supports three modes:

#### 1. **Custom Handler Mode** (Recommended for testing)
```python
from attune.tools import set_ask_user_question_handler

def my_handler(questions):
    # Your custom UI logic
    print(f"Questions: {questions}")
    return {"Pattern": "sequential"}

set_ask_user_question_handler(my_handler)

# Now interactive mode will use your handler
orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(task="...", interactive=True)
```

#### 2. **Claude Code IPC Mode** (Automatic in Claude Code)
When running in Claude Code environment, uses file-based IPC:
- Python code writes request to `/tmp/.claude-code-ipc/ask-request-{id}.json`
- Claude Code monitors directory and shows UI prompt
- Claude Code writes response to `/tmp/.claude-code-ipc/ask-response-{id}.json`
- Python code reads response and continues

#### 3. **Fallback Mode** (Raises NotImplementedError)
If no handler is set and not in Claude Code environment, raises helpful error.

---

## Usage Examples

### Example 1: Interactive Mode in Claude Code

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()

# Interactive mode - will prompt user when confidence < 0.8
plan = orchestrator.analyze_and_compose(
    task="Redesign system architecture",
    context={},
    interactive=True
)

# User sees prompt in IDE:
# ┌─────────────────────────────────────────┐
# │ How would you like to create the team?  │
# ├─────────────────────────────────────────┤
# │ ○ Use recommended: delegation_chain     │
# │   (Confidence: 65%)                     │
# │ ○ Customize team composition            │
# │ ○ Show all 10 patterns                  │
# └─────────────────────────────────────────┘

# After user selection, execution continues automatically
print(f"Selected: {plan.strategy.value}")
print(f"Agents: {[a.role for a in plan.agents]}")
```

### Example 2: Custom Handler for Testing

```python
from attune.tools import set_ask_user_question_handler
from attune.orchestration import MetaOrchestrator

# Set up test handler
def test_handler(questions):
    # Simulate user always choosing first option
    answers = {}
    for q in questions:
        header = q["header"]
        first_option = q["options"][0]["label"]
        answers[header] = first_option
    return answers

set_ask_user_question_handler(test_handler)

# Now test interactive mode
orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Complex task",
    interactive=True
)

# Handler will be called automatically when confidence is low
```

### Example 3: CLI Integration

```python
from attune.tools import set_ask_user_question_handler

def cli_handler(questions):
    """Simple CLI prompt for questions."""
    answers = {}

    for q in questions:
        print(f"\n{q['question']}")
        options = q['options']

        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt['label']}")
            print(f"     {opt['description']}")

        if q['multiSelect']:
            print("Enter numbers separated by commas:")
        else:
            print("Enter number:")

        choice = input("> ").strip()

        if q['multiSelect']:
            selected = [options[int(i)-1]['label'] for i in choice.split(',')]
            answers[q['header']] = selected
        else:
            answers[q['header']] = options[int(choice)-1]['label']

    return answers

# Use CLI handler
set_ask_user_question_handler(cli_handler)
```

---

## IPC Protocol Specification

### Request Format

File: `/tmp/.claude-code-ipc/ask-request-{uuid}.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1706553600.0,
  "questions": [
    {
      "header": "Approach",
      "question": "How would you like to create the agent team?",
      "multiSelect": false,
      "options": [
        {
          "label": "Use recommended: delegation_chain (Recommended)",
          "description": "Auto-selected based on task analysis. 3 agents: Coordinator, Architect, Analyst. Confidence: 65%"
        },
        {
          "label": "Customize team composition",
          "description": "Choose specific agents and pattern manually"
        },
        {
          "label": "Show all 10 patterns",
          "description": "Learn about patterns and select one"
        }
      ]
    }
  ]
}
```

### Response Format

File: `/tmp/.claude-code-ipc/ask-response-{uuid}.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1706553605.0,
  "answers": {
    "Approach": "Use recommended: delegation_chain (Recommended)"
  }
}
```

### Timeout Behavior

- Python code waits max 60 seconds for response
- If timeout: raises `RuntimeError` with message about user cancellation
- Meta-orchestrator catches error and falls back to automatic mode

---

## Environment Detection

The IPC mode activates when any of these conditions are met:

1. `CLAUDE_CODE_SESSION` environment variable is set
2. `CLAUDE_AGENT_MODE` environment variable is set
3. `/tmp/.claude-code` marker file exists

### Setting Up Environment

```bash
# Enable Claude Code IPC mode
export CLAUDE_CODE_SESSION=1

# Or create marker file
touch /tmp/.claude-code

# Run your script
python your_script.py
```

---

## Testing Interactive Features

### Unit Tests

```python
from attune.tools import set_ask_user_question_handler
from attune.orchestration import MetaOrchestrator

def test_interactive_mode():
    # Mock user choices
    def mock_handler(questions):
        return {"Approach": "Use recommended: sequential (Recommended)"}

    set_ask_user_question_handler(mock_handler)

    # Test
    orchestrator = MetaOrchestrator()
    plan = orchestrator.analyze_and_compose(
        task="Complex task",
        interactive=True
    )

    assert plan is not None
    assert plan.strategy is not None
```

### Integration Tests

```bash
# Start IPC monitor in background
python scripts/claude_code_ipc_monitor.py &

# Enable Claude Code mode
export CLAUDE_CODE_SESSION=1

# Run your code
python -c "
from attune.orchestration import MetaOrchestrator
orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task='Complex architectural redesign',
    interactive=True
)
print(f'Selected: {plan.strategy.value}')
"

# Stop monitor
pkill -f claude_code_ipc_monitor
```

---

## Troubleshooting

### Issue: "AskUserQuestion requires integration"

**Cause:** Not in Claude Code environment and no custom handler set.

**Solution:**
```python
# Option 1: Use automatic mode
plan = orchestrator.analyze_and_compose(task="...", interactive=False)

# Option 2: Set custom handler
set_ask_user_question_handler(my_handler)

# Option 3: Enable IPC mode
export CLAUDE_CODE_SESSION=1
```

### Issue: "Timeout waiting for user response"

**Cause:** IPC monitor not running or user didn't respond within 60s.

**Solution:**
```bash
# Start IPC monitor
python scripts/claude_code_ipc_monitor.py &

# Or increase timeout in code:
# Edit src/attune/tools.py, change timeout=60 to higher value
```

### Issue: "No questions asked even with interactive=True"

**Cause:** Confidence score >= 0.8, so automatic mode was used.

**Solution:**
```python
# Force low confidence for testing
import unittest.mock as mock

with mock.patch.object(orchestrator, '_calculate_confidence', return_value=0.7):
    plan = orchestrator.analyze_and_compose(task="...", interactive=True)
    # Now will prompt user
```

---

## Production Deployment

### Recommended Setup

1. **For CLI applications:**
   - Use custom CLI handler (see Example 3)
   - Or use IPC mode with monitor running

2. **For web applications:**
   - Use custom handler that integrates with your web UI
   - Store questions in session, show in next response
   - Collect answers via form submission

3. **For IDE extensions:**
   - Use IPC mode
   - Claude Code monitors and shows native IDE prompts

### Performance Considerations

- IPC adds ~100-200ms latency per question
- Custom handlers are instant
- Confidence scoring adds <1ms overhead
- Overall: Interactive mode ~95% as fast as automatic mode

---

## Future Enhancements

### Planned Features

1. **WebSocket IPC** - Real-time communication instead of file polling
2. **Rich UI Components** - Progress bars, previews, diagrams
3. **Pattern Visualizations** - Show flow diagrams in prompts
4. **History & Suggestions** - Learn from user choices
5. **Batch Questions** - Collect multiple answers in single prompt

### API Stability

Current API is **stable** and will be maintained:
- `set_ask_user_question_handler(handler)` - Will not change
- `AskUserQuestion(questions)` - Signature will not change
- IPC format - Will be versioned (v1, v2, etc.)

---

## Related Documentation

- Interactive Agent Creation
- Anthropic Patterns Integration
- Meta-Orchestrator API

---

## Support

Questions or issues with Claude Code integration?

- GitHub Issues: https://github.com/Smart-AI-Memory/attune-ai/issues
- Discord: https://discord.gg/attune-ai
- Email: support@attune-ai.dev

---

**Version:** 1.0
**Last Updated:** January 29, 2026
**Maintained By:** Attune AI Team
