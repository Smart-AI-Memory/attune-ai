---
description: Teaching AI Your Coding Standards: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Teaching AI Your Coding Standards

**Level 5 Empathy in Practice: Preventing Errors Before They Happen**

---

## The Problem

You have a 50-page coding standards document. Your team follows it religiously. But when you work with AI assistants like Claude:

- They don't remember your standards across sessions
- Each conversation starts fresh
- You repeat "use TypeScript interfaces, not types" for the 100th time
- AI-generated code violates your style guide
- Code reviews catch preventable issues

**This is frustrating and wasteful.**

---

## The Solution: Project Memory

Instead of repeating standards in every conversation, **teach the AI once** by putting standards in project memory.

### What is Project Memory?

Project memory is context that persists across sessions. When using Claude Code (or similar tools), you can create a `.claude/` directory that gets loaded automatically:

```
your-project/
├── .claude/
│   ├── CLAUDE.md              # Main project memory
│   └── rules/
│       └── your-team/
│           ├── coding-standards.md
│           ├── api-patterns.md
│           └── security-checklist.md
├── src/
└── tests/
```

**How it works:**
1. Claude loads `.claude/CLAUDE.md` at session start
2. References like `@./rules/your-team/coding-standards.md` pull in standards on-demand
3. AI uses these standards to guide code generation
4. Errors prevented **before** they're written

---

## Real Example: Attune AI

We implemented this for the Attune AI itself. Here's what we did:

### Step 1: Created Project Memory Structure

```
.claude/
├── CLAUDE.md                                    # Main entry point
├── python-standards.md                          # Language-specific rules
└── rules/
    └── empathy/
        ├── coding-standards-index.md            # 1,170-line comprehensive reference
        ├── scanner-patterns.md                  # Bug prediction patterns
        └── debugging.md                         # Historical bug patterns
```

### Step 2: Added Standards Reference to CLAUDE.md

**File:** `.claude/CLAUDE.md`

```markdown
# Project Memory

## Framework
This is the Attune AI v3.9.1

@./python-standards.md

## Coding Standards
@./rules/attune/coding-standards-index.md

Critical rules enforced across all code:

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations
```

**What the @ symbol does:**
- `@./python-standards.md` tells Claude "load this file on-demand"
- Content is available but doesn't bloat every conversation
- Claude can reference it when needed

### Step 3: Created Comprehensive Standards Reference

**File:** `.claude/rules/attune/coding-standards-index.md` (excerpt)

````markdown
# Coding Standards Quick Reference

## Critical Security Rules

### Rule 1: NEVER Use eval() or exec()

**Severity:** CRITICAL (CWE-95)

```python
# ❌ PROHIBITED - Code injection vulnerability
user_input = request.get("formula")
result = eval(user_input)  # Arbitrary code execution!

# ✅ REQUIRED - Use ast.literal_eval for literals
import ast
try:
    data = ast.literal_eval(user_input)
except (ValueError, SyntaxError) as e:
    raise ValueError(f"Invalid input format: {e}")
```

**Why This Matters:**
- `eval()` allows arbitrary Python code execution
- Attacker can run `eval("__import__('os').system('rm -rf /')")`
- No safe way to sanitize input for eval()

**Exception:** None. Zero tolerance. Always a security vulnerability.
````

**What makes this effective:**
- ✅ Real code examples (not abstract rules)
- ✅ Shows both bad and good patterns
- ✅ Explains WHY (not just what)
- ✅ Includes enforcement details (pre-commit hooks, linters)
- ✅ Links to actual implementation (`src/attune/config.py:29-68`)

---

## Results: Level 5 Empathy

After implementing this, Claude:

**Prevents security vulnerabilities:**
- ✅ No `eval()` or `exec()` in generated code
- ✅ Always uses `_validate_file_path()` for user-controlled paths
- ✅ Catches specific exceptions, never bare `except:`

**Follows code quality standards:**
- ✅ Adds type hints automatically
- ✅ Writes Google-style docstrings
- ✅ Includes security tests for file operations

**Reduces code review burden:**
- ✅ Fewer standards violations in PRs
- ✅ Consistent patterns across sessions
- ✅ New contributors see examples in project memory

