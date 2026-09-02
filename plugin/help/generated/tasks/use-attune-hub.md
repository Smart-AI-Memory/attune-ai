---
type: task
name: use-attune-hub
tags: [skill, task]
source: plugin/skills/attune-hub/SKILL.md
---

# Task: Use the attune-hub skill

Developer workflow hub — routes to the right skill based on what you need. Triggers on: attune, what can attune do, what can you do, capabilities, where do I start, get started.

Invoke with: `/attune-hub <what you need help with>`

## Steps

1. **Scope the attune-hub request**
   Answer the scoping questions before running.

2. **Review attune-hub execution guidance**
   Based on the user's answer or arguments, describe the
   intent so Claude matches the right skill:

   | Input | Describe to Claude |
   | ----- | ------------------ |
   | "Run a workflow" or `security` | "Run a security audit on the code" |
   | "Run a workflow" or `review` | "Review the code for quality issues" |
   | "Run a workflow" or `tests` | "Generate tests for uncovered code" |
   | "Run a workflow" or `perf` | "Analyze code for performance issues" |
   | "Run a workflow" or `release` | "Prepare for a release" |
   | "Run a workflow" or `bugs` | "Predict likely bug locations" |
   | "Manage memory" or `memory` | "Store or retrieve from memory" |
   | "Configure settings" or `setup` | Run `attune doctor` and `attune auth` |
   | "Configure settings" or `update` | Run `pip install --upgrade attune-ai` |


## Related Topics
- **Reference**: Skill: attune-hub — full reference
