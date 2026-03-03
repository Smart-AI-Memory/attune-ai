---
description: Intelligent Agent Team Creation - Right in Your IDE: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

<!-- markdownlint-disable MD036 -->
# Intelligent Agent Team Creation - Right in Your IDE

> Interactive mode with Claude Code: Get prompted when AI needs your input

**Published:** January 29, 2026
**Author:** Attune AI Team
**Reading Time:** 8 minutes
**Level:** Beginner to Intermediate

---

## TL;DR (2-minute read)

The Attune AI now has **intelligent interactive mode** for agent team creation:

- 🎯 **Smart branching**: High confidence (≥80%) → automatic, low confidence → asks you
- 💬 **IDE-native prompts**: Questions appear right in Claude Code's interface
- 🔧 **3 interaction paths**: Accept recommendation, customize team, or explore all 10 patterns
- ⚡ **Zero setup**: Works automatically when running in Claude Code
- 🆕 **3 new patterns**: Tool-enhanced, prompt-cached sequential, delegation chain

**Quick start:**

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Redesign authentication system",
    interactive=True
)
```

[Skip to complete workflow →](#running-in-claude-code-the-complete-workflow)

---

## What You'll Learn

By the end of this tutorial, you'll know how to:

- Run Python code that **pauses and prompts you** in Claude Code when it's uncertain
- Understand **when you'll be prompted** (confidence < 80%) vs automatic execution (≥80%)
- Choose between **3 interaction paths**: accept, customize, or explore patterns
- Use the **3 new Anthropic patterns** for optimal efficiency
- Build **custom handlers** for non-IDE use cases (CLI, web apps)

---

## The Problem: Sometimes AI Needs Your Input

Imagine you're building a system that automatically creates agent teams:

```python
plan = orchestrator.analyze_and_compose(
    task="Redesign our microservices architecture"
)
```

The system picks agents and a pattern... but what if it's unsure? What if multiple approaches could work?

**Traditional solution:** Build everything manually

- Too tedious for simple cases
- Error-prone
- Doesn't leverage AI intelligence

**Our solution:** Intelligent branching

- ✅ Automatic when confident (80%+ of cases)
- ✅ Interactive when uncertain
- ✅ Best of both worlds!

---

## Running in Claude Code: The Complete Workflow

This is the **easiest way** to use interactive mode. Zero configuration needed!

### Option 1: Ask Claude to Run It (Recommended)

**You say to Claude:**

```text
"Use the Attune AI to redesign our authentication system with interactive mode"
```

**Claude writes and runs:**

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Redesign authentication system for microservices",
    interactive=True
)
```

**What happens next:**

1. Code executes in the background
2. System analyzes task and calculates confidence
3. **If confidence < 80%**, a prompt appears in your Claude Code interface
4. You select your choice (recommended/customize/explore)
5. Claude shows you the result and can execute the plan

**Example output:**

```text
[INFO] Analyzing task: Redesign authentication system for microservices
[INFO] Task analysis: complexity=complex, domain=security
[INFO] Selected 3 agents: ['Security Architect', 'API Designer', 'Auth Specialist']
[INFO] Recommended strategy: delegation_chain
[INFO] Confidence score: 0.72
[INFO] Low confidence - prompting user for choice
```

---

### Option 2: Write It Yourself, Ask Claude to Run

**Create `run_orchestrator.py`:**

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Redesign authentication system",
    interactive=True
)

print(f"Pattern: {plan.strategy.value}")
print(f"Agents: {[a.role for a in plan.agents]}")
```

**Ask Claude:**

```text
"Run run_orchestrator.py"
```

Claude executes it, and you'll see the prompt if confidence is low.

---

### Option 3: Run from Terminal (Manual)

**In VSCode with Claude Code installed:**

```bash
# Terminal in VSCode
python run_orchestrator.py
```

When `AskUserQuestion` is called, Claude Code detects it and shows the prompt in the IDE.

**Important:** The Python process pauses while waiting for your response. You have 60 seconds to answer.

---

### What the Prompt Looks Like in Claude Code

When confidence < 80%, you'll see something like this in your Claude Code interface:

```text
┌─────────────────────────────────────────────────────┐
│ Python script is asking for input                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ How would you like to create the agent team?       │
│                                                     │
│ ○ Use recommended: delegation_chain (Recommended)  │
│   Auto-selected based on task analysis.            │
│   3 agents: Coordinator, Security Architect,       │
│   API Designer. Confidence: 72%                    │
│                                                     │
│ ○ Customize team composition                       │
│   Choose specific agents and pattern manually      │
│                                                     │
│ ○ Show all 10 patterns                             │
│   Learn about patterns and select one              │
│                                                     │
│ [Submit]  [Cancel]                                 │
└─────────────────────────────────────────────────────┘
```

**After you select and click Submit:**

- Your choice is sent back to Python
- Execution continues automatically
- Results appear in terminal or Claude's response

---

### Full Example: End-to-End

#### 1. You ask Claude

```text
"Help me create an agent team to analyze our codebase security"
```

#### 2. Claude writes

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Comprehensive security analysis of codebase",
    interactive=True
)
```

