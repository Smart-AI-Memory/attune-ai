# Attune AI Dashboard (VS Code extension)

Minimal, cross-platform scaffold for monitoring Attune AI telemetry
from VS Code. Works identically on macOS, Linux, and Windows.

This is a deliberate scaffold, not a restoration of the pre-2026
dashboard extension (removed in `0511e99ee`). Feature growth goes
through `specs/vscode-extension/` per the workspace SDD discipline.

## What it does

- **Attune Telemetry** tree view in the Explorer sidebar, reading
  `~/.attune/telemetry/*.jsonl` (or `$ATTUNE_HOME/telemetry/`)
- Live refresh via `workspace.createFileSystemWatcher` (reliable on
  all platforms, unlike `fs.watch`)
- `Ctrl+Shift+A` (`Cmd+Shift+A` on macOS) opens the dashboard view

## Setup (all platforms)

```bash
cd vscode-extension
npm install
npm run compile
```

Then launch the extension in an Extension Development Host: open
this folder in VS Code and press `F5`.

To install into your regular VS Code, package it with `vsce`:

```bash
npm install -g @vscode/vsce
vsce package
code --install-extension attune-dashboard-0.1.0.vsix
```

These commands are identical on macOS, Linux, and Windows — no
`cp -r` into `~/.vscode/extensions` needed (that path is
platform-specific and manual copies break extension updates).

## Redis (optional)

The extension never talks to Redis directly — it reads the telemetry
files written by the Python hook layer, which works with or without
Redis. If you want Redis-backed cross-session memory on Windows, use
Docker:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

See the repo README "Platform Support" section for the full policy.

## Cross-platform rules for contributors

- Build every path with `path.join()`; resolve home via
  `os.homedir()`; honor `ATTUNE_HOME`
- Watch files with `workspace.createFileSystemWatcher`, never
  `fs.watch`
- Read/write files with explicit `utf-8` encoding
- Keybindings declare both `key` (Windows/Linux) and `mac` variants
