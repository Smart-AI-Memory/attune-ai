---
type: faq
name: bug-predict-faq
feature: bug-predict
depth: faq
generated_at: 2026-05-16T06:19:45.790357+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict FAQ

## What does bug prediction do?

It scans your codebase for patterns that historically cause production incidents — things like `eval()` on user input, silently swallowed exceptions, and unfinished code paths — then scores and ranks the results by severity so you know where to focus first.

## When should I use it?

Use bug prediction before merging a large PR, during code review to focus attention on real risks, or before a release to confirm no new high-severity patterns crept in. It's also useful when you're onboarding to an unfamiliar codebase and want to map risk hotspots quickly.

## How do I run it?

Pass a file or directory to `/bug-predict`:

```
/bug-predict src/
```

You can also use natural language:

```
predict bugs in src/
where are bugs most likely in the auth package?
```

If you don't specify a path, the skill prompts you to scope the scan before it runs.

## What patterns does it detect?

Three categories:

| Pattern | Severity | Example |
|---|---|---|
| `dangerous_eval` | HIGH | `eval()` or `exec()` on user input |
| `broad_exception` | MEDIUM | Bare `except:` that silently swallows errors |
| `incomplete_code` | LOW | TODO, FIXME, HACK, or XXX comments |

Beyond pattern matching, the scanner also weighs cyclomatic complexity, how frequently a file changes, and general code smells like functions over 50 lines.

## Will it flag false positives?

It filters out several known-safe patterns automatically — for example, `eval()` inside test fixture strings, JavaScript's `regex.exec()` calls, and broad exceptions marked with `# INTENTIONAL:` or `# noqa: BLE001`. You can also signal intent through keywords like `fallback`, `graceful`, or `optional` in comments.

## How do I read the report?

Results are grouped by severity (HIGH → MEDIUM → LOW). Each finding shows the file path, line number, pattern type, and a plain-English description. File links are clickable so you can jump directly to the issue.

The overall risk score runs from 0 to 100 and appears at the top of the report alongside a short executive summary of the biggest hotspots.

## What should I do after I see the results?

Fix HIGH findings first. You can ask directly — for example, `"fix the dangerous_eval in executor.py"` — to get a guided fix. After that, consider asking `"write tests for the flagged files"` to prevent regressions, or run a focused scan on a specific subdirectory to go deeper.

## How do I generate a report programmatically?

Call `format_bug_predict_report(result, input_data)` from `src/attune/workflows/bug_predict_report.py`. It takes the raw workflow result and the original input data, and returns a formatted string. For the CLI, use `main()` in the same module.

## How do I debug a failing scan?

Run the related tests first:

```
pytest -k "bug-predict" -v
```

If the tests pass but your scan still fails, add a `logger.debug` statement at the suspected failure point and re-run with logging enabled. The three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) each report findings independently — checking their individual output can help you isolate which stage is failing.

## Where are the source files?

- `src/attune/workflows/bug_predict.py` — orchestration workflow and subagent coordination
- `src/attune/workflows/bug_predict_report.py` — report formatting and CLI entry point

**Tags:** `bugs`, `scanning`, `security`