#### 3. Claude runs the code

#### 4. System analyzes

```text
[INFO] Analyzing task: Comprehensive security analysis of codebase
[INFO] Task analysis: complexity=complex, domain=security
[INFO] Selected 4 agents: ['Security Auditor', 'Code Reviewer',
                            'Dependency Scanner', 'Vulnerability Expert']
[INFO] Recommended strategy: parallel
[INFO] Confidence score: 0.72
[INFO] Low confidence - prompting user for choice
```

#### 5. Prompt appears in your IDE

*(see mockup above)*

#### 6. You select

"Use recommended: parallel"

#### 7. Execution continues

```text
[INFO] User accepted recommended approach
[INFO] Creating execution plan with 4 agents
[INFO] Pattern: parallel
✓ Execution plan created
```

#### 8. Claude shows you the plan

```text
Created agent team:
- Pattern: parallel (all agents run simultaneously)
- Agents: 4 security experts
- Estimated cost: $0.15
- Estimated duration: 120s

Would you like me to execute this plan?
```

---

## How It Works: The Confidence Branch

The system calculates **confidence** (0.0-1.0) based on 4 factors:

### Confidence Calculation

```python
confidence = 1.0

# Penalties
if domain == GENERAL:        confidence *= 0.7   # -30% (ambiguous domain)
if len(agents) > 5:          confidence *= 0.8   # -20% (many agents)
if complexity == COMPLEX:    confidence *= 0.85  # -15% (complex task)

# Bonuses
if pattern in [TOOL_ENHANCED, DELEGATION_CHAIN, PROMPT_CACHED]:
    confidence *= 1.1  # +10% (clear pattern match)
```

#### Threshold: 0.8 (80%)

- **≥80% confidence:** Execute automatically (no prompt)
- **<80% confidence:** Prompt user for choice

### The Decision Tree

```text
Your Code
    ↓
Analyze Task
    ↓
Calculate Confidence
    ↓
    ├─ ≥80% → Execute automatically ✓
    │         (You see nothing, it just works)
    │
    └─ <80% → Prompt in IDE:
              ┌─────────────────────────────────┐
              │ How create the agent team?      │
              ├─────────────────────────────────┤
              │ ○ Use recommended: sequential   │
              │   (Confidence: 72%)             │
              │ ○ Customize team composition    │
              │ ○ Show all 10 patterns          │
              └─────────────────────────────────┘
```

---

## What Gets High Confidence? (Automatic Execution)

These scenarios typically run automatically **without prompting**:

### ✓ Simple, clear tasks

```python
# Confidence: 0.95 - No prompt shown
plan = orchestrator.analyze_and_compose(
    task="Run tests and report coverage",
    interactive=True
)
```

**Why:** Clear domain (testing), simple task, 1-2 agents needed

### ✓ Domain-specific tasks

```python
# Confidence: 0.92 - No prompt shown
plan = orchestrator.analyze_and_compose(
    task="Generate API documentation from docstrings",
    interactive=True
)
```

**Why:** Clear domain (documentation), well-defined task

### ✓ Tasks with tools (triggers TOOL_ENHANCED)

```python
# Confidence: 0.88 - No prompt shown
plan = orchestrator.analyze_and_compose(
    task="Analyze Python files for complexity",
    context={"tools": [
        {"name": "read_file"},
        {"name": "parse_ast"}
    ]},
    interactive=True
)
```

**Why:** Clear pattern match (TOOL_ENHANCED), confidence bonus applies

---

## What Gets Low Confidence? (Prompts You)

These scenarios typically **prompt for user choice**:

### ✗ Ambiguous tasks

```python
# Confidence: 0.65 - PROMPTS YOU
plan = orchestrator.analyze_and_compose(
    task="Improve the system",  # Too vague
    interactive=True
)
```

**Why:** General domain (ambiguous), unclear requirements

### ✗ Complex architectural changes

```python
# Confidence: 0.70 - PROMPTS YOU
plan = orchestrator.analyze_and_compose(
    task="Redesign authentication architecture for microservices",
    interactive=True
)
```

**Why:** Complex task, general domain, multiple valid approaches

### ✗ Many agents needed

```python
# Confidence: 0.72 - PROMPTS YOU (6 agents selected)
plan = orchestrator.analyze_and_compose(
    task="Complete security audit across all systems",
    interactive=True
)
```

