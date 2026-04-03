---
type: warning
name: gpg-signing-fails-in-non-interactive-terminals-vscode-extension
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: GPG signing fails in non-interactive terminals (VSCode
  extension, Claude Code)

## Condition

`gpg` tries to open `/dev/tty` for passphrase input, which doesn't exist in spawned subprocesses

## Risk

Ignoring this guidance may cause: GPG signing fails in non-interactive terminals (VSCode
  extension, Claude Code)

## Mitigation

1. install `pinentry-mac` (`brew install pinentry-mac`), set `pinentry-program /opt/homebrew/bin/pinentry-mac` in `~/.gnupg/gpg-agent.conf` (remove any earlier `pinentry-tty` lines — GPG uses the first match), then `gpgconf --kill gpg-agent`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: GPG signing fails in non-interactive terminals (VSCode
  extension, Claude Code)
