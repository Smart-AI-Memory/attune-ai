# Round Table Deliberation Report: 5-PR Implementation Plan

- **Thread ID:** q-review-five-implementation-plans-001
- **Status:** Promoted (Chair-Ruled)
- **Promoted Message IDs:** 2, 3, 5

## Ratified Implementation Sequence

1. **PR 1: Adaptive Friction Matrix** (`src/attune/orchestration/friction/`)
   - Core 2D risk/clarity gating engine and pretooluse hook enforcement.
2. **PR 5: AST-Driven Context Budgeting** (`src/attune/rag/ast_budget/`)
   - AST skeleton generator & dynamic token budget manager (50%+ token cost reduction). Includes Redis caching for parsed ASTs (`attune:ast:<file_sha256>`).
3. **PR 3: Self-Healing Traps** (`src/attune/telemetry/lessons/`)
   - Pre-commit & verification failure listeners, root-cause synthesizer, `.claude/lessons.md` + Redis memory hydration.
4. **PR 2: Ghost Simulator Sandbox** (`src/attune/orchestration/ghosts/`)
   - Ephemeral Git worktrees under `.attune/ghosts`, parallel trajectory execution, comparative diff matrix. Includes ephemeral memory tagging (`ghost:true`) to prevent memory pollution.
5. **PR 4: Visual Debate Theater** (`attune-gui/src/components/debate/`)
   - Real-time WebSocket event broadcaster, Cytoscape graph UI, Executive Chair promotion panel in `attune-gui`.