**Why:** 6 agents needed (penalty for >5 agents), complex coordination

---

## The Three Interaction Paths

When the system prompts you (confidence < 80%), you get **3 options**:

### Path 1: Accept Recommendation (Fastest)

**What it does:** Uses the auto-selected pattern and agents

**When to use:**

- ✅ The recommendation looks good
- ✅ You trust the confidence score (even if <80%)
- ✅ You want to proceed quickly

**Example:**

```text
You select: "Use recommended: delegation_chain"

[INFO] User accepted recommended approach
[INFO] Creating plan with 3 agents: Coordinator, Security Architect, API Designer
[INFO] Using pattern: delegation_chain
✓ Execution plan created
```

---

### Path 2: Customize Team (Most Control)

**What it does:** Lets you pick specific agents and pattern

**When to use:**

- ✅ You know exactly which agents you need
- ✅ You want a different pattern than recommended
- ✅ You're experimenting with team composition

**Example flow:**

#### Step 1: Agent selection

```text
Which agents should be included in the team?

☑ Security Architect
☑ API Designer
☐ Database Expert
☐ UI/UX Specialist
☐ Performance Analyst

(Select multiple)
```

#### Step 2: Pattern selection

```text
Which composition pattern should be used?

○ delegation_chain (Recommended)
  Hierarchical coordinator → specialists

○ sequential
  Execute agents one after another

● parallel
  Execute agents simultaneously

You selected: parallel
```

**Result:** Custom team with your selections

---

### Path 3: Explore Patterns (Educational)

**What it does:** Shows all 10 patterns with descriptions and examples

**When to use:**

- ✅ You're learning about patterns
- ✅ Not sure which pattern fits
- ✅ Want to see all options

**What you see:**

```text
Choose a composition pattern:

○ sequential
  A → B → C | Step-by-step pipeline
  Example: Parse → Analyze → Report

○ parallel
  A || B || C | Independent tasks
  Example: Security + Quality + Performance audits

○ tool_enhanced (NEW)
  Single agent + tools | Most efficient
  Example: File reader with analysis tools

○ delegation_chain (NEW)
  Coordinator → Specialists | Hierarchical
  Example: Task planner delegates to architects

○ prompt_cached_sequential (NEW)
  Sequential + cached context | Cost-optimized
  Example: Multiple agents reviewing same docs

[... 5 more patterns ...]
```

---

## The 3 New Anthropic Patterns

