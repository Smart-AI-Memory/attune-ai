---
type: task
name: task-dependency-management
tags: [deps, packaging, python]
source: developer-guidance
---

# How to Manage Dependencies

## Adding a new dependency

Before you type `pip install`, pause and evaluate the
package. This takes two minutes and saves hours of
debugging or security remediation later.

### Step 1: Check the package

Look at the package on PyPI and its source repository:

| Question | Where to look | Red flag |
|----------|--------------|----------|
| Last release? | PyPI release history | Over 2 years ago |
| Open issues? | GitHub issues tab | Hundreds with no triage |
| License? | PyPI sidebar or `LICENSE` file | No license, or GPL when you need permissive |
| Known CVEs? | `pip-audit` or osv.dev | Unpatched advisories |
| Transitive deps? | `pip show <package>` Requires field | Pulls in 50+ packages |

### Step 2: Add it properly

Add the dependency to `pyproject.toml` with a version
constraint, not just `pip install`:

```toml
[project]
dependencies = [
    "httpx>=0.27.0,<1.0",
]
```

For optional features, use extras:

```toml
[project.optional-dependencies]
redis = ["redis>=5.0.0"]
```

### Step 3: Verify the install

```
pip install -e '.[dev]'
python -c "import new_package; print(new_package.__version__)"
```

Run your test suite to catch conflicts immediately.

## Auditing existing dependencies

Run a vulnerability scan on what you already have
installed:

```
pip-audit
```

Example output:

```
Found 2 known vulnerabilities in 1 package
Name     Version  ID           Fix
-------- -------- ------------ --------
urllib3  1.26.5   PYSEC-2023-  >=1.26.17
urllib3  1.26.5   GHSA-v845-  >=2.0.7
```

Each finding includes the package name, your installed
version, the advisory ID, and the minimum version that
fixes it.

### What to do with findings

| Severity | Action | Timeline |
|----------|--------|----------|
| **Critical/High** | Bump immediately, test, deploy | Same day |
| **Medium** | Add to current sprint | This week |
| **Low** | Bundle with next planned update | Next release |

## Updating dependencies

### Single package

```
pip install --upgrade httpx
```

Then update the constraint in `pyproject.toml` if the
new version is outside your current range.

### Full update

```
pip install --upgrade-strategy eager -e '.[dev]'
```

Always run the test suite after bulk updates. If
something breaks, bisect by updating one package at a
time.

## Checking licenses

Before adding a dependency, verify its license is
compatible with your project:

```
pip-licenses --format=table --with-urls
```

Example output:

```
Name      Version  License      URL
--------- -------- ------------ --------
httpx     0.27.0   BSD-3-Clause https://...
pydantic  2.6.0    MIT          https://...
redis     5.0.0    MIT          https://...
```

Watch for:

- **GPL/AGPL** in a permissive-licensed project
- **No license** (legally unusable)
- **Custom licenses** that need legal review

## What to do next

| Goal | What to say |
|------|-------------|
| Scan for vulnerabilities now | "run a security audit" |
| Check before releasing | "help me prepare a release" |
| See version constraint syntax | "show me the dependency reference" |
| Audit licenses across the project | "check dependency licenses" |

## Want to learn more?

- Say **"show me the reference"** for version constraint
  syntax, lockfile formats, and all tooling options
- Say **"what is dependency management?"** to go back
  to the overview
- Say **"run a security audit"** to scan your installed
  packages for known CVEs
