---
description: Meta-Workflow CLI Command Reference API reference: **Version:** 4.2.0 **Last Updated:** 2026-01-17 **Total Commands:** 10 --- ## Quick Reference empath
---

# Meta-Workflow CLI Command Reference

**Version:** 4.2.0
**Last Updated:** 2026-01-17
**Total Commands:** 10

---

## Quick Reference

```bash
attune meta-workflow <command> [options]
```

### Template Management

| Command | Description | Usage |
|---------|-------------|-------|
| `list-templates` | List all available workflow templates | `attune meta-workflow list-templates` |
| `inspect` | Inspect a specific template in detail | `attune meta-workflow inspect <template_id>` |

### Workflow Execution

| Command | Description | Usage |
|---------|-------------|-------|
| `run` | Execute a meta-workflow from template | `attune meta-workflow run <template_id>` |
| `list-runs` | List historical executions | `attune meta-workflow list-runs` |
| `show` | Show detailed execution report | `attune meta-workflow show <run_id>` |
| `cleanup` | Clean up old execution results | `attune meta-workflow cleanup` |

### Analytics & Learning

| Command | Description | Usage |
|---------|-------------|-------|
| `analytics` | Show pattern learning insights | `attune meta-workflow analytics [template_id]` |
| `search-memory` | Search memory for patterns | `attune meta-workflow search-memory <query>` |

### Session Context

| Command | Description | Usage |
|---------|-------------|-------|
| `session-stats` | Show session context statistics | `attune meta-workflow session-stats` |
| `suggest-defaults` | Get suggested defaults based on history | `attune meta-workflow suggest-defaults <template_id>` |

---

## Detailed Command Reference

### 1. `list-templates`

**Purpose:** List all available workflow templates

**Usage:**
```bash
attune meta-workflow list-templates
```

**Output:**
```
Available Templates (5):

╭────────────────────────────────────────────────────────────╮
│ Test Creation and Management Workflow                      │
│ Enterprise-level test creation, inspection, updating...    │
│                                                            │
│ ID: test_creation_management_workflow                      │
│ Questions: 12                                              │
│ Agent Rules: 11                                            │
│ Est. Cost: $0.30-$3.50                                     │
╰────────────────────────────────────────────────────────────╯
```

---

### 2. `inspect`

**Purpose:** Inspect a specific template in detail

**Usage:**
```bash
attune meta-workflow inspect <template_id>
```

**Examples:**
```bash
# Inspect test creation workflow
attune meta-workflow inspect test_creation_management_workflow

# Inspect security audit workflow
attune meta-workflow inspect security_audit_workflow
```

**Output:**
```
Template: Test Creation and Management Workflow
Enterprise-level test creation, inspection, updating...

Form Questions:
📋 Questions
├── 1. What is the scope of your testing effort?
│   ├── ID: test_scope
│   ├── Type: single_select
│   └── Options: Single function/class, Single module/package...
├── 2. What types of tests should be created?
│   ├── ID: test_types
│   ├── Type: multi_select
│   └── Options: Unit tests, Integration tests...
...

Summary:
  Questions: 12
  Agent Rules: 11
  Estimated Cost: $0.30-$3.50
```

---

### 3. `run`

**Purpose:** Execute a meta-workflow from template

**Usage:**
```bash
attune meta-workflow run <template_id> [OPTIONS]
```

**Options:**
- `--mock / --real` - Use mock execution (default: mock)
- `-m, --use-memory` - Enable memory integration
- `-u, --user-id TEXT` - User ID for memory integration (default: cli_user)

**Examples:**
```bash
# Run test creation workflow (mock mode)
attune meta-workflow run test_creation_management_workflow

# Run with real LLM integration (when implemented)
attune meta-workflow run test_creation_management_workflow --real

# Run with memory integration
attune meta-workflow run test_creation_management_workflow -m --user-id "user@example.com"
```

**Interactive Flow:**
1. Loads template
2. Asks form questions (batched, max 4 at a time)
3. Generates agent team based on responses
4. Executes agents (mock or real)
5. Saves results to files + memory (if enabled)
6. Displays summary

