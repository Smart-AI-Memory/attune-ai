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
   For docstring generation: For a full documentation audit first: Then generate docs for gaps found: For a complete pipeline (audit + generate + review):

   ```
   doc_gen(source_path="<target module>")
   ```

4. **Run tool (option 2)**

   ```
   doc_audit(path="<target>")
   ```

5. **Run tool (option 3)**

   ```
   doc_gen(source_path="<gap file>")
   ```

6. **Run tool (option 4)**

   ```
   doc_orchestrator(path="<target>")
   ```

7. **Choose follow-up action**
   Want me to apply these docstrings to the files?; Should I audit the rest of the project?; Want a README section generated from this?


## Related Topics
- **Reference**: Skill: doc-gen — full reference
