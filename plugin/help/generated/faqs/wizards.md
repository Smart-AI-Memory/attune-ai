---
name: wizards
source: content/features/wizards.md
tags:
- wizards
- interactive
type: faq
---

# Wizards FAQ

## How do I run a wizard?

`get_wizard(id)` returns the class; instantiate it and
`await run()`. Or use the `/wizard` skill in a conversation. There's
no `attune wizard` CLI command.

## Which wizards ship built in?

Five — `debug`, `refactor`, `release-prep`, `security`,
`test-gen` (`list_wizards()` to confirm).

## Are the calls async?

`run()` is a coroutine — `await` it. The registry functions
(`list_wizards`, `get_wizard`) are synchronous.

## Is there a `WizardRegistry` class?

No. The registry is module-level functions in
`attune.wizards` (`list_wizards`, `get_wizard`, `register_wizard`,
`save_custom_wizard`, `delete_custom_wizard`).

## How do I add my own wizard?

Subclass `BaseWizard` and `register_wizard(id, cls)`, or build
a `ConfigDrivenWizard` / `save_custom_wizard(data)`.
