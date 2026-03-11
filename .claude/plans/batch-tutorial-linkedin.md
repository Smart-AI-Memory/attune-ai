# LinkedIn Tutorial: Batch Processing with Attune AI

**Created:** 2026-03-05
**Source:** /brainstorm session

## Problem

Claude Code users run repetitive AI tasks (security audits,
test generation, code reviews) one at a time at full API
price. Most don't know Anthropic's Batch API exists or that
it cuts costs 50%.

## Goals

- Show Claude Code users a concrete cost savings they can
  get today
- Introduce Attune AI as the tool that makes batch
  processing easy
- Format: code screenshot + walkthrough (Patrick's
  highest-engagement style)

## End State

A LinkedIn post with screenshots showing:

1. Screenshot 1: AskUserQuestion UI prompting the user to
   pick batch task types (interactive Socratic discovery)
2. Screenshot 2: Generated batch processing code that
   Attune wrote based on user's answers (editable)
3. Brief cost comparison (50% savings)

Reader sees: "It asked me what I needed, wrote the code,
and I can edit it." Thinks "I should install this."

## Task Prompts

```xml
<task id="1" name="draft-linkedin-post">
  <objective>
    Write a LinkedIn tutorial post showing how to batch
    multiple code analysis tasks with Attune AI and save
    50% on Anthropic API costs.
  </objective>

  <context>
    <audience>
      Claude Code users who have never heard of Attune AI.
      Developers who use Claude for code reviews, test
      generation, security audits.
    </audience>

    <product-facts>
      - Attune AI is a pip-installable Python package
        (`pip install attune-ai`)
      - Batch processing uses Anthropic's Message Batches
        API (50% cost reduction, processes within 24 hours)
      - CLI command: `/bulk submit`
      - Python API: BatchProcessingWorkflow class
      - Supports task types: analyze_logs, generate_report,
        classify_bulk, generate_docs, generate_tests
      - Model tier selection: cheap (Haiku), capable
        (Sonnet), premium (Opus)
      - Results saved to JSON
    </product-facts>

    <existing-code path="src/attune/workflows/batch_processing.py">
      BatchProcessingWorkflow class with:
      - BatchRequest(task_id, task_type, input_data, model_tier)
      - execute_batch(requests, poll_interval, timeout)
      - load_requests_from_file(file_path)
      - save_results_to_file(results, output_path)
    </existing-code>

    <cli-commands path="src/attune/commands/bulk.md">
      /bulk submit - Queue tasks for async processing
      /bulk status <id> - Check progress
      /bulk results <id> - Retrieve completed results
      /bulk wait <id> - Block until complete
    </cli-commands>
  </context>

  <structure>
    <section name="hook">
      Opening line that stops scrolling. Lead with the
      interactive experience, not just cost savings.
      Example angle: "What if your AI assistant asked
      what you needed before writing the code?"
    </section>

    <section name="problem">
      2-3 sentences: You run security audits, test gen,
      code reviews one at a time. You write the same
      boilerplate batch code every time. Full price
      per call.
    </section>

    <section name="screenshot-1">
      Screenshot of AskUserQuestion UI in Claude Code.
      Attune asks: "What tasks do you want to batch?"
      with options like:
      - Generate tests (for multiple files)
      - Generate docs (for your API)
      - Security audit (across modules)
      - Code review (bulk analysis)
      The user picks their tasks interactively.
    </section>

    <section name="screenshot-2">
      Screenshot of the generated Python code that
      Attune produces based on the user's selections.
      Clean BatchRequest list, execute_batch() call,
      results handling. Caption: "Attune wrote this
      based on my answers. I can edit it before running."
    </section>

    <section name="cost-comparison">
      Brief callout (not the main story):
      "Oh, and batch API = 50% off Anthropic pricing.
      Same results. Half the cost."
    </section>

    <section name="cta">
      pip install attune-ai
      Link to repo
      "Try /bulk submit in Claude Code"
    </section>
  </structure>

  <format-rules>
    - LinkedIn max ~3000 chars for full visibility
    - Use ASCII code block markers (--- CODE START --- /
      --- CODE END ---) not Unicode arrows (LinkedIn
      mangles them)
    - Code screenshots > inline code for engagement
    - Short paragraphs (1-2 sentences each)
    - No emojis unless Patrick adds them
  </format-rules>

  <validation>
    <check>Post is under 3000 characters</check>
    <check>All code examples use real Attune API (BatchRequest,
      BatchProcessingWorkflow, execute_batch)</check>
    <check>50% savings claim references Anthropic's Batch API
      pricing, not a made-up number</check>
    <check>Install command is `pip install attune-ai`</check>
    <check>No Unicode characters that LinkedIn will mangle</check>
    <check>Includes at least one code screenshot description</check>
  </validation>
</task>

<task id="2" name="create-screenshots">
  <objective>
    Create the two screenshots for the LinkedIn post:
    (1) AskUserQuestion interactive prompt for batch task
    selection, and (2) the generated editable code output.
  </objective>

  <context>
    <screenshot-1-approach>
      Run `/bulk submit` in Claude Code with Attune
      installed. Attune's Socratic flow will trigger
      AskUserQuestion to ask the user what tasks to
      batch. Screenshot the VSCode/terminal UI showing
      the interactive picker with options.
    </screenshot-1-approach>

    <screenshot-2-approach>
      After selecting tasks, Attune generates a Python
      script with BatchRequests tailored to the user's
      choices. Screenshot the generated code in the
      editor — showing it's real, editable Python.
    </screenshot-2-approach>

    <askuserquestion-format>
      AskUserQuestion renders as a picker UI in Claude
      Code with labeled options and descriptions. The
      screenshot should show something like:

      Header: "Batch Tasks"
      Question: "What tasks do you want to batch?"
      Options:
      - Generate tests — Create unit tests for
        multiple files
      - Generate docs — Auto-document your API
      - Security audit — Scan modules for
        vulnerabilities
      - Code review — Bulk code analysis
    </askuserquestion-format>
  </context>

  <files-to-create>
    <file path="docs/tutorials/linkedin-batch-demo.py">
      The "generated code" that appears in screenshot 2.
      Must look like something Attune would produce
      after the user picks "Generate tests" + "Generate
      docs" from the AskUserQuestion picker.

      Should include:
      1. Import BatchProcessingWorkflow, BatchRequest
      2. BatchRequests matching the user's selections
         (3 generate_tests + 2 generate_docs)
      3. execute_batch() call
      4. Results summary print
      5. Cost savings note as a comment

      Keep it under 35 lines. Clean enough to
      screenshot. Add a header comment like:
      "# Generated by Attune AI - edit as needed"
    </file>
  </files-to-create>

  <validation>
    <check>Screenshot 1 shows real AskUserQuestion UI
      (run /bulk submit to trigger it)</check>
    <check>Screenshot 2 shows generated code that's
      clearly editable (in an editor, not terminal)</check>
    <check>Generated code uses real Attune API</check>
    <check>Code is under 35 lines and visually clean</check>
    <check>The two screenshots tell a story: ask -> generate</check>
  </validation>
</task>

<task id="3" name="prompt-chaining-feature-plan">
  <objective>
    Plan the prompt chaining feature for tomorrow's
    session — a dedicated tool that chains prompts with
    context passing between steps, adding value beyond
    what manual chaining provides.
  </objective>

  <context>
    <current-state>
      Attune can chain prompts via multi-stage workflows
      and agent handoffs, but there's no dedicated prompt
      chaining feature that adds value over doing it
      manually in Claude Code.
    </current-state>

    <desired-outcome>
      A feature that makes prompt chaining easier, more
      reliable, or more powerful than manual chaining.
      Should be tutorial-worthy for a follow-up LinkedIn
      post.
    </desired-outcome>
  </context>

  <research-questions>
    - What context is lost between manual prompt chains
      that a tool could preserve?
    - Should chains be defined as YAML/JSON specs or
      built programmatically?
    - How does this differ from existing workflow stages?
    - What's the smallest useful version (MVP)?
    - Can chains be batched for cost savings (combine
      with Task 1)?
  </research-questions>

  <validation>
    <check>Plan identifies a clear value-add over manual
      chaining</check>
    <check>MVP is scoped to 1 session of work</check>
    <check>Plan includes at least one concrete usage
      example</check>
  </validation>
</task>
```

## Next Steps

- [ ] Execute Task 1: Draft the LinkedIn post
- [ ] Execute Task 2: Create screenshot-ready code
- [ ] Execute Task 3: Plan prompt chaining feature
  (tomorrow)

## Open Questions

- What's the actual per-request cost for Sonnet via Batch
  API? (Need current pricing for the cost comparison
  section)
- Does Patrick want to show the CLI (`/bulk submit`) or
  the Python API, or both?
- Should the post link to the Attune GitHub repo or
  the PyPI page?
