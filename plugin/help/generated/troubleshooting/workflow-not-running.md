---
name: workflow-not-running
source: common support pattern
summary: This template provides diagnostic steps and solutions for resolving issues
  when the `attune workflow run` command fails to execute, covering authentication
  verification, workflow validation, and environment configuration.
tags:
- workflow
- auth
- setup
type: troubleshooting
---

# Troubleshooting: Workflow Won't Run

## Symptom

Running `attune workflow run <name>` produces no output or returns an authentication error.

## Diagnosis

Work through the following checks in order:

1. **Confirm your API key is set:**
   ```sh
   echo $ANTHROPIC_API_KEY
   ```
   An empty response means the variable is not exported in the current shell session.

2. **Verify the workflow name exists:**
   ```sh
   attune workflow list
   ```
   Confirm that `<name>` appears exactly as listed — names are case-sensitive.

3. **Check your authentication strategy:**
   ```sh
   attune auth status
   ```
   This reports whether you are using an API key, a subscription token, or no active credentials.

4. **Run a full environment check:**
   ```sh
   attune doctor
   ```
   This command inspects your configuration, connectivity, and credentials, and prints actionable suggestions for any issues it finds.

## Fix

Apply the resolution that matches your authentication strategy:

- **API key authentication** — export your key in the current shell session:
  ```sh
  export ANTHROPIC_API_KEY=your-key-here
  ```

- **Subscription authentication** — complete the interactive setup flow:
  ```sh
  attune auth setup
  ```

After applying a fix, re-run `attune doctor` to confirm the issue is resolved before retrying the workflow.

## Prevention

To avoid losing your API key between sessions, add the export statement to your shell profile:

- **Zsh:** `~/.zshrc`
- **Bash:** `~/.bashrc` or `~/.bash_profile`

After editing your profile, reload it with `source ~/.zshrc` (or the equivalent for your shell).

> **Security note:** Avoid committing your API key to version control. Consider using a secrets manager or a `.env` file excluded by `.gitignore` for project-level configuration.

## Related Topics

- [Authentication overview](../auth/overview.md)
- [Configuring environment variables](../config/env-vars.md)
- [`attune doctor` reference](../cli/doctor.md)
