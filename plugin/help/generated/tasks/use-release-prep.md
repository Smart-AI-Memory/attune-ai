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

1. **Scope the release-prep request**
   The skill asks scoping questions before running.

2. **Execute the release-prep workflow**
   Run the MCP tool with your scoped parameters.

   ```
   release_prep(path="<project root>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: release-prep — full reference
