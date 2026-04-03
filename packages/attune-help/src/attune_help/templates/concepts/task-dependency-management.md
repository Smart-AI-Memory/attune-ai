---
type: concept
name: task-dependency-management
tags: [deps, packaging, python]
source: developer-guidance
---

# Dependency Management

Every package you add to your project is a decision with
long-term consequences. A dependency brings code you
didn't write into your supply chain — its bugs become
your bugs, its vulnerabilities become your vulnerabilities,
and its license terms apply to your users. Dependency
management is the practice of making those decisions
deliberately instead of by accident.

## What to evaluate before adding a dependency

| Concern | What to check | Risk if ignored |
|---------|---------------|-----------------|
| **Security** | Known CVEs, advisory history, maintainer reputation | Shipping exploitable code to production |
| **Compatibility** | Python version support, conflicts with existing deps | Import failures, runtime crashes |
| **License** | SPDX identifier, copyleft vs permissive, patent clauses | Legal liability, license violations |
| **Size** | Install footprint, transitive dependency count | Bloated containers, slow CI, larger attack surface |
| **Maintenance** | Last release date, open issue ratio, bus factor | Stuck on a dead library with no security patches |
| **Alternatives** | Can stdlib or existing deps cover this? | Unnecessary complexity |

## When you'd think about this

When adding a new package to `pyproject.toml`. When
upgrading a pinned version. When a security scanner
flags a CVE in your dependency tree. When CI breaks
after a transitive dependency released a bad version.
When preparing a release and you want to verify
nothing risky slipped in since the last one.

## The dependency lifecycle

| Phase | What happens | Tools involved |
|-------|-------------|----------------|
| **Evaluate** | Check license, security, maintenance | PyPI, GitHub, `pip-licenses` |
| **Add** | Pin version, install, verify | `pyproject.toml`, `pip install` |
| **Audit** | Scan for known vulnerabilities | `pip-audit`, security audit |
| **Update** | Bump versions, test compatibility | Dependabot, `pip-compile` |
| **Remove** | Drop unused deps, shrink tree | `pip-autoremove`, manual review |

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
  on adding and auditing dependencies
- Say **"show me the reference"** for version constraint
  syntax, lockfile management, and tooling details
- Say **"run a security audit"** to scan your current
  dependencies for known CVEs
- Say **"help me prepare a release"** to verify
  dependencies before publishing
