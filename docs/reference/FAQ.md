---
description: Frequently Asked Questions
---

# Frequently Asked Questions

**Last Updated:** April 23, 2026

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Teaching AI Your Standards](#teaching-ai-your-standards)
3. [Tool Compatibility](#tool-compatibility)
4. [Implementation](#implementation)
5. [Cost Optimization](#cost-optimization)
6. [Results & ROI](#results-roi)
7. [Common Concerns](#common-concerns)
8. [Wizards](#wizards)
9. [Advanced Topics](#advanced-topics)

---

## Getting Started

### What is the Attune AI?

Attune AI is an open-source Python framework that gives AI assistants persistent memory, multi-agent coordination, and anticipatory intelligence.

#### Core capabilities

- 🧠 **Persistent Memory**: Pattern library that survives sessions (git-based + optional Redis)
- 🤝 **Multi-Agent Coordination**: AI teams that share context and validate each other
- 🔮 **Anticipatory Intelligence**: Predicts potential bugs based on learned patterns
- 🛡️ **Enterprise-Ready**: Local-first, HIPAA-compliant options, comprehensive security
- 💰 **Cost Optimization**: Smart tier routing saves 34-86% on LLM costs

#### Quick start

```bash
pip install attune-ai
attune setup
```

**Learn more:** [Getting Started Guide](../getting-started/index.md)

---

### What are the "5 Levels of Empathy"?

The framework defines five levels of AI-human collaboration:

1. **Level 1 (Reactive):** Responds only when asked
2. **Level 2 (Guided):** Asks clarifying questions
3. **Level 3 (Proactive):** Notices patterns, offers improvements
4. **Level 4 (Anticipatory):** Predicts problems before they happen
5. **Level 5 (Transformative):** Reshapes workflows to prevent problem classes

**Learn more:** Five Levels of Empathy Guide (15,000 words with real examples)

---

## Teaching AI Your Standards

### How do I teach AI my coding standards?

Instead of repeating standards in every session, create a project-level standards file with real code examples.

**Step 1:** Create a standards reference file (`.ai/python-standards.md` or similar)

**Step 2:** Document patterns with examples:

```python
## Security: Never Use eval()

### ❌ Prohibited
user_input = request.get("formula")
result = eval(user_input)  # Code injection vulnerability!

### ✅ Required
import ast
try:
    data = ast.literal_eval(user_input)
except (ValueError, SyntaxError) as e:
    raise ValueError(f"Invalid input: {e}")

**Why:** eval() enables arbitrary code execution
**Exception:** None. Always use ast.literal_eval() or json.loads()
```

**Step 3:** Add to project context:

- Claude Code: `.claude/CLAUDE.md`
- GitHub Copilot: `.github/copilot-instructions.md`
- Cursor: `.cursorrules`

**Learn more:** Teaching AI Your Standards (11,000 words)

---

### What's the difference between prompting and project memory?

#### Traditional prompting

- Include instructions in every prompt
- Consumes context window
- Need to repeat every session
- Example: "Use type hints. Validate paths. [Your question]"

#### Project memory

- Standards loaded once at session start
- Available on-demand
- Persists across all sessions
- Zero context window cost
- Example: Just ask your question, AI knows standards

#### Think of it like

- Prompting = telling someone the rules every time
- Project memory = giving them a handbook once

---

### Can you share an example standards file?

Yes! Our production standards file is available:

**Location:** `.claude/rules-tail/attune/coding-standards-index.md`

#### Contents

- Security rules (eval, path validation, SQL injection)
- Exception handling patterns
- File operations
- Testing requirements
- Pre-commit hook configurations
- Real code examples from production

**Size:** ~1,170 lines with real patterns

**How to use:** Adapt for your team's needs, your language, your patterns

---

### How much time does this save?

#### Our measured results (30 days)

#### Before

- 47% of code review comments were standards violations
- 12 linter violations per PR average
- ~2 hours/week explaining standards

#### After

- 18% of code review comments are standards violations (-62%)
- 3 linter violations per PR average (-75%)
- ~20 min/week on standards questions (-83%)
- 0 security issues caught in review (all prevented at source)

**Time saved:** ~80 hours/month in code review

#### Your results will vary based on

- Team size (solo: 10-20h/month, team of 5+: 100+h/month)
- Current code review burden
- How often you repeat standards

---

## Tool Compatibility

### Does this work with GitHub Copilot?

Yes! GitHub Copilot supports project-level instructions.

#### Setup

1. Create `.github/copilot-instructions.md` in your repository
2. Add your coding standards with examples
3. Copilot reads it automatically

#### Example

```markdown
# Python Coding Standards

Follow the patterns in .ai/python-standards.md

Always:
- Use type hints
- Validate file paths before operations
- Catch specific exceptions
- Use ast.literal_eval() instead of eval()
```

**Learn more:** [GitHub Copilot Documentation](https://docs.github.com/en/copilot)

---

### Does this work with Cursor?

Yes! Cursor supports project rules via `.cursorrules` file.

#### Setup

1. Create `.cursorrules` in project root
2. Add your standards
3. Cursor applies them automatically

#### Example

```text
Follow Python standards in .ai/python-standards.md
Use type hints, validate file paths, catch specific exceptions
```

**Learn more:** [Cursor Documentation](https://docs.cursor.sh)

---

### Does this work with Claude Code?

Yes! Claude Code has native support for project memory.

#### Setup

1. Create `.claude/CLAUDE.md` in your project
2. Reference standards with `@./path/to/standards.md`
3. Claude loads them at session start

#### Example

```markdown
# Project Context

## Python Standards
@./python-standards.md

Critical rules:
- Never use eval() or exec()
- Validate all file paths
- Use specific exceptions
```

**Learn more:** [Claude Code Documentation](https://docs.anthropic.com/claude/docs)

---

### Does this work with ChatGPT?

Not yet. ChatGPT doesn't currently support persistent project-level context. You would need to include standards in each conversation.

#### Alternatives

- Create a custom GPT with standards in instructions
- Use a browser extension to inject standards
- Copy/paste standards at conversation start

---

## Implementation

### How long does setup take?

**Initial setup:** 4-8 hours

- Identify top 5-10 coding standard violations (1-2 hours)
- Document with real code examples (2-4 hours)
- Write actual implementation functions (1-2 hours)
- Add to project context (30 minutes)

**Maintenance:** ~1 hour/month

- Update when standards change
- Add new patterns as discovered
- Keep examples current

**ROI:** Pays back in first week for teams with regular code reviews

---

### What should I document first?

Start with your **top 5 coding standard violations**:

1. Look at last 10 code reviews
2. What do you keep commenting about?
3. Document those patterns first

#### Common starting points

- Security: eval(), path validation, SQL injection
- Type hints / type checking
- Exception handling (specific vs bare)
- File operations (context managers, validation)
- Logging patterns

**Don't try to document everything at once.** Start small, add patterns as you encounter them.

---

### Should I use abstract rules or real code?

**Always use real code examples**, not abstract descriptions.

#### Bad (abstract)

```text
Always handle errors properly
Use best practices
Follow team conventions
```

#### Good (concrete)

```python
## Error Handling: Catch Specific Exceptions

### ❌ Prohibited
try:
    risky_operation()
except:  # Masks KeyboardInterrupt, SystemExit
    pass

### ✅ Required
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except IOError as e:
    logger.warning(f"IO error: {e}")
    return default_value

**Why:** Bare except catches system signals, makes debugging impossible
```

#### Include

- ❌ What NOT to do (with code example)
- ✅ What TO do instead (with code example)
- **Why** it matters (security? performance? maintainability?)
- Your actual implementation (show the function from your codebase)

---

### How do I adapt this for TypeScript?

The pattern works for any language. Here's TypeScript example:

```typescript
// .ai/typescript-standards.md

## Error Handling: Custom Error Classes

### ❌ Prohibited
if (!user) {
  throw new Error("User not found");
}

### ✅ Required
export class UserNotFoundError extends Error {
  constructor(userId: string) {
    super(`User not found: ${userId}`);
    this.name = 'UserNotFoundError';
  }
}

if (!user) {
  throw new UserNotFoundError(userId);
}

// Usage in try-catch
try {
  const user = await getUser(id);
} catch (error) {
  if (error instanceof UserNotFoundError) {
    return res.status(404).json({ error: error.message });
  }
  throw error; // Re-throw unexpected errors
}

**Why:** Type-safe error handling, better logging, clearer debugging
```

**Add to:** `.github/copilot-instructions.md` or `.cursorrules`

---

### How do I keep standards updated?

#### Integrate with code review process

1. **When code review finds violation:**
   - Fix the code
   - Add pattern to standards file
   - Show ❌ bad pattern (what was just fixed)
   - Show ✅ good pattern (what to do instead)
   - Explain why

2. **Time investment:** ~10 minutes per violation

3. **Result:** Pattern doesn't repeat

#### Example workflow

```text
Code review finds: bare except:
→ Fix it: catch ValueError specifically
→ Add to standards file (takes 10 min)
→ AI generates correct pattern next time
→ Never see that violation again
```

**Pro tip:** Make updating standards part of your review checklist.

---

## Cost Optimization

### What is intelligent tier fallback?

Automatic cost optimization that tries cheaper tiers first and only upgrades when quality gates fail.

#### How it works

1. Start with CHEAP tier (Haiku - $0.03/1M tokens)
2. Validate output with quality gates
3. If validation fails → upgrade to CAPABLE (Sonnet 4.6)
4. Still failing? → upgrade to PREMIUM (Opus 4.8)
5. Track savings and learn from patterns

#### Enable it

```bash
attune workflow run health-check --use-recommended-tier
```

**Expected savings:** 30-50% on average workflow execution

**Learn more:** CHANGELOG.md v3.10.0

---

### When should I use tier fallback?

#### When to use tier fallback

- Cost is a primary concern
- Workflow has measurable quality metrics (health score, test coverage)
- CHEAP tier often succeeds (simple refactoring, docs, health checks)
- You can tolerate 2-3x latency increase on quality failures
- You want automatic cost optimization

#### When NOT to use tier fallback

- Time is critical (tier upgrades add latency)
- Quality gates are hard to define
- PREMIUM tier is always required (complex reasoning, novel problems)
- You prefer predictable performance over cost savings

**Best for:** health-check, test-gen, doc-gen, refactoring workflows

**Not ideal for:** complex debugging, architecture design, novel feature implementation

---

### How much can I save with tier fallback?

#### Real savings depend on your workflow success rates

#### Scenario 1: CHEAP often succeeds (60% of stages)

- Both stages succeed at CHEAP: **~90% savings** vs. all-PREMIUM
- Typical result: **60-70% overall savings**

#### Scenario 2: Mixed success (40% CHEAP, 40% CAPABLE, 20% PREMIUM)

- Real-world mix: **40-50% savings** vs. all-PREMIUM

#### Scenario 3: CHEAP rarely succeeds (20% of stages)

- Most stages need CAPABLE or PREMIUM: **10-20% savings**
- May not be worth the latency cost

#### Track your actual savings

```bash
attune telemetry savings --days 30
```

**See detailed breakdown:** TIER_FALLBACK_TEST_REPORT.md

---

### What are quality gates?

#### Quality gates defined

**Default quality gates** (all workflows):

- ✅ Execution succeeded (no exceptions)
- ✅ Output is not empty
- ✅ No error keys in response

**Workflow-specific gates** (health-check):

- ✅ Health score ≥ 95 (configurable with `--health-score-threshold`)
- ✅ Diagnosis data present
- ✅ Required fields populated

**Custom quality gates:** Override `validate_output()` in your workflow:

```python
def validate_output(self, stage_output: dict) -> tuple[bool, str | None]:
    # Custom validation logic
    if stage_output.get("confidence", 0) < 0.8:
        return False, "confidence_too_low"
    return True, None
```

**See code:** `src/attune/workflows/base.py:156-187`

---

### Can I customize the tier fallback behavior?

#### Customization options

#### 1. Change the starting threshold

```bash
attune workflow run health-check --use-recommended-tier --health-score-threshold 90
```

#### 2. Use Python API for full control

```python
from attune.workflows import get_workflow

workflow_cls = get_workflow("health-check")
workflow = workflow_cls(
    provider="anthropic",
    enable_tier_fallback=True,
    health_score_threshold=95,  # Custom threshold
)

result = await workflow.execute(path=".")
```

#### 3. Create custom workflows with specific quality gates

```python
class MyWorkflow(BaseWorkflow):
    def validate_output(self, stage_output: dict) -> tuple[bool, str | None]:
        # Your custom validation logic
        pass
```

**See examples:** CHANGELOG.md Migration Guide

---

### Is tier fallback production-ready?

**Yes!** Fully tested and validated:

- ✅ **8/8 unit tests passing** (100%)
- ✅ **89% code coverage** on tier_tracking module
- ✅ **Zero lint errors, zero type errors**
- ✅ **Comprehensive error handling**
- ✅ **Backward compatible** (opt-in, default behavior unchanged)
- ✅ **Full telemetry tracking**

#### Deployment checklist completed

- ✅ All unit tests pass
- ✅ Code coverage ≥80% on critical modules
- ✅ Documentation updated
- ✅ CHANGELOG.md entry added
- ✅ Migration guide available

**See full validation:** TIER_FALLBACK_TEST_REPORT.md

---

## Results & ROI

### What results can I expect?

#### Conservative estimates (based on our data)

#### Solo developer

- Time saved: 10-20 hours/month
- Code review improvements: -40% standards comments
- Prevention: 2-3 bugs caught before writing

#### Team of 5

- Time saved: 50-100 hours/month
- Code review improvements: -60% standards comments
- Prevention: 5-10 bugs caught before writing

#### Team of 10+

- Time saved: 100-200 hours/month
- Code review improvements: -70% standards comments
- Prevention: 10-20 bugs caught before writing

#### Key factors

- Current code review burden
- How often you repeat standards
- Team size and turnover
- Codebase complexity

---

### How do I measure impact?

#### Track these metrics for 30 days

#### Before implementation

- % of code review comments on standards
- Linter violations per PR
- Time spent explaining standards
- Security issues caught in review

#### After implementation

- Same metrics
- Calculate reduction
- Note patterns that stopped recurring

#### Example tracking

```text
Week 1: 15 linter violations, 12 standards comments
Week 2: 12 linter violations, 9 standards comments
Week 3: 8 linter violations, 6 standards comments
Week 4: 5 linter violations, 4 standards comments

Result: -67% violations, -67% comments
```

---

## Common Concerns

### Isn't this overengineered?

#### It depends on your situation

#### When this is overkill

- Solo dev who rarely repeats standards
- Small team with perfect code review adherence
- Simple codebase with few patterns
- No security requirements

#### When this pays off

- Team of 3+ developers
- Onboarding new developers regularly
- Recurring standards violations in code review
- Complex codebase with security requirements
- High cost of bugs (security, compliance, $$$)

#### The lightweight version

- Document top 3 violations only
- Skip the rest
- Still saves time, much less work

**Our take:** If you find yourself repeating the same code review comment 5+ times, document it.

---

### Does AI replace code review?

#### This complements code review, doesn't replace it

#### What it does

- Reduces noise (fewer "use type hints" comments)
- Lets reviewers focus on logic, architecture, edge cases
- Prevents obvious issues

#### What it doesn't do

- Replace human judgment
- Catch business logic bugs
- Understand context-specific requirements
- Make architectural decisions

#### Think of it like a linter on steroids

- Linters catch syntax issues
- This catches patterns linters can't detect
- Humans focus on the hard problems

**You still need code review** - just less time on repetitive standards enforcement.

---

### What about AI hallucinations?

#### How we handle it

#### 1. Reference actual implementations

```python
## File Path Validation

### Our Implementation: src/utils/validation.py:15-40

[Paste actual function from your codebase]
```

When AI uses `validate_file_path()`, it's using a tested, production function, not generating something new.

#### 2. Include test patterns

```python
## Tests Required

def test_validate_file_path_blocks_traversal():
    with pytest.raises(ValueError):
        validate_file_path("../../etc/passwd")
```

AI generates tests that match your existing test suite.

#### 3. Code review still catches issues

- AI-generated code goes through normal review
- Standards reduce noise, but humans verify logic

#### 4. Start with high-confidence patterns

- Security rules (eval, path validation)
- Well-established best practices
- Patterns you've used 100+ times

---

### What if my team disagrees on standards?

#### Document the disagreement and decision

```python
## String Formatting: Use f-strings (Python 3.6+)

### ❌ Prohibited
name = "Alice"
message = "Hello, %s" % name  # Old style
message = "Hello, {}".format(name)  # Verbose

### ✅ Required
message = f"Hello, {name}"  # Readable, fast

**Team decision (2024-03-15):**
- Discussed .format() vs f-strings
- Chose f-strings for readability
- Exception: When string is reused with different values
- Documented in standards for new team members
```

#### Benefits

- New team members see the decision
- Context preserved ("why did we choose this?")
- Reduces re-litigating decisions
- Standards document becomes team memory

---

## Wizards

### What are wizards?

Wizards are guided, multi-step AI workflows that walk you through complex tasks like debugging, security audits, refactoring, and test generation. Each wizard collects context, runs AI analysis, decomposes work into tasks, and previews results before acting.

#### Built-in wizards

| ID | Name | Use Case |
| ---- | ------ | ---------- |
| `debug` | Debugging Wizard | Investigating errors, finding root causes |
| `test-gen` | Test Generation Wizard | Creating tests for untested code |
| `refactor` | Refactoring Wizard | Planning safe, incremental refactoring |
| `security` | Security Audit Wizard | Scanning for vulnerabilities |
| `release-prep` | Release Preparation Wizard | Pre-release readiness checks |

**Quick start:** `/wizard run debug` in Claude Code, or see the [Getting Started guide](../guides/wizards-getting-started.md).

---

### How do I create a custom wizard?

Two approaches:

**YAML (no Python required):** Create a `.attune/wizards/my-wizard.yaml` file with step definitions. See [Getting Started](../guides/wizards-getting-started.md).

**Python (for advanced logic):** Subclass `BaseWizard` with custom step handling, workflow delegation, and conditional steps. See Custom Wizard Development.

---

### How does the wizard system work internally?

Wizards follow a step-based execution model with 5 step types: QUESTION, LLM_CALL, TASK_DECOMPOSE, PREVIEW, and CONFIRM. Session state flows between steps, and conditions can skip steps dynamically.

Production wizards delegate LLM steps to multi-stage workflow engines for deeper analysis, with graceful fallback to basic LLM calls.

**Deep dive:** [Wizard Architecture](../guides/wizard-architecture.md)

---

## Advanced Topics

### Can I share standards across multiple projects?

Yes! Use symlinks or git submodules:

```text
company-standards/
├── python-standards.md
├── typescript-standards.md
└── security-baseline.md

project-a/
├── .claude/CLAUDE.md
│   # References: @../company-standards/python-standards.md
└── src/

project-b/
├── .claude/CLAUDE.md
│   # References: @../company-standards/python-standards.md
└── src/
```

#### Benefits

- Update once, applies everywhere
- Consistent standards across org
- New projects inherit standards automatically

---

### How do I handle language-specific vs general standards?

#### Structure by specificity

```text
standards/
├── general.md              # Applies to all projects
│   ├── Code review process
│   ├── Git commit format
│   └── Documentation requirements
├── security-baseline.md    # Applies to all code
│   ├── Never use eval()
│   ├── Validate all inputs
│   └── Authentication patterns
└── python/
    ├── security.md         # Python-specific security
    ├── testing.md          # Python testing patterns
    └── style.md            # Python style guide
```

#### Reference in project

```markdown
# .claude/CLAUDE.md

@../standards/general.md
@../standards/security-baseline.md
@../standards/python/security.md
@../standards/python/testing.md
```

---

### Can I use this for data science workflows?

Absolutely! Example patterns:

```python
## Data Validation: Check DataFrame Schema

### ❌ Prohibited
result = df['column_name']  # KeyError if missing

### ✅ Required
def validate_dataframe(df: pd.DataFrame, required_cols: list[str]):
    """Validate DataFrame has required columns."""
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

validate_dataframe(df, ['user_id', 'timestamp', 'value'])
result = df['column_name']

**Tests:**
- Missing column handling
- Type validation (int vs float)
- NaN/null handling
```

#### Other DS patterns

- Data validation (schema, types, ranges)
- Reproducibility (random seeds, versioning)
- Performance (vectorization, avoid loops)
- Visualization (consistent styling, labels)

---

### How do I version control standards?

#### Treat standards like code

```bash
git add .claude/rules/python-standards.md
git commit -m "docs: Add SQL injection prevention pattern"
git push
```

#### Use CHANGELOG

```markdown
# Standards Changelog

## 2026-01-07
- Added: SQL injection prevention pattern
- Updated: Exception handling (added cleanup pattern)
- Removed: Deprecated string formatting rules

## 2025-12-15
- Added: Path validation for file operations
- Updated: Type hints (Python 3.10 syntax)
```

#### Benefits

- Track what changed and when
- See evolution of standards
- Revert if pattern doesn't work
- Team sees updates in pull requests

---

## Still Have Questions?

### Resources

- **Getting Started:** [Getting Started Guide](../getting-started/index.md)
- **Five Levels:** Five Levels of Empathy Guide
- **Teaching AI:** Teaching AI Your Standards
- **Coding Standards:** [Our Standards Reference](../CODING_STANDARDS.md)

### Community

- **GitHub Issues:** [Report bugs or request features](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **GitHub Discussions:** [Ask questions, share ideas](https://github.com/Smart-AI-Memory/attune-ai/discussions)
- **Twitter:** [@your_handle] - Follow for updates

### Commercial Support

- **Email:** <admin@smartaimemory.com>
- **Website:** <https://smartaimemory.com>

---

**Contributing:** Found an error or have a question not covered here? [Open an issue](https://github.com/Smart-AI-Memory/attune-ai/issues) or [start a discussion](https://github.com/Smart-AI-Memory/attune-ai/discussions).

**Last Updated:** February 20, 2026
