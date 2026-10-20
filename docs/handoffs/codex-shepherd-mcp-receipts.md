# PR #2566 native MCP receipt refresh

## Goal

Replay native protocol evidence against the MCP 1.30.0 dependency
selected by the existing PR, preserving the current evidence contract.

## Current state

Base: `cf7e096459ab3f1546aa6d22954cd255c47fc6d4`. Local preparation
only; no remote branch, draft state or merge/deployment was changed.

## Change

Ran the existing `scripts/project_surface_runtime.py` projector through its
public `project(write=True)` entry after installing the unit inference guard.
This replays finite fixture-owned SDK exchanges with no network/model. Five
implementation digests changed in the source parity registry and its identical
packaged projection. All other registry fields, receipt observations, pending
obligations, mappings, test assertions and source code remain identical.

## Verification

- Python 3.10.11, isolated MCP 1.30.0 overlay. Other test dependencies were read
  from the existing developer environment; this was not a fresh locked install.
- Before replay: 11 failed / 251 passed in the surface parity/runtime modules.
- After replay: all 262 passed, including actual MCP stdio fixture transport.
- Native evidence, bootstrap, key, policy and selection modules: 128 passed.
- Existing projector check mode passed. JSON comparison confirmed exactly five
  implementation-digest changes and identical source/package projections.
- `git diff --check` passed. No test source, gates or pin policy changed.

## Next action

Different-model review of this external-boundary receipt refresh is pending.
The current instruction prohibits additional model calls, so none was started.
Full fresh hosted matrix and installed distribution qualification are pending.
These local tests do not establish Windows behavior or visible host rendering.
PR #2530 is the older manifest-only duplicate and remains open for owner choice.
Before publication, refresh the remote head and inspect concurrent ownership.
Publication triggers normal previews/CI. Merge and production remain held.
