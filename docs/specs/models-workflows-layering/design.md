# Models↔Workflows Layering — Design

**Status:** draft (2026-08-26) — executes D2 (rename-by-role) with
per-class names verified against the tree, plus one finding that D2's
ruling did not have in front of it. Awaiting chair read.
**Scope:** R3 only. Edge 1 (R1) shipped in #2314; R4/R5 are constraints
carried here, not work.

---

## What each `WorkflowConfig` actually is

D2 ruled the direction — canonical keeps the name, the others get
role-true names — and explicitly deferred exact names to "verified and
proposed in the design phase, per-class, against what each actually
does". Verified 2026-08-26:

| # | Class | Shape | Live consumers | Currently exported as |
|---|---|---|---|---|
| 1 | `workflows/config.py:53` | `workflows.yaml`-backed, 676 lines, 23 defs | ~35 importers | `WorkflowConfig` |
| 2 | `config/sections/workflows.py:11` | 4 fields + `to_dict`/`from_dict`; the `workflows:` block of the unified config file | `config/unified.py`, `config/sections/__init__` | `WorkflowConfig` |
| 3 | `config/agent_config.py:256` | pydantic `BaseModel`; **field-for-field identical to #4** | **none** | `AgentWorkflowConfig` |
| 4 | `agent_factory/base.py:101` | dataclass; `mode`/`state_schema`/`checkpointing`/`framework_options` — graph construction | `agent_factory/__init__` + 7 test modules | `WorkflowConfig` |

## The finding D2 did not have

**#3 and #4 carry the same ten fields** (`name`, `description`, `mode`,
`max_iterations`, `timeout_seconds`, `state_schema`, `checkpointing`,
`retry_on_error`, `max_retries`, `framework_options`) — one a dataclass,
one a pydantic model. That is a duplicated model, not a name collision,
and renaming both to distinct role-true names would make the duplication
permanent and harder to see.

**#3 has no consumer.** `AgentWorkflowConfig` appears exactly twice in
the tree: the aliased import at `config/__init__.py:23` and its `__all__`
entry at `:75`. No src caller, no test, no doc. It entered in
`dc6c8f69e` ("Modular architecture phases 1A/1B/2A"), after #4
(`faeac70db`) — an orphan twin left by the consolidation.

Against `removing-dead-code.md` this trips **zero usage evidence**
("no caller in the live code paths — only tests and `__init__` exports";
here, not even tests) and **orphaned motivation**. The rule's gate says
switch from renaming a surface to removing the engine.

**Proposal: delete #3 rather than rename it**, and drop the
`AgentWorkflowConfig` alias with it. This is a chair call, not a lead
call, because D2 declined consolidation-to-one-class and this is
adjacent to that ruling — though not the same thing: D2 declined merging
LIVE classes, and #3 is not live.

## Per-class proposal

**#1 `workflows/config.py` — keeps `WorkflowConfig`.** Ruled by D2. The
public `workflows.yaml`-backed type; ~35 importers; renaming it is the
expensive, low-value direction.

**#2 → `WorkflowsConfig`** (plural). Not an invented name — it restores
the convention its six siblings already follow, where the class matches
its module and config key:

| module | class |
|---|---|
| `analysis.py` | `AnalysisConfig` |
| `auth.py` | `AuthConfig` |
| `environment.py` | `EnvironmentConfig` |
| `persistence.py` | `PersistenceConfig` |
| `routing.py` | `RoutingConfig` |
| `telemetry.py` | `TelemetryConfig` |
| `workflows.py` | `WorkflowConfig` ← the only one that breaks it |

Cost: 3 import sites. Deprecation alias per D2.

**#3 — delete** (see above). If the chair prefers rename-only, the
fallback is `AgentWorkflowConfig` as the class's real name, since that
is already what `config/__init__` advertises — near-zero churn either
way, so the choice is purely "should this exist".

**#4 → `AgentGraphConfig`.** Note the honest counter-case: *within its
own module* `WorkflowConfig` is already well-named, sitting beside
`AgentConfig`, `BaseAgent`, `BaseWorkflow`, `BaseAdapter` — the
collision is only visible globally. But D2's intent is that exactly one
class holds the bare name, so it moves. `AgentGraphConfig` is chosen
over `WorkflowGraphConfig` because the neighbourhood prefixes with
`Agent` (`AgentRole`, `AgentCapability`, `AgentConfig`), and the fields
it carries (`state_schema`, `checkpointing`, `framework_options`,
`mode` ∈ sequential/parallel/graph/conversation) are graph-construction
concerns. Cost: `agent_factory/__init__` export + 7 test modules.

## Sequencing

1. **#3 disposition first** — a delete removes a third of the problem
   and the duplication question in one step; a rename does not.
2. **#2 rename** — smallest live blast radius (3 sites).
3. **#4 rename** — largest (8 sites); lands last so the earlier two are
   already green.

Aliases first, hard rename at the next major (D2). One PR per class:
each is independently revertible, and #4's test churn should not sit in
the same diff as #2's three-line change.

## Constraints carried

- **R4** — no new top-level packages. Every name above lands in its
  existing module.
- **R5** — each rename moves with its tests' patch targets in the same
  PR; any back-compat alias carries the defining-module warning.
- The layering boundary itself is now gated mechanically
  (`test_no_models_module_imports_workflows_at_any_scope`, #2314), so
  none of this work can silently reopen the cycle.

## Open questions for the chair

1. **Delete #3, or rename it to `AgentWorkflowConfig`?** Recommendation:
   delete. It has no consumer and duplicates #4.
2. **Is `AgentGraphConfig` right for #4**, given it is already coherent
   inside its own module? Recommendation: yes — D2's one-bare-name
   intent outranks local coherence, and the alias absorbs the churn.
3. **Does #2239 close when these land?** R6 says it closes when Edge 1
   is dead and R3 is ruled. Edge 1 died in #2314; R3 is ruled once the
   chair reads this. The renames themselves could execute after the
   close.
