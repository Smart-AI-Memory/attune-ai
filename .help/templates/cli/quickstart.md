---
type: quickstart
name: cli-quickstart
feature: cli
depth: quickstart
generated_at: 2026-05-16T06:19:45.826688+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Quickstart: CLI commands and routing

Run your first `attune` command and confirm the CLI is working.

```
attune help-docs --tags
```

**Result:** A list of 34 tags with template counts — confirms the CLI is installed and responding.

## Prerequisites

- The project is cloned and installed locally.
- `attune` is available on your `PATH`.

## Step 1: Check today's costs

```
attune costs today
```

**Result:** A summary of today's API cost data.

## Step 2: Export cost data

```
attune costs export
```

**Result:** Cost data written to a file you can inspect or share.

## Step 3: Browse available help topics

```
attune help-docs --tag cli
```

**Result:** A filtered list of help templates tagged `cli`, confirming the help system and routing are both functional.

---

**Next:** Add a lesson to memory with `attune remember` so you can retrieve it later with `attune memory-recall`.
