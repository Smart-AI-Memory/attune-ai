---
name: decision-d3-faq-sourcing-four-channels
source: .claude/plans/documentation-stack-spec.md
summary: This template describes a four-channel FAQ sourcing system that ingests content
  from unmatched user queries, repeated error patterns, GitHub issues, and author
  curation, then deduplicates and ranks entries by frequency.
tags:
- architecture
- design-decision
type: note
---

# Design Decision: FAQ Sourcing (Four Channels)

## Context

This decision defines how FAQ content is sourced within the documentation stack architecture.

## Overview

FAQ entries are drawn from four distinct channels, ensuring coverage across automated signals and manual curation. All four channels feed into FAQ templates, where the engine deduplicates entries and ranks them by frequency.

## Sourcing Channels

### 1. Unmatched User Queries

Questions that fail to match any existing template are automatically flagged as FAQ candidates. This channel captures gaps in current documentation coverage.

### 2. Repeated Error Patterns

Errors that appear frequently in telemetry data are promoted to FAQ entries. This channel surfaces recurring pain points that may not be explicitly reported by users.

### 3. GitHub Issues and Discussions

Questions raised in issues and discussion threads feed directly into the FAQ pipeline. This channel captures real-world problems reported by the developer community.

### 4. Author-Curated Entries

Developers can manually associate FAQ entries with specific features when shipping new functionality. This channel allows proactive coverage of anticipated questions before they appear through other channels.

## Deduplication and Ranking

After ingestion from all four channels, the FAQ engine:

- **Deduplicates** entries that address the same underlying question
- **Ranks** surviving entries by frequency to surface the most relevant content first

## Related Topics

*No related topics yet.*
