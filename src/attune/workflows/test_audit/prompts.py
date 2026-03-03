"""Prompt templates for TestAuditWorkflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

AUDIT_SYSTEM_PROMPT = """\
You are a test coverage analyst. You have been given a list of Python
modules sorted by their test coverage gap (lowest coverage, most
statements first). Your task is to review the list and confirm the
prioritization is correct for the project's goals.

For each module, consider:
- Whether the module is critical to core functionality
- Whether the missing lines are in error-handling paths
- Whether there are known bugs in this area of the codebase

Return your analysis as a JSON object with a "modules" key containing
the ordered list with any re-prioritization notes.
"""

PLAN_SYSTEM_PROMPT = """\
You are a test planning expert. You have been given a list of Python
modules that need additional test coverage. Your task is to group
these modules into logical batches and generate XML-enhanced task
prompts that a test writer can execute.

For each batch:
- Group by subsystem or shared functionality
- Identify the key behaviors to test
- Specify concrete test class names and method stubs
- Set a realistic coverage target for each module

Return a JSON object with a "batches" key containing the batch list,
each with a "task_xml" field containing the XML task prompt.
"""

BATCH_TASK_TEMPLATE = """\
<task id="{batch_id}" name="{subsystem}-tests">
  <objective>
    Write unit tests for {subsystem} to reach {target_pct}% coverage.
    Focus on missing lines: {missing_lines_summary}.
  </objective>
  <context>
    <existing-code path="{source_path}">
      {key_signatures}
    </existing-code>
  </context>
  <files-to-create>
    <file path="{test_path}">
      {test_class_specs}
    </file>
  </files-to-create>
  <validation>
    <check>{module} reaches >= {target_pct}% coverage</check>
    <check>All new tests pass: pytest {test_path} -v</check>
  </validation>
</task>
"""
