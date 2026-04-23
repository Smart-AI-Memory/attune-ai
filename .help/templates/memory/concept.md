---
type: concept
feature: memory
depth: concept
generated_at: 2026-04-23T03:30:41.225048+00:00
source_hash: 65cd08d1432d00333db89709ddcd7b9eb6a2277e6649a322b27cb5880d2058a3
status: generated
---

# Memory

## What it is

The memory subsystem provides both short-term storage for active conversations and long-term persistence for Claude memory files, with security controls and enterprise management capabilities.

## Why it matters

Attune AI agents need to remember context across conversations and access persistent knowledge stored in CLAUDE.md files. The memory subsystem handles this through two distinct pathways: a backend protocol for short-term memory (like Redis) and a loader system for Claude's structured memory files.

## Core components

**Short-term memory backends** implement the `MemoryBackend` protocol to store conversation state, with operations like `stash()` for saving data with TTL, `retrieve()` for lookup, and `search()` for semantic queries on backends that support it.

**Claude memory integration** loads CLAUDE.md files from project hierarchies through `ClaudeMemoryLoader`, which resolves imports, manages load order, and provides a unified view of enterprise, project, and user-level memory files.

**Control panel** offers enterprise management through `MemoryControlPanel`, including Redis lifecycle management, pattern classification, audit logging, and API endpoints for administrative tasks.

## Memory file hierarchy

Claude memory files follow a three-tier structure:

- **Enterprise level** — organization-wide patterns and protocols
- **Project level** — repository-specific context and conventions
- **User level** — personal preferences and working patterns

The loader resolves imports between levels and presents them as a single consolidated memory string for Claude to use as context.

## Security model

The subsystem includes built-in protection against storing sensitive data:

- **PII scrubbing** automatically detects and masks personal information
- **Secrets detection** prevents API keys and credentials from being stored
- **Pattern classification** categorizes memory content by sensitivity level
- **Access controls** enforce permissions based on data classification

## Backend flexibility

Different backends serve different deployment needs:

- **Redis** for production deployments with persistence and distribution
- **File-based** for local development and testing
- **Mock** for unit tests and CI environments

All backends implement the same protocol, so you can switch between them based on environment or performance requirements.
