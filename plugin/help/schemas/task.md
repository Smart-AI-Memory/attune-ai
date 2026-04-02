---
type: task
description: >
  Task template schema for procedural content —
  step-by-step instructions for completing a goal.
required_fields:
  - name
  - introduction
  - steps
optional_fields:
  - prerequisites
  - related_topics
  - tags
  - source
---

# Task: {name}

## Introduction

{introduction}

Sets context: why and when to perform this task.

## Prerequisites

{prerequisites}

What must be in place before starting (optional).

## Steps

{steps}

Ordered list of actions. Each step has a description
and optional code example.

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Reference: detailed specs for tools used in steps
- Error: known failure modes at specific steps
- Tip: efficiency improvements
- Warning: actions with consequences
