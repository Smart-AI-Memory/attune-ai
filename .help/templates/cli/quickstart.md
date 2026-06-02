---
type: quickstart
name: cli-quickstart
feature: cli
depth: quickstart
generated_at: 2026-06-02T10:56:02.737376+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Quickstart: attune CLI

Run your first attune command and route user input to a skill in under a minute.

```bash
attune version
```

Expected output:

```
attune x.y.z
```

## Prerequisites

- attune is installed and available on your `PATH`
- You have a terminal open in your project directory

## Step 1: Verify your setup

Run the doctor command to confirm everything is configured correctly:

```bash
attune doctor
```

If the output shows no errors, you're ready to proceed.

## Step 2: Check today's costs

```bash
attune costs today
```

This calls `cmd_costs_today` and prints a summary of your AI usage costs for the current day.

## Step 3: Route user input programmatically

Use `route_user_input` to send a plain-language string to the appropriate skill:

```python
from attune.cli_router import route_user_input

result = route_user_input("show me my lessons")
print(result)
```

Expected output is a dict describing the routed skill and any arguments resolved from your input.

## Step 4: Teach the router a custom shortcut

```python
from attune.cli_router import HybridRouter

router = HybridRouter()
router.learn_preference(keyword="costs", skill="cmd_costs_today")
result = router.route("costs")
print(result)
```

`learn_preference` stores a `RoutingPreference` entry (with fields `keyword`, `skill`, `args`, `usage_count`, and `confidence`) so the router recognises your shorthand on every future call.

## What you just did

- Confirmed your installation with `cmd_doctor`
- Viewed a cost summary with `cmd_costs_today`
- Routed plain-language input with `route_user_input`
- Registered a custom routing shortcut with `HybridRouter.learn_preference`

Next: say **"how do I configure routing preferences?"** for a full walkthrough of `HybridRouter`, `RoutingPreference` fields, and persistent preference storage.
