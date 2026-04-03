---
type: reference
subtype: procedural
name: skill-bug-predict
category: skill
tags: [skill, plugin, reference]
source: plugin/skills/bug-predict/SKILL.md
---

# Bug Prediction Reference

Complete reference for the bug prediction skill -- every
pattern it detects, how risk scores work, false-positive
filtering, and configuration.

## Invocation

```
/bug-predict <path>
```

Or natural language:

```
predict bugs in src/
where are bugs most likely?
find risky code in the auth module
what might break in src/api/
```

The skill runs on your Claude subscription -- no API key
or additional cost.

## Scoping

Before running, the skill asks you to scope the scan:

1. **"Which files or directory should I scan?"** -- pick a
   file, directory, or the whole project. Defaults to
   `src/` if not specified.
2. **"Show all findings, or only HIGH severity?"** --
   filter by severity to focus on what matters.

You can skip the prompts by providing the path directly:

```
/bug-predict src/auth/
```

## All detected patterns

### dangerous_eval (HIGH)

| What it catches | Why it matters |
|-----------------|----------------|
| `eval(user_input)` | Arbitrary code execution -- attacker runs any Python |
| `exec(code_string)` | Same risk as eval, can modify global state |
| `compile()` on untrusted input | Creates executable code objects from strings |

**Confidence:** High. These are almost always real
vulnerabilities when found outside test fixtures.

**Auto-filtered false positives:**

- `eval()` inside `write_text()` calls (test data written
  to temp files, not executable)
- JavaScript `regex.exec()` method calls (safe string
  method, not Python `exec()`)
- Detection code like `if "eval(" in content` (scanner
  logic, not usage)
- Files matching `test_bug_predict*`,
  `test_scanner*`, or `test_security_scan*`

### broad_exception (MEDIUM)

| What it catches | Why it matters |
|-----------------|----------------|
| Bare `except:` | Catches `KeyboardInterrupt`, `SystemExit` -- masks everything |
| `except Exception:` without logging | Swallows errors silently -- impossible to debug |
| `except Exception as e: pass` | Captures the error then discards it |

**Confidence:** Medium. Context matters -- some broad
catches are intentional. The scanner uses context analysis
to allow acceptable patterns.

**Auto-filtered false positives:**

- Version detection: `try: get_version() except: "dev"`
- Config loading: `try: yaml.safe_load() except: defaults`
- Optional imports: `try: import lib except: lib = None`
- Cleanup code: `__del__`, `__exit__`, `cleanup()`,
  `close()`, `teardown()`
- Logged re-raises: `except Exception as e: log(e); raise`
- Intentional markers: `# fallback`, `# optional`,
  `# best effort`, `# graceful`
- Explicit suppression: `# INTENTIONAL:` or
  `# noqa: BLE001`

### incomplete_code (LOW)

| What it catches | Why it matters |
|-----------------|----------------|
| `TODO:` comments | Planned work that was never finished |
| `FIXME:` comments | Known bugs the author didn't fix yet |
| `HACK:` comments | Workarounds that were meant to be temporary |
| `XXX:` comments | Flagged areas needing attention |

**Confidence:** Low. Not all TODOs are bugs, but
incomplete code paths are where edge cases go unhandled.

## Risk scoring

The report assigns a risk score from 0-100:

| Range | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Low risk | No HIGH findings, few MEDIUM |
| 70-89 | Moderate risk | Some MEDIUM findings, no HIGH |
| 50-69 | Elevated risk | HIGH findings present |
| 0-49 | High risk | Multiple HIGH findings -- address before release |

**Scoring formula:**

- Start at 100
- Each HIGH finding: -15 points
- Each MEDIUM finding: -5 points
- Each LOW finding: -1 point
- Minimum score: 0

## Risk factors

Beyond pattern matching, the scanner weighs contextual
signals:

| Factor | Weight | What it measures |
|--------|--------|------------------|
| Cyclomatic complexity | High | Deeply nested conditionals, many branches |
| Change frequency | Medium | Files modified often have more regressions |
| Function length | Medium | Functions over 50 lines are harder to test |
| Missing test coverage | High | Untested code is where bugs hide |
| Duplicated logic | Low | Copy-paste code drifts out of sync |

## Output format

Results are presented as a severity-grouped report:

```markdown
## Bug Prediction Report

**Risk Score:** 73/100 (Moderate) | **Files:** 34
**Findings:** 8 (2 HIGH, 3 MEDIUM, 3 LOW)

### HIGH

| File | Line | Pattern | Description |
|------|------|---------|-------------|
| [executor.py:89](src/hooks/executor.py#L89) | 89 | dangerous_eval | eval() on user input |
| [loader.py:142](src/plugins/loader.py#L142) | 142 | dangerous_eval | exec() in plugin loader |

### MEDIUM

| File | Line | Pattern | Description |
|------|------|---------|-------------|
| [webhook.py:67](src/api/webhook.py#L67) | 67 | broad_exception | bare except: masks errors |

### LOW

| File | Line | Pattern | Description |
|------|------|---------|-------------|
| [session.py:45](src/auth/session.py#L45) | 45 | incomplete_code | TODO: add token rotation |
```

File links are clickable -- click to jump directly to the
issue.

## Configuration

### Excluding paths

Suppress findings for specific directories:

```yaml
# attune.config.yml
bug_predict:
  exclude_files:
    - "tests/fixtures/**"
    - "benchmarks/**"
    - "**/migrations/**"
```

### Acceptable exception contexts

Extend the list of contexts where broad exceptions are
acceptable:

```yaml
bug_predict:
  acceptable_exception_contexts:
    - version
    - config
    - cleanup
    - optional
```

### Inline suppression

Suppress a specific finding with an inline comment:

```python
result = eval(trusted_input)  # noqa: S307
```

Or mark an intentional broad catch:

```python
except Exception:  # noqa: BLE001
    # INTENTIONAL: graceful degradation for optional feature
    logger.warning("Feature unavailable")
```

## After the scan

| Goal | What to say |
|------|-------------|
| Fix high-severity findings | "fix the dangerous_eval in executor.py" |
| Generate regression tests | "write tests for the flagged files" |
| Focused scan on one area | "predict bugs in src/auth/" |
| Compare with last scan | "compare with previous bug prediction" |
| Run a security audit instead | "scan for security vulnerabilities" |

## Want to learn more?

- Say **"what is bug prediction?"** to go back to the
  overview
- Say **"how do I run bug prediction?"** for the
  step-by-step guide
- Say **"scan for security issues"** to run a security
  audit
- Say **"review my code"** for a broader code quality
  review