We've added 3 battle-tested patterns from [Anthropic's agent guidelines](https://anthropic.com/research/building-effective-agents). These get **confidence boosts** because they have clear heuristics:

### 1. Tool-Enhanced (Pattern 8)

**When automatically selected:**

- Single task + tools provided in context
- File analysis, data processing, code parsing

**Why it's better:**

- 67% cost reduction vs multi-agent sequential
- 60% faster execution
- Single agent maintains full context

**Example:**

```python
# Automatically selects TOOL_ENHANCED
plan = orchestrator.analyze_and_compose(
    task="Analyze codebase complexity",
    context={
        "tools": [
            {"name": "read_file", "description": "Read file contents"},
            {"name": "parse_ast", "description": "Parse Python AST"}
        ]
    },
    interactive=True
)
```

---

### 2. Prompt-Cached Sequential (Pattern 9)

**When automatically selected:**

- 3+ agents need same large context
- Codebase analysis, documentation review

**Why it's better:**

- 60% token cost reduction with cache hits
- Large context (10k+ tokens) cached once, shared across agents
- Sequential execution maintains order

**Example:**

```python
# Automatically selects PROMPT_CACHED_SEQUENTIAL
large_docs = """
[10,000+ lines of architecture docs, API specs, coding standards...]
"""

plan = orchestrator.analyze_and_compose(
    task="Comprehensive codebase review",
    context={"cached_context": large_docs},
    interactive=True
)
```

---

### 3. Delegation Chain (Pattern 10)

**When automatically selected:**

- Complex task requiring coordination
- Multiple specialist domains
- Hierarchical decomposition needed

**Why it's better:**

- Better organization and responsibility boundaries
- Max 3 levels of hierarchy (prevents complexity explosion)
- Coordinator handles task decomposition

**Example:**

```python
# Automatically selects DELEGATION_CHAIN
plan = orchestrator.analyze_and_compose(
    task="Prepare comprehensive architecture redesign",
    interactive=True
)
# → Coordinator agent analyzes and delegates to specialists
```

[Full pattern guide →](../how-to/practical-patterns.md)

---

## Advanced: Custom Handlers (For Non-IDE Use)

If you're building a **web app**, **CLI tool**, or **custom UI**, you can provide your own handler:

### CLI Handler Example

```python
from attune.orchestration import MetaOrchestrator
from attune.tools import set_ask_user_question_handler

def cli_handler(questions):
    """Simple CLI prompts."""
    answers = {}
    for q in questions:
        print(f"\n{q['question']}")
        for i, opt in enumerate(q['options'], 1):
            print(f"  {i}. {opt['label']}")
            print(f"     {opt['description']}")

        choice = int(input("\nYour choice: "))
        answers[q['header']] = q['options'][choice-1]['label']

    return answers

# Register your handler
set_ask_user_question_handler(cli_handler)

# Now interactive mode uses YOUR handler
orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Complex task",
    interactive=True
)
```

### Web Application Handler

```python
from flask import Flask, request, jsonify
from attune.tools import set_ask_user_question_handler

pending_questions = {}

def web_handler(questions):
    """Store questions, return via API."""
    request_id = str(uuid.uuid4())
    pending_questions[request_id] = questions

    # Signal "waiting for user input"
    raise PendingUserInputException(request_id)

set_ask_user_question_handler(web_handler)

@app.route('/api/create-team', methods=['POST'])
def create_team():
    try:
        plan = orchestrator.analyze_and_compose(
            task=request.json['task'],
            interactive=True
        )
        return jsonify({'status': 'success', 'plan': plan.to_dict()})

    except PendingUserInputException as e:
        return jsonify({
            'status': 'pending',
            'request_id': e.request_id,
            'questions': pending_questions[e.request_id]
        })
```

### Jupyter Notebook Handler

```python
from attune.tools import set_ask_user_question_handler
from ipywidgets import RadioButtons, VBox
from IPython.display import display

def notebook_handler(questions):
    """Interactive Jupyter widgets."""
    answers = {}
    for q in questions:
        print(f"\n{q['question']}\n")

        radio = RadioButtons(
            options=[opt['label'] for opt in q['options']],
            description=''
        )
        display(radio)

        # Wait for user interaction
        answers[q['header']] = radio.value

    return answers

set_ask_user_question_handler(notebook_handler)
```

**Use cases for custom handlers:**

- Terminal/CLI applications
- Web applications with custom UI
- Mobile apps
- Jupyter notebooks
- Custom integrations

[Full integration guide →](../integration/claude-code-integration.md)

---

## Troubleshooting

| Issue | Cause | Solution |
| ------- | ------- | ---------- |
| No prompt shown | Confidence ≥80% | **This is normal!** High confidence = automatic execution |
| `NotImplementedError` | No handler, not in Claude Code | Use `interactive=False` or add handler |
| Timeout error | User didn't respond within 60s | Respond faster or increase timeout in `tools.py` |
| Wrong pattern selected | Low confidence in choice | Use `interactive=True` to customize |

### Disabling Interactive Mode

If you want pure automation (no prompts ever):

```python
plan = orchestrator.analyze_and_compose(
    task="Any task",
    interactive=False  # Never prompts, always automatic
)
```

### Testing Interactive Mode

Force low confidence to test prompting:

```python
from unittest.mock import patch

# Force confidence below 0.8 to trigger prompt
with patch.object(orchestrator, '_calculate_confidence', return_value=0.7):
    plan = orchestrator.analyze_and_compose(
        task="Test task",
        interactive=True
    )
```

---

## When to Use Interactive Mode?

### Use `interactive=True` when

- ✅ Task is complex or ambiguous
- ✅ Multiple valid approaches exist
- ✅ You want to learn about patterns
- ✅ You're experimenting with approaches
- ✅ Working in IDE with Claude Code

### Use `interactive=False` when

- ⚡ Task is straightforward
- ⚡ Running in CI/CD pipelines
- ⚡ Confidence is consistently high (>80%)
- ⚡ Full automation is priority
- ⚡ No user available to respond

---

## Summary

**What we built:**

- 🤖 **Confidence-based branching** (≥80% = auto, <80% = prompt)
- 💬 **IDE-native prompts** in Claude Code (zero setup)
- 🎯 **Three interaction paths** (accept, customize, explore)
- 🔧 **Custom handlers** for CLI/web apps
- ⚡ **3 new Anthropic patterns** (tool-enhanced, prompt-cached, delegation)

**Try it now in Claude Code:**

Just ask Claude:

```text
"Use the Attune AI to [your task] with interactive mode"
```

Or write your own:

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Your complex task here",
    interactive=True
)
```

Run this in Claude Code and see the magic happen!

---

## Next Steps

- 🔧 [Claude Code integration guide](../integration/claude-code-integration.md)
- 🎯 [Pattern selection guide](../how-to/practical-patterns.md)
- 💬 [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

---

**Happy agent orchestrating!** 🎉

*Built by Patrick Roebuck in collaboration with Claude*
*Implementing patterns from Anthropic's agent research*
