---
type: task
name: use-release-prep
tags: [skill, task]
source: plugin/skills/release-prep/SKILL.md
---

# Task: Use the release-prep skill

Pre-release preparation with health checks, security audit, changelog validation, version bumps, and dependency audits. Triggers on: release, publish, ship, deploy, version bump, changelog.

Invoke with: `/release-prep <version or 'check'>`

## Steps

1. **Define version**
   "What version are you releasing? Or should I check the current version and suggest?"

2. **Define scope**
   "Full release prep or a specific check?" - Full: All 4 agents (security, testing, docs, versioning) - Specific: Single check (e.g., just changelog)

3. **Run the tool**
   Call the `release_prep` MCP tool for a full assessment: For targeted checks, use individual tools: The full `release_prep` orchestrates a 4-agent team: - **Security Agent** — runs security_audit, flags
  vulnerabilities that block release
- **Testing Agent** — checks test coverage, runs
  test_generation for gaps
- **Docs Agent** — validates changelog, README, and
  documentation freshness
- **Version Agent** — checks version bumps, dependency
  compatibility, semver compliance

   ```
   release_prep(path="<project root>")
   ```

4. **Run tool (option 2)**

   ```
   health_check(path="<project root>")
dependency_check(path="<project root>")
secure_release(path="<project root>")
   ```

5. **Choose follow-up action**
   Want me to fix the blockers?; Should I update the changelog?; Ready to tag and publish?


## Related Topics
- **Reference**: Skill: release-prep — full reference
