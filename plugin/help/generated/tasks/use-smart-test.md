---
type: task
name: use-smart-test
tags: [skill, task]
source: plugin/skills/smart-test/SKILL.md
---

# Task: Use the smart-test skill

Find test gaps and generate tests for uncovered code. Triggers on: generate tests, write tests, test coverage, find untested code, test gaps, smart test, what needs testing.

Invoke with: `/smart-test <path or module to test>`

## Steps

1. **Define target**
   "Which file or module needs tests?"

2. **Define approach**
   "What kind of testing?" - Gap analysis — Find untested public functions - Generate tests — Write pytest tests for a module - Both — Audit gaps then generate tests for them

3. **Run the tool**
   For gap analysis: For targeted test generation: For batch generation across many modules:

   ```
   test_audit(path="<target>")
   ```

4. **Run tool (option 2)**

   ```
   test_generation(module="<target module>")
   ```

5. **Run tool (option 3)**

   ```
   test_gen_parallel(top=10)
   ```

6. **Choose follow-up action**
   Want me to generate tests for the top gaps?; Should I run the generated tests to verify?; Want to see coverage for a different module?


## Related Topics
- **Reference**: Skill: smart-test — full reference
