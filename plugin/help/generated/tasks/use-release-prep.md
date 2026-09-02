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
   "Full advisory or a specific check?" - Full: advisory across security, testing, docs, versioning - Specific: Single check (e.g., just changelog)

3. **Run the tool**
   Call the `release_notes` MCP tool for a changelog draft and
   go/no-go recommendation:

   ```
   release_notes(path="<project root>")
   ```

4. **Run tool (option 2)**
   For targeted checks, use individual tools:

   ```
   health_check(path="<project root>")
   dependency_check(path="<project root>")
   secure_release(path="<project root>")
   ```

5. **Review release-prep execution guidance**
   The full release prep covers four areas:

   - **Security** — scans for vulnerabilities that block
     release
   - **Testing** — checks test coverage, identifies gaps
   - **Documentation** — validates changelog, README, and
     documentation freshness
   - **Versioning** — checks version bumps, dependency
     compatibility, semver compliance

6. **Choose follow-up action**
   Want me to fix the blockers?; Should I update the changelog?; Ready to tag and publish?


## Related Topics
- **Reference**: Skill: release-prep — full reference
