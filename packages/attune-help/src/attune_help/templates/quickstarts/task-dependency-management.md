---
type: quickstart
name: task-dependency-management
tags: [deps, packaging, python]
source: developer-guidance
---

# Quickstart: Add a Dependency

The fastest path from "I need this package" to
"it's properly added and verified."

## 5 steps

**1. Check the package on PyPI**

Look at the release history, license, and maintenance
status. If the last release was over two years ago or
there's no license, find an alternative.

**2. Add it to pyproject.toml**

```toml
[project]
dependencies = [
    "httpx>=0.27.0,<1.0",
]
```

Use `>=floor,<ceiling` to allow patches but block
breaking changes.

**3. Install and verify**

```
pip install -e '.'
python -c "import httpx; print(httpx.__version__)"
```

**4. Audit for vulnerabilities**

```
pip-audit
```

If anything is flagged, bump the version or find a
safer alternative before proceeding.

**5. Run your tests**

```
pytest
```

If tests pass, you're done. Commit the updated
`pyproject.toml`.

## What you just did

- Evaluated the package before installing it
- Pinned a version range (not unbounded `>=`)
- Checked for known CVEs
- Verified nothing broke

## Next steps

- Say **"tell me more"** for the full guide — auditing,
  updating, license checks
- Say **"show me the reference"** for version constraint
  syntax and lockfile management
- Say **"run a security audit"** to scan all your
  dependencies for vulnerabilities