---

### 4. `list-runs`

**Purpose:** List historical executions

**Usage:**
```bash
attune meta-workflow list-runs [OPTIONS]
```

**Options:**
- `--template-id TEXT` - Filter by template ID
- `--limit INTEGER` - Maximum number of runs to display (default: 20)

**Examples:**
```bash
# List all recent runs
attune meta-workflow list-runs

# List runs for specific template
attune meta-workflow list-runs --template-id test_creation_management_workflow

# List last 50 runs
attune meta-workflow list-runs --limit 50
```

**Output:**
```
Recent Execution History (3 runs):

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓
┃ Run ID                     ┃ Template               ┃ Success ┃ Cost  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩
│ test_...-20260117-070612   │ test_creation_...      │ ✓       │ $1.75 │
│ code_...-20260117-064532   │ code_refactoring_...   │ ✓       │ $0.89 │
│ python_...-20260117-063210 │ python_package_publish │ ✓       │ $0.12 │
└────────────────────────────┴────────────────────────┴─────────┴───────┘
```

---

### 5. `show`

**Purpose:** Show detailed execution report

**Usage:**
```bash
attune meta-workflow show <run_id>
```

**Examples:**
```bash
attune meta-workflow show test_creation_management_workflow-20260117-070612
```

**Output:**
```
╭─ Execution Report ─────────────────────────────────────────╮
│                                                            │
│ Run ID: test_creation_management_workflow-20260117-070612 │
│ Template: test_creation_management_workflow                │
│ Status: ✓ Success                                          │
│ Timestamp: 2026-01-17T07:06:14                             │
│                                                            │
│ Agents Created: 11                                         │
│ Total Cost: $1.75                                          │
│ Duration: 33.5s                                            │
│                                                            │
╰────────────────────────────────────────────────────────────╯

Agent Execution Results:
  ✓ test_analyzer (capable, $0.25, 4.0s)
  ✓ unit_test_generator (capable, $0.15, 3.0s)
  ...

Form Responses:
  test_scope: Entire project (full suite)
  test_types: Unit tests, Integration tests, E2E tests
  ...
```

---

### 6. `cleanup`

**Purpose:** Clean up old execution results

**Usage:**
```bash
attune meta-workflow cleanup [OPTIONS]
```

**Options:**
- `--older-than INTEGER` - Delete runs older than N days (default: 30)
- `--dry-run` - Preview what would be deleted without deleting

**Examples:**
```bash
# Clean up runs older than 30 days
attune meta-workflow cleanup

# Preview what would be deleted
attune meta-workflow cleanup --dry-run

# Clean up runs older than 7 days
attune meta-workflow cleanup --older-than 7
```

**Output:**
```
Executions to delete: (2)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ Run ID                   ┃ Template       ┃ Age (days)┃ Cost  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│ old_run_123             │ test_creation  │ 45        │ $1.50 │
│ old_run_456             │ security_audit │ 60        │ $2.00 │
└─────────────────────────┴────────────────┴───────────┴───────┘

Total cost represented: $3.50

Delete 2 execution(s)? [y/N]:
```

---

### 7. `analytics`

**Purpose:** Show pattern learning analytics and recommendations

**Usage:**
```bash
attune meta-workflow analytics [template_id] [OPTIONS]
```

**Options:**
- `--min-confidence FLOAT` - Minimum confidence threshold (default: 0.5)
- `-m, --use-memory` - Use memory-enhanced analytics

**Examples:**
```bash
# Show analytics for all templates
attune meta-workflow analytics

# Show analytics for specific template
attune meta-workflow analytics test_creation_management_workflow

# Use memory-enhanced analytics
attune meta-workflow analytics -m

# Set confidence threshold
attune meta-workflow analytics --min-confidence 0.7
```

