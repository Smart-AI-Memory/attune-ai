---
name: real-project-files-on-disk-override-test-mocks
source: .claude/CLAUDE.md
summary: 'This template explains why tests that mock functions at their definition
  site fail to intercept real filesystem reads, and provides two solutions: mocking
  at the import site where functions are used, or isolating the filesystem with a
  temporary directory.'
tags:
- testing
- imports
type: faq
---

# FAQ: Real Project Files on Disk Override Test Mocks

## Answer

Tests that mock `_get_raw_suggestions()` at the definition site can still receive real suggestions from `_get_spec_suggestions()`, which reads actual `.claude/plans/` files from disk.

**Root Cause**

When you mock a function at its definition site rather than at its import site, the consuming module continues to reference the original, unmocked implementation. As a result, any code path that calls `_get_spec_suggestions()` bypasses the mock entirely and reads from the real filesystem.

**How to Fix**

Use one of the following approaches:

- **Mock at the import site** — patch the function in the consuming module, not where it is defined:
  ```
  # Correct: mock where it is used
  attune.voice.formatter.get_next_steps

  # Incorrect: mock where it is defined
  attune.voice.next_steps.get_next_steps
  ```

- **Isolate the filesystem** — use `monkeypatch.chdir(tmp_path)` to redirect the working directory to a temporary path, preventing the code from finding real `.claude/plans/` files:
  ```python
  def test_example(monkeypatch, tmp_path):
      monkeypatch.chdir(tmp_path)
      # test body here
  ```

---

## Related Topics

- **Error:** Real project files on disk override test mocks
