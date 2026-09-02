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
   ### Shared command workspace (preferred)

   Open adapter `smart-test` with the validated target and `gap`, `generate`, or
   `both` approach. The bound audit action is read-only. Publish the actual audit
   as `audit_result`, including exact proposed test paths before any generator is
   called. Present the proposal widget or Markdown; only an explicitly confirmed
   `generate_tests` action authorizes those paths.

   After `test_generation`, publish `generation_result` with the exact files
   reported from disk. The adapter independently hashes those files and rejects
   writes outside or different from the approved set. Run the returned test
   probe and publish its exact command and exit code as `validation_result`.
   Generator or test failure must say “did not complete” and retain the written
   paths for rollback; it may not claim tests were created successfully. Preserve
   the same preview/write/validation gates in compact text when the shared tools
   are unavailable.

   For gap analysis:

   ```
   test_audit(path="<target>")
   ```

4. **Run tool (option 2)**
   For targeted test generation:

   ```
   test_generation(module="<target module>")
   ```

5. **Run tool (option 3)**
   For batch generation across many modules:

   ```
   test_gen_parallel(top=10)
   ```

6. **Choose follow-up action**
   Want me to generate tests for the top gaps?; Should I run the generated tests to verify?; Want to see coverage for a different module?


## Related Topics
- **Reference**: Skill: smart-test — full reference