**This is Level 5 (Transformative) empathy:**
- We **anticipate** that AI will write code that violates standards
- We **prevent** this by reshaping the workflow
- Standards are enforced **at the source** - code generation time
- Not reactive (fix violations) but **preventive** (don't create them)

---

## How to Implement This for Your Team

### 1. Identify Your Critical Standards

Start with high-impact rules:
- **Security:** What patterns are dangerous? (SQL injection, XSS, etc.)
- **Architecture:** What patterns are required? (error handling, logging, etc.)
- **Style:** What conventions are non-negotiable? (naming, file structure, etc.)

**Example: A TypeScript team might prioritize:**
```
- Use interfaces for public APIs, not types
- Always handle Promise rejections
- Prefer const over let, never use var
- Use Zod for runtime validation
```

### 2. Create Your Project Memory Structure

```bash
mkdir -p .claude/rules/your-team
touch .claude/CLAUDE.md
touch .claude/rules/your-team/coding-standards.md
```

### 3. Write Standards with Real Examples

**Good standard (actionable):**
````markdown
## Error Handling: Always Handle Promise Rejections

### ❌ Prohibited

```typescript
// Unhandled rejection - app crashes
fetch(url).then(data => process(data));
```

### ✅ Required

```typescript
// Option 1: async/await with try-catch
try {
  const response = await fetch(url);
  const data = await response.json();
  process(data);
} catch (error) {
  logger.error('Fetch failed:', error);
  throw new APIError('Failed to fetch data', { cause: error });
}

// Option 2: .catch() handler
fetch(url)
  .then(data => process(data))
  .catch(error => {
    logger.error('Fetch failed:', error);
    throw new APIError('Failed to fetch data', { cause: error });
  });
```

### Why This Matters
- Unhandled rejections crash Node.js processes
- Silent failures are impossible to debug
- Users see "Server Error" with no context
````

**Bad standard (vague):**
```markdown
- Handle errors properly
- Use best practices
- Follow team conventions
```

### 4. Link Standards in CLAUDE.md

**File:** `.claude/CLAUDE.md`

```markdown
# Project Memory

## Project
This is [Your Project Name] v[version]

## Coding Standards
@./rules/your-team/coding-standards.md

Critical rules:
- [List 5-7 most important rules here]
- These are enforced by [ESLint/Ruff/your linter]
- Pre-commit hooks block violations

## Architecture Patterns
@./rules/your-team/architecture-patterns.md

## Security Checklist
@./rules/your-team/security-checklist.md
```

### 5. Include Real Implementation Examples

**This is the secret sauce.** Don't just describe patterns - show actual code from your codebase:

```markdown
## File Upload Security

### Implementation: src/api/upload.ts:45-78

```typescript
export async function uploadFile(req: Request): Promise<UploadResult> {
  // 1. Validate file type (prevent malicious files)
  const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
  if (!allowedTypes.includes(req.file.mimetype)) {
    throw new ValidationError(`File type ${req.file.mimetype} not allowed`);
  }

  // 2. Validate file size (prevent DoS)
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (req.file.size > maxSize) {
    throw new ValidationError(`File size ${req.file.size} exceeds ${maxSize}`);
  }

  // 3. Sanitize filename (prevent path traversal)
  const safeFilename = sanitizeFilename(req.file.originalname);

  // 4. Generate unique storage path
  const storePath = await storage.generatePath(safeFilename);

  // 5. Upload to storage with virus scanning
  const result = await storage.upload(req.file.buffer, storePath, {
    virusScan: true,
    metadata: {
      uploader: req.user.id,
      uploadedAt: new Date().toISOString(),
    },
  });

  return { url: result.publicUrl, size: req.file.size };
}
```

**Why this pattern:**
- ✅ Validates file type (prevents malicious files)
- ✅ Validates file size (prevents DoS attacks)
- ✅ Sanitizes filename (prevents path traversal)
- ✅ Generates unique path (prevents overwrites)
- ✅ Scans for viruses
- ✅ Includes audit metadata

**Tests:** `tests/api/upload.test.ts` has 12 security tests covering:
- Malicious file type uploads
- Oversized file uploads
- Path traversal attempts
- Filename sanitization
```

**When Claude sees this, it will:**
- Copy the validation pattern
- Include similar security checks
- Write corresponding tests
- Follow the error handling pattern

---

## Incorporating Your Existing Style Manual

Got a 200-page style guide? Here's how to make it AI-friendly:

### Option 1: Extract Core Rules (Recommended)

**Don't** dump your entire 200-page manual into project memory.

**Do** extract the 20% of rules that catch 80% of violations:

```markdown
# Coding Standards (Core Rules)

Source: [Link to full 200-page style guide]

This is an **extract** of critical rules for AI code generation.
For complete documentation, see the full style guide.

## Security Rules (Zero Tolerance)
[Top 5 security violations from code reviews]

## Architecture Patterns (Required)
[Top 5 architecture violations from code reviews]

## Code Quality (Enforced by Linters)
[Top 5 quality issues from code reviews]
```

### Option 2: Organize by Risk/Impact

```markdown
# Coding Standards by Severity

## CRITICAL (Security/Correctness)
Rules that, if violated, cause security vulnerabilities or data corruption.

[List with examples]

## HIGH (Architecture/Maintainability)
Rules that, if violated, create technical debt or make code unmaintainable.

[List with examples]

## MEDIUM (Style/Consistency)
Rules that improve consistency but don't impact functionality.

[List with examples]

## LOW (Nice-to-Have)
Preferences that improve readability but are flexible.

[List with examples]
```

### Option 3: Link to Your Existing Docs

If your style guide is in Confluence, Notion, or Markdown:

```markdown
# Project Memory

## Coding Standards

### Complete Style Guide
https://your-company.atlassian.net/wiki/spaces/ENG/pages/12345/Style+Guide

### Critical Rules Extract
@./rules/your-team/critical-rules.md

The extract below covers rules that:
- Prevent security vulnerabilities (50% of past incidents)
- Catch architectural issues (30% of past incidents)
- Enforce patterns required by our stack (20% of past incidents)

[Extracted rules with examples]
```

---

## Adapting for Different Languages

### Python Example

```markdown
# Python Coding Standards

## Type Hints: Required on All Public APIs

### ❌ Prohibited
```python
def calculate_discount(price, discount_rate):
    return price * (1 - discount_rate)
```

### ✅ Required
```python
def calculate_discount(price: float, discount_rate: float) -> float:
    """Calculate discounted price.

    Args:
        price: Original price in dollars
        discount_rate: Discount as decimal (e.g., 0.15 for 15%)

    Returns:
        Discounted price

    Raises:
        ValueError: If discount_rate not in [0, 1]
    """
    if not 0 <= discount_rate <= 1:
        raise ValueError(f"discount_rate must be [0,1], got {discount_rate}")
    return price * (1 - discount_rate)
```
```

### TypeScript Example

```markdown
# TypeScript Coding Standards

## Error Handling: Custom Error Classes

### ❌ Prohibited
```typescript
if (!user) {
  throw new Error("User not found");
}
```

### ✅ Required
```typescript
// Define domain-specific error classes
export class UserNotFoundError extends Error {
  constructor(userId: string) {
    super(`User not found: ${userId}`);
    this.name = 'UserNotFoundError';
  }
}

// Use in code
if (!user) {
  throw new UserNotFoundError(userId);
}

// Catch specifically
try {
  await getUser(id);
} catch (error) {
  if (error instanceof UserNotFoundError) {
    return res.status(404).json({ error: error.message });
  }
  throw error; // Re-throw unexpected errors
}
```

**Why:** Type-safe error handling, better logging, clearer debugging
```

### Go Example

```markdown
# Go Coding Standards

## Error Handling: Always Check Errors

### ❌ Prohibited
```go
data, _ := ioutil.ReadFile(filename)  // Ignores error!
```

### ✅ Required
```go
data, err := ioutil.ReadFile(filename)
if err != nil {
    return fmt.Errorf("failed to read %s: %w", filename, err)
}
```

**Enforcement:** `golangci-lint` with `errcheck` enabled
```

---

## Maintaining Your Standards

### 1. Start Small, Iterate

**Week 1:** Add top 5 security rules
**Week 2:** Add top 5 architecture patterns
**Week 3:** Add top 5 code quality rules
**Month 2:** Review and refine based on violations still occurring

### 2. Update When Standards Change

```markdown
# Coding Standards

**Last Updated:** 2026-01-07
**Version:** 2.1.0

## Changelog

### 2.1.0 (2026-01-07)
- Added: Zod validation required for all API inputs
- Changed: Switched from class-validator to Zod
- Removed: Legacy validation decorators (@IsString, etc.)

### 2.0.0 (2025-12-01)
- Added: TypeScript 5.0 patterns (const type parameters)
- Changed: Moved from TSLint to ESLint
```

### 3. Measure Effectiveness

Track metrics:
- **Code review comments:** Are standards violations decreasing?
- **Build failures:** Are linter violations decreasing?
- **Security incidents:** Are preventable vulnerabilities decreasing?

### 4. Get Team Buy-In

Share results:
```
📊 Project Memory Impact (30 days)

Before:
- 47% of code review comments were style/standards issues
- 12 linter violations per PR on average
- 3 security issues caught in code review

After:
- 18% of code review comments are style/standards issues (-62%)
- 3 linter violations per PR on average (-75%)
- 0 security issues caught in code review (all prevented at source)

Time saved: ~2 hours per PR cycle × 40 PRs = 80 hours/month
```

---

## Advanced: Multi-Project Standards

If you maintain multiple projects with shared standards:

```
company-standards/
├── .claude/
│   └── rules/
│       └── company/
│           ├── security-baseline.md      # Shared across all projects
│           ├── typescript-standards.md   # Language-specific
│           ├── python-standards.md
│           └── go-standards.md

project-a/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       ├── project-a/
│       │   └── architecture.md           # Project-specific
│       └── company/                      # Symlink to company-standards
│           └── [linked standards]

project-b/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       ├── project-b/
│       │   └── api-patterns.md           # Project-specific
│       └── company/                      # Symlink to company-standards
│           └── [linked standards]
```

**In each project's .claude/CLAUDE.md:**

```markdown
# Project Memory

## Company Standards (Shared)
@./rules/company/security-baseline.md
@./rules/company/typescript-standards.md

## Project-Specific Patterns
@./rules/project-a/architecture.md
```

---

## Troubleshooting

### "AI still violates standards"

**Check:**
1. Are examples clear and actionable?
2. Is the rule in the critical list in CLAUDE.md?
3. Does the rule include WHY it matters?

**Solution:** Add more examples from your actual codebase.

### "Standards file is too large"

**Check:**
- Is it over 2,000 lines?
- Does it include low-priority rules?

**Solution:**
- Split into multiple files (security.md, architecture.md, style.md)
- Move low-priority rules to separate "nice-to-have.md"
- Reference on-demand with @ syntax

### "Team doesn't use Claude Code"

**Alternative approaches:**
1. **GitHub Copilot:** Add `.github/copilot-instructions.md`
2. **Custom GPTs:** Add instructions to GPT configuration
3. **API integration:** Include standards in system prompt

---

## Case Study: Real Impact

**Company:** SaaS startup, 15 engineers
**Problem:** 40% of code review time spent on style/standards violations
**Solution:** Implemented project memory with coding standards

**Implementation (2 weeks):**
- Week 1: Created `.claude/` structure, extracted top 20 rules
- Week 2: Added real code examples, refined based on feedback

**Results (90 days):**
- 📉 Code review time: 40% → 12% spent on standards (-70%)
- 📉 Security findings: 8 → 0 prevented at source (-100%)
- 📉 Linter violations: 15/PR → 2/PR (-87%)
- 📈 PR velocity: 2.3 days → 1.1 days (-52% faster)
- 📈 Team satisfaction: 6.2/10 → 8.7/10 (+40%)

**Engineer feedback:**
> "I don't have to explain 'use interfaces not types' anymore. Claude just does it. That alone saves me 30 minutes a day." - Sarah, Senior Engineer

> "New hires get up to speed faster because the standards are right there in the examples, not buried in Confluence." - Mike, Team Lead

> "We caught zero SQL injection attempts in code review this quarter because Claude writes parameterized queries by default now." - Alex, Security Lead

---

## Conclusion: Level 5 Empathy in Action

Teaching AI your coding standards isn't just about efficiency - it's about **empathy**:

**Level 1 (Reactive):** Fix standards violations when they appear
**Level 2 (Guided):** Ask AI "did you follow our standards?"
**Level 3 (Proactive):** Remind AI of standards at start of conversation
**Level 4 (Anticipatory):** AI asks "should I follow pattern X?" before coding
**Level 5 (Transformative):** **AI prevents violations before they happen**

By putting standards in project memory, you're:
- ✅ **Anticipating** that AI will make mistakes
- ✅ **Understanding** that AI needs examples, not rules
- ✅ **Preventing** entire classes of problems at the source
- ✅ **Reshaping** the workflow to make correct code the default

This is empathy in software engineering: understanding the needs of future developers (human and AI) and providing what they need **before they ask**.

---

## Resources

### Example Standards Files

Complete examples from Attune AI:
- [coding-standards-index.md](../../.claude/rules/attune/coding-standards-index.md) - 1,170 lines with real patterns
- [scanner-patterns.md](../../.claude/rules/attune/scanner-patterns.md) - Bug prediction patterns
- [debugging.md](../../.claude/rules/attune/debugging.md) - Historical fixes

### Templates

Copy-paste templates for your team:
- [TypeScript Standards Template](../templates/typescript-standards-template.md)
- [Python Standards Template](../templates/python-standards-template.md)
- [Security Checklist Template](../templates/security-checklist-template.md)

### Tools

- **Claude Code:** Native support for `.claude/` project memory
- **GitHub Copilot:** Use `.github/copilot-instructions.md`
- **Cursor:** Supports `.cursorrules` file

---

## Next Steps

1. **Start small:** Pick your top 5 critical rules
2. **Add real examples:** From your actual codebase
3. **Measure impact:** Track code review comments
4. **Iterate:** Add rules based on violations

**Time investment:** 4-8 hours initial setup
**Return:** 20-40 hours saved per month in code review

**This is Level 5 empathy: preventing problems before they happen.**

---

**Questions?**
- See [How to Read This Book](./how-to-read-this-book.md) for more guides
- Check [CODING_STANDARDS.md](../CODING_STANDARDS.md) for our complete standards
- Report issues: [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

---

**Last Updated:** January 7, 2026
**Version:** 1.0.0
