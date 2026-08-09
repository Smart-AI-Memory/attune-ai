---
type: task
name: use-code-quality
tags: [skill, task]
source: plugin/skills/code-quality/SKILL.md
---

# Task: Use the code-quality skill

Code review to find quality issues, style violations, and code smells. Triggers on: review, code review, quality, lint, code smell, analyze code.

Invoke with: `/code-quality <path or directory to review>`

## Steps

1. **Define scope**
   "Which files or directory should I review?"

2. **Define depth**
   "Quick scan, thorough, or deep review?" - Quick: code_review only - Thorough: code_review + bug_predict combined - Deep: deep_review (security + quality + test gaps)

3. **Run the tool**
   **Quick scan:** **Thorough analysis:** Merge and deduplicate results from both tools. **Deep review** (multi-pass: security, quality, test gaps):

   ```
   code_review(path="<user-specified path>")
   ```

4. **Run tool (option 2)**

   ```
   code_review(path="<user-specified path>")
bug_predict(path="<user-specified path>")
   ```

5. **Run tool (option 3)**

   ```
   deep_review(path="<user-specified path>")
   ```

6. **Choose follow-up action**
   Want me to fix these issues?; Should I generate tests for the risky areas?; Want to run a security-focused deep scan?


## Related Topics
- **Reference**: Skill: code-quality — full reference
