---
type: task
name: use-doc-gen
tags: [skill, task]
source: plugin/skills/doc-gen/SKILL.md
---

# Task: Use the doc-gen skill

Generate documentation from source code — docstrings, READMEs, API references. Triggers on: generate docs, write documentation, document this, create README, API docs, doc-gen.

Invoke with: `/doc-gen <path or module to document>`

## Steps

1. **Define target**
   "Which file or module needs documentation?"

2. **Define type**
   "What kind of docs?" - Docstrings — Add or update Google-style docstrings - README — Generate a README section for a module - API reference — Generate full API documentation - Overview — High-level module explanation

3. **Run the tool**
   ### Shared command workspace (preferred)

   Open adapter `doc-gen` with the validated target and documentation type. Run
   the bound read-only `doc_audit` action first and publish `audit_result` with
   the exact proposed artifact paths. Present the proposal widget or Markdown;
   only an explicitly confirmed `apply_docs` action authorizes those paths.

   After `doc_gen`, publish `generation_result` with the exact files reported
   from disk. The adapter hashes them independently and rejects writes outside or
   different from the approved set. Run the returned `doc-import-audit`/symbol
   reality probe and publish its exact command and outcome as
   `validation_result`. A partial write or failed reality probe must say “did not
   complete” and retain changed-file hashes for rollback. Preserve these gates
   and receipts in compact text when the shared tools are unavailable.

   For docstring generation:

   ```
   doc_gen(source_path="<target module>")
   ```

4. **Run tool (option 2)**
   For a full documentation audit first:

   ```
   doc_audit(path="<target>")
   ```

5. **Run tool (option 3)**
   Then generate docs for gaps found:

   ```
   doc_gen(source_path="<gap file>")
   ```

6. **Run tool (option 4)**
   For a complete pipeline (audit + generate + review):

   ```
   doc_orchestrator(path="<target>")
   ```

7. **Choose follow-up action**
   Want me to apply these docstrings to the files?; Should I audit the rest of the project?; Want a README section generated from this?


## Related Topics
- **Reference**: Skill: doc-gen — full reference