**Output:**
```
╭─ Pattern Learning Analytics ──────────────────────────────╮
│                                                            │
│ Template: test_creation_management_workflow                │
│ Executions Analyzed: 15                                    │
│                                                            │
│ Agent Count:                                               │
│   Min: 8 agents                                            │
│   Max: 11 agents                                           │
│   Avg: 9.5 agents                                          │
│                                                            │
│ Tier Performance:                                          │
│   cheap: Success: 95%, Avg Cost: $0.05                    │
│   capable: Success: 88%, Avg Cost: $0.20                  │
│   premium: Success: 100%, Avg Cost: $0.45                 │
│                                                            │
│ Cost Analysis:                                             │
│   Total Cost: $26.25                                       │
│   Avg per Run: $1.75                                       │
│   By Tier: cheap: $4.50, capable: $18.00, premium: $3.75  │
│                                                            │
│ Recommendations:                                           │
│   • Consider using capable tier for test_analyzer         │
│   • Progressive escalation working well for unit tests     │
│   • Consider batch execution for multiple runs            │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

---

### 8. `search-memory` (NEW)

**Purpose:** Search memory for patterns using keyword matching

**Usage:**
```bash
attune meta-workflow search-memory <query> [OPTIONS]
```

**Options:**
- `-t, --type TEXT` - Filter by pattern type (e.g., 'meta_workflow_execution')
- `-l, --limit INTEGER` - Maximum results to return (default: 10)
- `-u, --user-id TEXT` - User ID for memory access (default: cli_user)

**Examples:**
```bash
# Search for successful workflows
attune meta-workflow search-memory "successful workflow"

# Search for test-related patterns
attune meta-workflow search-memory "test coverage" --type meta_workflow_execution

# Search with custom limit
attune meta-workflow search-memory "error" --limit 20

# Search with specific user ID
attune meta-workflow search-memory "refactoring" -u "user@example.com"
```

**Output:**
```
Searching memory for: 'successful workflow'

Found 3 matching pattern(s):

╭─ Result 1/3 ──────────────────────────────────────────────╮
│                                                            │
│ Pattern ID: pattern_abc123                                │
│ Type: meta_workflow_execution                              │
│ Classification: INTERNAL                                   │
│                                                            │
│ Content:                                                   │
│ Successful execution of test_creation_management_workflow │
│ with 11 agents, total cost $1.75...                       │
│                                                            │
│ Metadata: {'run_id': 'test_...-070612', 'cost': 1.75}    │
╰────────────────────────────────────────────────────────────╯
```

**How Search Works:**
- **Relevance Scoring:**
  - Exact phrase match in content: 10 points
  - Keyword in content: 2 points
  - Keyword in metadata: 1 point
- **Results:** Sorted by relevance (highest score first)
- **Filtering:** By pattern_type and classification
- **Performance:** ~10-50ms for 1000 patterns

---

### 9. `session-stats` (NEW)

**Purpose:** Show session context statistics

**Usage:**
```bash
attune meta-workflow session-stats [OPTIONS]
```

**Options:**
- `-s, --session-id TEXT` - Session ID (optional, creates new if not specified)
- `-u, --user-id TEXT` - User ID for session (default: cli_user)

**Examples:**
```bash
# Show stats for current session
attune meta-workflow session-stats

# Show stats for specific session
attune meta-workflow session-stats --session-id sess_abc123

# Show stats for specific user
attune meta-workflow session-stats -u "user@example.com"
```

**Output:**
```
Session Statistics
Session ID: sess_abc123
User ID: cli_user

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric               ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Total Choices        │ 24                              │
│ Templates Used       │ 3                               │
│ Most Recent Choice   │ 2026-01-17T07:06:12             │
└──────────────────────┴─────────────────────────────────┘

Templates Used:
  • test_creation_management_workflow
  • code_refactoring_workflow
  • python_package_publish
```

**Use Case:**
- Track user's workflow history
- Analyze form choice patterns
- Monitor session activity

---

### 10. `suggest-defaults` (NEW)

**Purpose:** Get suggested default values based on session history

**Usage:**
```bash
attune meta-workflow suggest-defaults <template_id> [OPTIONS]
```

**Options:**
- `-s, --session-id TEXT` - Session ID (optional)
- `-u, --user-id TEXT` - User ID for session (default: cli_user)

**Examples:**
```bash
# Get suggestions for test creation workflow
attune meta-workflow suggest-defaults test_creation_management_workflow

