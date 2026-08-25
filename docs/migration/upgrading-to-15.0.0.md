# Upgrading to 15.0.0

15.0.0 finishes the Empathy-framework excision that began in 9.0.0.
Everything it removes is a public surface that pointed at a retired
contract: the 1–5 `empathy_level` knob, the `EmpathyMCPServer` name,
and the legacy entry-point groups. **If you use attune-ai through
the CLI, the plugin, or the MCP tools, you upgrade with no code
changes.** The removals bite in exactly one place — third-party code
that subclasses the plugin contract, registers entry points, or
passes a level.

## Do you need to change anything?

| Situation | What's different in 15.0.0 | What to do |
|---|---|---|
| You import `EmpathyMCPServer` (§1) | the alias is gone | import `AttuneMCPServer` |
| You register workflows under `empathy.workflows` (§2) | the group is no longer read | re-register under `attune.workflows` |
| You register plugins under `attune_framework.plugins` or `empathy_framework.plugins` (§2) | neither group is read | re-register under `attune.plugins` |
| You subclass `attune.plugins.base.BaseWorkflow` (§3) | `__init__` no longer takes `empathy_level`; `get_empathy_level()` is gone | drop the argument and the call |
| You pass `empathy_level` to `AgentConfig` or `UnifiedAgentConfig` (§3) | the field is gone | drop it |
| You call `PluginRegistry.find_workflows_by_level()` or `AgentRegistry.get_by_empathy_level()` (§3) | both are gone | filter on your own metadata |
| You call the `attune_get_level` / `attune_set_level` MCP tools (§3) | both are deleted | remove the calls |
| You read `workflows_by_level` from plugin statistics (§3) | the block is gone | drop the read |
| You have `empathy_level:` in agents.md frontmatter (§4) | the key is ignored, not an error | nothing — remove it at your leisure |
| You have an existing metrics database (§4) | the legacy column is dropped on first open | nothing — it migrates itself |

**If none of these describe you, you're done — upgrade normally.**

---

## 1. `EmpathyMCPServer` is gone

The alias was deprecated in 14.x and is removed. The class itself is
unchanged — only the old name went away.

Before:

<!-- doc-import-skip: 15.0.0-removed API, shown for migration -->
```python
from attune.mcp import EmpathyMCPServer
```

After:

```python
from attune.mcp import AttuneMCPServer
```

## 2. Entry-point discovery is `attune.*` only

Discovery previously read a three-way split of groups. 15.0.0 reads
one group per kind:

| Kind | Read in 15.0.0 | No longer read |
|---|---|---|
| Workflows | `attune.workflows` | `empathy.workflows` |
| Plugins | `attune.plugins` | `attune_framework.plugins`, `empathy_framework.plugins` |

If your package declares a legacy group, your workflow or plugin
will simply stop being discovered — silently, since an unreadable
group is indistinguishable from having none. Update `pyproject.toml`:

```toml
# before
[project.entry-points."empathy.workflows"]
my_workflow = "my_pkg.workflows:MyWorkflow"

# after
[project.entry-points."attune.workflows"]
my_workflow = "my_pkg.workflows:MyWorkflow"
```

Re-install the package after editing so the metadata is regenerated.

## 3. The `empathy_level` knob is gone from every public API

The 1–5 level was defined by the retired framework, so it retires
with it rather than surviving under a new name.

```python
# before
class MyWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__(name="mine", domain="software", empathy_level=3)

# after
class MyWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__(name="mine", domain="software")
```

The current signature is
`BaseWorkflow.__init__(self, name, domain, category=None)`.

Removed alongside it: `get_empathy_level()`, the `empathy_level`
field on `AgentConfig` (`attune.agent_factory.base`) and
`UnifiedAgentConfig` (`attune.config.agent_config`),
`PluginRegistry.find_workflows_by_level()`, the `workflows_by_level`
statistics block, `AgentRegistry.get_by_empathy_level()`, the
`empathy_level` parameter of `MetricsCollector.record_metric()`, and
the `attune_get_level` / `attune_set_level` MCP tools.

If you were using the level to select among your own workflows, keep
your own mapping — the framework no longer has an opinion about what
1–5 means.

### Heads-up: `BaseWorkflow.analyze()` is not settled

`attune.plugins.base.BaseWorkflow` still declares an abstract
`analyze()` that the engine does not call — this class is for
plugin-internal analyzers you invoke yourself, and workflows
discovered via entry points subclass
`attune.workflows.base.BaseWorkflow` (whose entry point is
`execute()`) instead.

That dead abstract is known and is **expected to change in a future
major** (tracked in
[#2238](https://github.com/Smart-AI-Memory/attune-ai/issues/2238); the
15.0.0 manifest deferred it deliberately). It does not affect your
15.0.0 upgrade — the signature above is what 15.0.0 ships — but if you
are writing a new plugin today, prefer
`attune.workflows.base.BaseWorkflow` for anything the engine should
run, and expect the plugin-internal contract to be revised.

## 4. Two things that migrate themselves

**agents.md frontmatter.** A leftover `empathy_level:` key parses as
ignored. It is not an error, so you can remove it whenever you like.

**Metrics databases.** An existing metrics database keeps its old
`empathy_level` column until first open under 15.0.0, at which point
the column is dropped automatically. No manual migration, no data
loss beyond that column.

## What did NOT change

`EmpathyLLM`'s internal five-level progression is untouched. It is an
un-exported implementation detail, not part of the public surface,
and its future is tracked separately. If you are reaching into it,
you are using a private API and it may still move.

## Not sure whether anything applies?

Grep your project:

```bash
grep -rn \
  -e "empathy_level" \
  -e "EmpathyMCPServer" \
  -e "empathy.workflows" \
  -e "empathy_framework.plugins" \
  -e "attune_framework.plugins" \
  -e "attune_get_level" \
  -e "attune_set_level" \
  -e "find_workflows_by_level" \
  -e "get_by_empathy_level" \
  .
```

No hits means no changes are needed.

## See also

- [CHANGELOG](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CHANGELOG.md) — the full 15.0.0 entry
- [Upgrading to 13.0.0](upgrading-to-13.0.0.md) — the previous guide
