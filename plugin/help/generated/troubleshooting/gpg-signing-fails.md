---
name: gpg-signing-fails
source: CLAUDE.md Lessons Learned
summary: This template provides troubleshooting steps for resolving GPG signing failures
  in VS Code and Claude Code, including diagnosis of the root cause, installation
  and configuration fixes for `pinentry-mac`, and preventive measures to cache passphrases
  before using non-interactive terminals.
tags:
- git
- macos
- setup
type: troubleshooting
---

# Troubleshooting: GPG Signing Fails in VS Code / Claude Code

## Symptom

Commits fail with the following error in non-interactive terminals:

```
error: gpg failed to sign the data
```

## Diagnosis

Run these checks in order to identify the root cause:

1. **Confirm `pinentry-mac` is installed:**
   ```bash
   which pinentry-mac
   ```

2. **Verify `gpg-agent.conf` specifies the correct pinentry program.** The first matching `pinentry-program` line takes precedence, so order matters:
   ```bash
   cat ~/.gnupg/gpg-agent.conf
   ```

3. **Test whether the GPG agent has a cached passphrase:**
   ```bash
   echo test | gpg --clearsign
   ```
   If this prompts for a passphrase or fails silently, the agent has no cached credentials.

## Fix

### 1. Install `pinentry-mac`

```bash
brew install pinentry-mac
```

### 2. Configure the GPG agent

Add `pinentry-program` as the **first line** of `~/.gnupg/gpg-agent.conf`:

```
pinentry-program /opt/homebrew/bin/pinentry-mac
```

> **Note:** On Intel Macs, the path is `/usr/local/bin/pinentry-mac`. Confirm with `which pinentry-mac`.

### 3. Restart the GPG agent

```bash
gpgconf --kill gpg-agent
```

The agent restarts automatically on the next GPG operation.

## Prevention

Before switching to a non-interactive terminal (VS Code, Claude Code, etc.), prime the passphrase cache from a standard terminal session:

```bash
echo unlock | gpg --clearsign
```

This caches the passphrase for the duration defined by `default-cache-ttl` in `gpg-agent.conf` (default: 600 seconds).

## Related Topics

- Configuring commit signing in Git (`git config --global gpg.program`)
- Extending passphrase cache lifetime via `default-cache-ttl` and `max-cache-ttl`
- Using SSH keys as an alternative to GPG for commit signing
