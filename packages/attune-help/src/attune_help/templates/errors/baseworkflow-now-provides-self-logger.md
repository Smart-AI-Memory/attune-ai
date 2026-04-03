---
type: error
name: baseworkflow-now-provides-self-logger
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: BaseWorkflow now provides `self.logger`

## Signature

BaseWorkflow now provides `self.logger`

## Root Cause

Fixed in `c67ad740`. `BaseWorkflow.__init__` sets `self.logger = logging.getLogger(type(self).__module__)` so all subclasses get an instance logger namespaced to their own module. No more manual `wf.logger = ...` workarounds in test fixtures.

## Resolution

1. Fixed in `c67ad740`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
