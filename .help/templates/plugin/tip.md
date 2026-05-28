---
type: tip
name: plugin-tip
feature: plugin
depth: tip
generated_at: 2026-05-27T13:42:27.350556+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Tip: Working effectively with the plugin hooks

Call the public entry points — `main()` in `hooks.spec_orient`, `hooks.compact_warning`, and `hooks.format_on_save` — rather than reaching into underscore-prefixed modules directly. Those internal modules (`_state`, `_resume_prompt`, `_transcript_size`, `_handoff_cli`) can change between versions; the public `main()` functions are the stable interface.

**Why:** Underscore-prefixed modules in this package are explicitly internal — `_state`, `_resume_prompt`, and `_transcript_size` are shared helpers that multiple hooks import, so their signatures change whenever any of those hooks evolves.

**Tradeoff:** Staying at the public surface means you get less direct access to intermediate values — for example, you can't cheaply reuse a `GitState` object across two calls without going through `hooks._state.git_state()`. That is an acceptable cost; if you genuinely need the intermediate data, import the specific helper by name and treat it as an internal dependency you own.

**Tags:** `plugin`, `claude-code`
