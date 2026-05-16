# Tutorial: Smart Test

You'll finish this tutorial with a working script that reads a real coverage report, ranks the modules with the biggest test gaps, and prints generated test stubs for the highest-priority one — so you can see exactly how `smart-test` turns a coverage gap into runnable pytest code.

## Prerequisites

- Python 3.10 or newer
- `pytest-cov` installed and a `coverage.json` file already generated for your project (run `pytest --cov=src --cov-report=json` if you don't have one yet)
- The `attune` package installed in your environment

## What you will build

A short Python script that:
1. Parses your project's `coverage.json` into ranked `ModuleCoverage` objects
2. Filters out modules already above 50 % coverage
3. Uses `ASTFunctionAnalyzer` to inspect the worst-covered module
4. Generates a pytest test stub for each public function it finds

By the end you'll have a file called `explore_smart_test.py` that you can run any time your coverage report changes.

---

## Step 1 — Import the pieces you need

The coverage parser and the AST analyzer live in two separate workflow packages. Import them with their real module paths:

```python
from attune.workflows.test_audit.coverage_parser import (
    parse_coverage_json,
    prioritize_modules,
)
from attune.workflows.test_gen import ASTFunctionAnalyzer, generate_test_for_function
```

`parse_coverage_json` converts the raw JSON pytest-cov writes into typed `ModuleCoverage` dataclasses. `prioritize_modules` then sorts and filters that list so you work on the riskiest gaps first.

Run the file now to confirm there are no import errors:

```
python explore_smart_test.py
```

You should see a blank terminal — no traceback means the imports resolved correctly.

---

## Step 2 — Parse the coverage report

Point `parse_coverage_json` at your `coverage.json` file. It raises `FileNotFoundError` if the path is wrong and `ValueError` if the JSON structure is unexpected, so wrap it to get a clear error message during exploration:

```python
import sys

try:
    modules = parse_coverage_json("coverage.json")
except FileNotFoundError as exc:
    sys.exit(f"Coverage file missing: {exc}")
except ValueError as exc:
    sys.exit(f"Bad coverage JSON: {exc}")

print(f"Parsed {len(modules)} modules")
```

Run the script. You should see something like:

```
Parsed 47 modules
```

The number reflects every file tracked in your `coverage.json`. Each entry is a `ModuleCoverage` with `path`, `stmts`, `covered`, `missing_lines`, `pct`, and `priority` fields.

---

## Step 3 — Rank the gaps

`prioritize_modules` filters out anything already above `min_threshold` percent (default 50 %) and sorts what remains so the highest-risk module comes first. High risk means many statements, low coverage — exactly what you want to tackle next:

```python
gaps = prioritize_modules(modules, min_threshold=50.0)

if not gaps:
    sys.exit("Great news: all modules are above 50 % coverage.")

worst = gaps[0]
print(f"Top gap: {worst.path}  ({worst.pct:.1f}% covered, {worst.stmts} statements)")
```

Run the script. You should see one line naming the file with the most room for improvement, for example:

```
Top gap: src/auth/tokens.py  (12.3% covered, 84 statements)
```

This tells you where `smart-test` would focus first and why: low coverage on a large file carries the highest regression risk.

---

## Step 4 — Analyze the module's structure

`ASTFunctionAnalyzer` walks the AST of a source file and extracts every function and class signature — parameter names, type hints, return types, raised exceptions, and complexity scores. You need this to generate meaningful tests rather than empty stubs:

```python
analyzer = ASTFunctionAnalyzer()

with open(worst.path) as fh:
    source = fh.read()

functions, classes = analyzer.analyze(source, file_path=worst.path)

print(f"Found {len(functions)} functions, {len(classes)} classes")
for fn in functions[:5]:        # preview the first five
    print(f"  {fn.name}({', '.join(p[0] for p in fn.params)}) -> {fn.return_type}")
```

Run the script. You should see the real signatures extracted from your file:

```
Found 11 functions, 2 classes
  create_token(user_id, expires_in) -> str
  validate_token(token) -> bool
  ...
```

Each `FunctionSignature` also carries `raises` (the exception types the function may throw), `is_async`, and `complexity` — details the test generator uses in the next step.

---

## Step 5 — Generate test stubs

`generate_test_for_function` takes a module path and the dict representation of a function signature and returns a complete pytest function as a string. Generate one for each function and write them to a file:

```python
from pathlib import Path

output_lines = [
    "import pytest",
    f"from {worst.path.replace('/', '.').removesuffix('.py')} import *",
    "",
]

for fn in functions:
    stub = generate_test_for_function(
        module=worst.path,
        func={
            "name": fn.name,
            "params": fn.params,
            "return_type": fn.return_type,
            "raises": list(fn.raises),
            "is_async": fn.is_async,
            "complexity": fn.complexity,
        },
    )
    output_lines.append(stub)
    output_lines.append("")

out_path = Path("tests/generated/test_smart_test_tutorial.py")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(output_lines))

print(f"Wrote {len(functions)} test stubs to {out_path}")
```

Run the script. You should see:

```
Wrote 11 test stubs to tests/generated/test_smart_test_tutorial.py
```

Open that file — each stub is a real `def test_*` function with parameter values inferred from the type hints and assertions matched to the return type. They're designed to run immediately with `pytest tests/generated/`.

---

## What you learned

- **Step 2** showed you that `parse_coverage_json` converts pytest-cov's JSON into structured `ModuleCoverage` dataclasses — the foundation everything else builds on.
- **Step 3** demonstrated how `prioritize_modules` turns a flat list into an actionable ranked queue by combining statement count and coverage percentage into a priority score.
- **Step 4** revealed that `ASTFunctionAnalyzer.analyze` extracts richer information than coverage alone — parameter types, raised exceptions, and complexity — which is what makes generated tests meaningful rather than trivially empty.
- **Step 5** connected those signatures to `generate_test_for_function` to produce pytest stubs you can run and extend immediately.

## Next steps

To go deeper, read the [Smart Test concept doc](concepts/tool-smart-test.md), which explains the full gap taxonomy (untested branches, error paths, boundary values, parametrized combos) and shows how to invoke the complete `TestAuditWorkflow` and `TestGenerationWorkflow` orchestrators that automate everything you assembled by hand here.

<!-- attune-generated: source_hash=2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc feature=smart-test kind=tutorial generated_at=2026-05-16 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 182 | error | `[Smart Test concept doc](concepts/tool-smart-test.md)` — target does not exist |
