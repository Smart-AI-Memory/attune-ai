"""Hook scripts for Attune AI.

The plugin ships concrete hook scripts under ``attune/hooks/scripts/``
(e.g. ``security_guard``, ``worktree_path_guard``, ``lessons_reminder``)
— these are the hooks Claude Code actually runs, wired via the
plugin's ``hooks.json`` and invoked over the stdin/exit-code contract.

The former in-process hook-execution engine (``HookRegistry``,
``HookExecutor``, ``HookConfig``) was removed in v13.0.0: it had no
live caller in attune, its originating use-case was retired in 9.0.0,
and it carried unfixed bugs. See the removing-dead-code gate reversal
for the rationale.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""