# Get suggestions with specific session
attune meta-workflow suggest-defaults python_package_publish --session-id sess_abc123

# Get suggestions for specific user
attune meta-workflow suggest-defaults code_refactoring_workflow -u "user@example.com"
```

**Output:**
```
Suggested Defaults for: Test Creation and Management Workflow
Template ID: test_creation_management_workflow

Found 8 suggested default(s):

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Question ID                             ┃ Suggested Value        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ What is the scope of your testing...   │ Entire project         │
│ What types of tests should be created? │ Unit tests, Integra... │
│ Which testing framework should be...   │ pytest (Python)        │
│ What is your target test coverage?     │ 80% (good coverage)    │
│ ...                                     │ ...                    │
└─────────────────────────────────────────┴────────────────────────┘

Use these defaults by running:
  attune meta-workflow run test_creation_management_workflow --use-defaults
```

**How It Works:**
1. Analyzes recent choices for the specified template
2. Uses TTL-based expiration (default: 1 hour)
3. Validates suggestions against form schema
4. Returns only valid, recent choices

**Benefits:**
- Saves time on repeated workflows
- Learns from user preferences
- Reduces form fatigue

---

## Tips & Best Practices

### 1. Quick Workflow Execution
```bash
# Find template you want
attune meta-workflow list-templates

# Inspect to see questions
attune meta-workflow inspect <template_id>

# Run the workflow
attune meta-workflow run <template_id>
```

### 2. Using Suggested Defaults
```bash
# First run (answer all questions)
attune meta-workflow run test_creation_management_workflow

# Next time (get suggestions first)
attune meta-workflow suggest-defaults test_creation_management_workflow

# Then run with suggested values pre-filled
attune meta-workflow run test_creation_management_workflow --use-defaults
```

### 3. Memory Search for Debugging
```bash
# Find failed executions
attune meta-workflow search-memory "error" --type meta_workflow_execution

# Find expensive runs
attune meta-workflow search-memory "cost" --limit 20

# Find specific workflow outcomes
attune meta-workflow search-memory "test coverage 80%"
```

### 4. Analytics-Driven Optimization
```bash
# Check overall performance
attune meta-workflow analytics

# Focus on specific template
attune meta-workflow analytics test_creation_management_workflow -m

# Use insights to optimize tier strategies in templates
```

### 5. Cleanup Old Data
```bash
# Preview before deleting
attune meta-workflow cleanup --dry-run

# Clean up monthly
attune meta-workflow cleanup --older-than 30

# Aggressive cleanup for testing
attune meta-workflow cleanup --older-than 7
```

---

## Environment Variables

```bash
# Set default user ID
export ATTUNE_USER_ID="user@example.com"

# Set default memory directory
export ATTUNE_MEMORY_DIR="$HOME/.empathy/memory"

# Set default template directory
export ATTUNE_TEMPLATE_DIR="$HOME/.empathy/meta_workflows/templates"
```

---

## Troubleshooting

### Command Not Found
```bash
# Reinstall in editable mode
pip install -e .

# Or reinstall from PyPI
pip install --upgrade attune-ai
```

### Memory Not Available
```bash
# Check if memory module is installed
python -c "from attune.memory.unified import UnifiedMemory"

# If error, reinstall with memory support
pip install attune-ai[memory]
```

### Template Not Found
```bash
# Check templates directory
ls ~/.empathy/meta_workflows/templates/

# Or use project-local templates
export ATTUNE_TEMPLATE_DIR="./empathy/meta_workflows/templates"
```

---

## Related Documentation

- [V4.2.0 Release Summary](V4.2.0_RELEASE_SUMMARY.md)
- [Workflow Templates Reference](docs/WORKFLOW_TEMPLATES.md)
- [Meta-Workflows User Guide](docs/META_WORKFLOWS.md)
- [UX Improvement Plan](UX_IMPROVEMENT_PLAN.md)

---

**Version:** 4.2.0
**Last Updated:** 2026-01-17
**Total Commands:** 10 (3 new in v4.2.0)
