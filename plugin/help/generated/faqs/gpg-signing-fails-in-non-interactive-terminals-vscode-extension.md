---
type: faq
name: gpg-signing-fails-in-non-interactive-terminals-vscode-extension
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does GPG signing fails in non-interactive terminals (VSCode extension, Claude Code)?

## Answer

`gpg` tries to open `/dev/tty` for passphrase input, which doesn't exist in spawned subprocesses. The passphrase must still be cached first by running `echo "unlock" | gpg --clearsign` in a real terminal.

**How to fix:**
- install `pinentry-mac` (`brew install pinentry-mac`), set `pinentry-program /opt/homebrew/bin/pinentry-mac` in `~/.gnupg/gpg-agent.conf` (remove any earlier `pinentry-tty` lines — GPG uses the first match), then `gpgconf --kill gpg-agent`

```
 tries to open
```

## Related Topics
- **Error**: Detailed error: GPG signing fails in non-interactive terminals (VSCode
  extension, Claude Code)
