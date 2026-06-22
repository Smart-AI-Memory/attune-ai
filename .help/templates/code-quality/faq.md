---
type: faq
feature: code-quality
depth: faq
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Code Quality FAQ

## What is code quality review?

A unified analysis that checks your code for style violations, correctness issues, likely bugs, and structural problems in a single pass with a scored report.

## When should I run a code quality review?

Before opening pull requests, after large refactors, when inheriting unfamiliar code, or any time you want a health score for your codebase.

## How do I start a review?

Use `/code-quality <path>` to review specific files or directories, or just say "review src/" in natural language. You'll get guided through scope and depth questions if needed.

## What's the difference between quick, standard, and deep reviews?

Quick scans only style and formatting (seconds), standard adds logic errors and likely bugs (~1 minute), and deep includes security and architecture analysis (~3 minutes). Standard is the default.

## What do the health scores mean?

90-100 is excellent (ship it), 75-89 is good (fix before merge), 50-74 needs work (prioritize fixes), and 0-49 is poor (stop and address major problems).

## Can I fix issues automatically?

Some style issues like unused imports can be auto-fixed by saying "fix the quality issues" after getting results. Structural and logic problems require manual attention.

## How do I focus on specific types of issues?

After getting results, say "just show me the likely bugs" or "focus on security issues" to drill down into specific categories.

## What if I want to compare different parts of my code?

Ask "compare quality of src/auth/ vs src/api/" to get a side-by-side analysis showing which area needs more attention.

## Where can I learn more?

Say "tell me more" for complete step-by-step instructions, or check the related quickstart and task guides for this feature.

**Tags:** `review`, `quality`, `bugs`
