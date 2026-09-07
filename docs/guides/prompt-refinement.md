# Prompt refinement

Attune can guide the host LLM to gather missing information while helping you
express a request. It uses context you already supplied and asks only when an
answer materially affects the result. Terse prompts and short replies are valid;
you do not need to fill a form for every request.

The feature defaults on in the Claude Code plugin hook. MCP clients receive the
same policy through server instructions and the `prompt_refinement` tool;
automatic behavior depends on the client following those instructions. Reload
the updated plugin or restart the updated MCP server to receive the integration.
The CLI setting alone does not install a host integration.

Say **“turn off prompt refinement”** or run:

```sh
attune config set prompt_refinement false
```

This saves a user-wide preference on the machine running Attune, across projects
and restarts. Re-enable with `true`. Use `attune config show` to see the effective
setting. The separate `ATTUNE_PROMPT_REFINEMENT=false` environment override also
disables it; `true` defers to the saved preference. An invalid setting disables
optional refinement and reports that the preference needs attention.

For one message, say **“skip refinement this time”** or prefix your request:

```text
[no-refine] Summarize the changes in this diff.
```

Skipping refinement keeps normal assistance and necessary task clarification.
It does not change approval requirements. Forms/keyboard preferences remain
separate: you can refine prompts conversationally without forms.

If you ask only to polish a prompt, the intended result is an editable prompt,
with material assumptions visible, and no execution of that prompt. If you
already requested an action, refinement does not require a second authorization
for the same action or permit a broader one.

The feature stores only its setting in `~/.attune/prompt-refinement.json` and
does not log your prompts or make a separate model/API request. Refinement may
add ordinary conversation turns, and its host guidance consumes context. The
host LLM and context tools retain their existing data handling.

Python applications can call `attune.prompt_refinement.refinement_status()` at
their message boundary, pass its instructions to the host LLM, and honor its
`active` state. The library cannot observe prompts a host never passes to it.

## Codex native hook setup

A scripted trial on Codex CLI 0.153.4 verified the existing Attune hook at the
UserPromptSubmit boundary. MCP-only instructions did not reliably trigger a
policy check on ordinary turns. Use a native hook when per-turn delivery is
required; model adherence still needs observation.

For a source checkout with Attune installed in its Python environment, configure
the following in your Codex configuration, replacing both absolute paths:

```toml
[[hooks.UserPromptSubmit]]
[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "/absolute/path/to/venv/bin/python /absolute/path/to/attune-ai/plugin/hooks/prompt_refinement.py"
timeout = 10
```

Quote paths containing spaces using your shell's quoting rules. Use the same
user account and preference location for the hook and Attune MCP server. Restart
the host, review the exact command, and trust it through `/hooks`, as described
in the [Codex hooks documentation](https://learn.chatgpt.com/docs/hooks). The
hook supplies policy; retain the MCP connection or Attune CLI for saved setting
changes. A hook registered but not trusted is not a working integration.

This setup recipe is derived from the successful temporary CLI registration;
normal interactive trust setup and installed desktop behavior still require
validation. The [trial report](../specs/prompt-refinement/live-host-trials.md)
records the exact evidence and remaining UI obligations.
