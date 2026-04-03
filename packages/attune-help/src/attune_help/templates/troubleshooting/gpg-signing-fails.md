---
type: troubleshooting
name: gpg-signing-fails
tags: [git, macos, setup]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: GPG signing fails in VSCode/Claude Code

## Symptom

Commits fail with `error: gpg failed to sign the data` in non-interactive terminals.

## Diagnosis

1. Check if `pinentry-mac` is installed: `which pinentry-mac`
2. Verify `gpg-agent.conf` has the right pinentry-program (first line wins)
3. Check if the GPG agent has a cached passphrase: `echo test | gpg --clearsign`

## Fix

Install `pinentry-mac` (`brew install pinentry-mac`). Set `pinentry-program /opt/homebrew/bin/pinentry-mac` as the FIRST line in `~/.gnupg/gpg-agent.conf`. Kill agent: `gpgconf --kill gpg-agent`.

## Prevention

Cache the passphrase by running `echo unlock | gpg --clearsign` in a real terminal before using VSCode.

## Related Topics

_No related topics yet._
