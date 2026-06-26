---
description: Branches that resist 100% coverage are signal, not noise. Across 78 modules, 15 production bugs surfaced — most of them dead "defensive" code with four named sub-patterns.
---

# Coverage Isn't About Coverage

**Draft for Developer Blog**

---

## A Function That Crashed Every Time It Was Called

A public method in a codebase I was pushing toward 100% coverage crashed on every call. The test suite was green.

```python
# in a team-composition helper (since removed)
plan_dict = {
    "name": f"team-{plan.strategy.value}",
    "strategy": plan.strategy.value,
    "agents": [{"template_id": t.id, "role": t.role} for t in plan.agents],
    "quality_gates": plan.quality_gates,
    "phases": plan.phases,  # the plan object had no `phases` field
}
```

Every call to `compose_team()` raised `AttributeError` the moment it touched `plan.phases`. It had been there since the method was written. It surfaced because I tried to write a test for it — and the test crashed before the first assertion.

The thesis: **branches that resist 100% coverage are signal, not noise.** When you can't easily get a test to reach a line, the line is usually broken or dead. Pushing toward 100% turns coverage from a vanity metric into an adversarial reading of your own code.

I've now done this on 78 modules in one codebase. Fifteen bugs surfaced — about one in five modules — and they sort cleanly into three classes.

---

## The Three Classes

**Class 1: Crash paths nobody triggered.** Production code that throws on real input, but no test exercised the path. `compose_team()` is the canonical example. `Console.table()` was another — it raised `IndexError` whenever a row had more cells than headers, because the guard existed in the width-calculation loop but had been forgotten in the print loop. A third: `_generate_success_criteria()`, which constructed a `SuccessMetric()` without its required `description` argument and would have crashed the moment it ran.

These are easy bugs to explain but hard to find by reading. They look fine. The function signature is plausible, the variable names match, the surrounding code is correct. The only way to surface them is to make the runtime do the work — which is what tests are for, except no test was hitting that path.

**Class 2: Dead code wearing defensive-coding clothes.** Code that *looks* defensive but is unreachable, which means it's also untested, which means if its assumptions ever changed it couldn't actually defend anything. Eleven of the fifteen bugs I found were this class. The taxonomy is the rest of this post.

**Class 3: Tests that mocked around the bug.** The test suite passes. Coverage looks fine. The production code is broken, and the tests are the *reason* you can't see it — they mock the pathological caller out of existence. This is the worst kind, because the safety net is lying to you.

---

## The Class 2 Taxonomy

The interesting thing about Class 2 isn't the volume — it's that the dead code keeps falling into the same four shapes. Eleven instances across unrelated modules, four shapes. The patterns are clear enough to name.

### 2A — Defensive default after exhaustive enum dispatch

A function switches on an `Enum`, handles every value explicitly, then has a trailing default for "future-proofing":

```python
if format == OutputFormat.TEXT:
    return explanation.to_text()
if format == OutputFormat.MARKDOWN:
    return explanation.to_markdown()
if format == OutputFormat.HTML:
    return explanation.to_html()
if format == OutputFormat.JSON:
    return json.dumps(explanation.to_dict())
return explanation.to_markdown()  # ← dead
```

`OutputFormat` has exactly four values. All four are checked. The trailing `return` cannot fire. It looks like good defensive coding. It is not.

The mental model that produces this code is "if I add a fifth enum value later, the default catches it." That model is wrong on both ends. Adding a fifth enum value should *break the test suite at the new branch*, not silently produce a wrong default — the dead default suppresses the signal you'd otherwise get. And the default is itself untested, so if it ever does fire you have no idea what it actually does in practice.

Four times across `meta_orch_estimation`, `meta_orch_analysis`, `explainer`, and `ab_testing/allocator`. Every instance got removed.

### 2B — Post-loop fallback after a loop that always returns or raises

A `for ... try/except` loop where every body path either returns or raises, with a "just in case" block underneath:

```python
for attempt in range(1, config.max_attempts + 1):
    try:
        return await func(*args, **kwargs)
    except config.retryable_exceptions as e:
        if attempt == config.max_attempts:
            raise
        await asyncio.sleep(delay)

if last_exception:        # ← dead
    raise last_exception  # ← dead
raise RuntimeError(...)
```

The loop guarantees exit through `return` or `raise`. The post-loop block can only fire if `range()` produced an empty iterator — i.e. `max_attempts < 1`, an invalid input that should be validated up front, not handled with a pseudo-defensive shim three layers down.

Three sibling functions in `retry.py` had this same dead block, copy-pasted across them. All three got removed. The meaningful `RuntimeError` for the empty-range case stays as a single line.

### 2C — Defensive divisor guard where the divisor is structurally non-zero

The classic `if x > 0:` before a division, where every code path that creates the entry also increments past 0:

```python
def add_failure(self, key: str) -> None:
    self.failures[key] = self.failures.get(key, 0) + 1

def failure_rate(self, key: str) -> float:
    failure_count = self.failures.get(key, 0)
    if failure_count > 0:                 # ← dead
        return failure_count / total      # ← dead
    return 0.0
```

If the entry exists, `add_failure` already incremented it past 0. If the entry doesn't exist, `.get(key, 0)` returns 0 and we hit the `else`. The intermediate `if failure_count > 0:` over a value pulled from a structure that only ever stores positive counts is unreachable.

Four instances across `telemetry/analytics.py` and `pattern_learner.py`. The fix is to delete the guard and trust the data structure's invariants. If you're worried the invariants might break, write a test that asserts them — don't paper over it with a runtime check that can't actually fire.

### 2D — Filter on already-filtered data

A `filter(...)` or `[x for x in ... if x]` over a sequence whose construction already excluded the falsy values:

```python
def get_active_models(self) -> list[Model]:
    models = [m for m in self._models if m.enabled]
    return [m for m in models if m]   # ← dead
```

The first comprehension only keeps `m` when `m.enabled` is truthy, which means `m` is non-None (you can't access `.enabled` on `None`). The second filter has nothing to do.

Only one in this codebase (in `provider_config.py`), but the shape is common enough elsewhere that I'd bet it's underreported.

---

## The Common Cause

These four sub-patterns are all the same mental error: **conflating defensiveness with safety.**

Defensive code is supposed to handle the case where the real world doesn't match your assumptions. Code that can't be reached can't handle anything — it's visual noise that *suppresses* the signal you'd otherwise get when assumptions break. A test that fails because a new enum value isn't handled is useful. A silent default returning something plausible is dangerous. A divisor guard over a structurally-positive number isn't a guard; it's a comment that's been promoted to runtime.

The forcing function of 100% coverage is what surfaces all of this. As long as you tolerate 90%, dead defensive code blends into the gap. Push past it and every line either earns its keep or doesn't, and the ones that don't tell you something.

---

## Class 3 — When Tests Are the Bug

The worst bug I found wasn't in production code at all. It was in `feedback_collector.py`, where `get_insights()` called `_generate_recommendations()`, which called back into `get_insights()`. Infinite recursion. Stack overflow on the very first real call.

The tests were green. Coverage was acceptable. The reason: every test of `get_insights` had `_generate_recommendations` mocked out, and every test of `_generate_recommendations` had `get_insights` mocked out. Each function's test suite stood up the half of the cycle that didn't include itself, and the recursion never ran.

I found it because pushing toward 100% coverage meant writing the *integrated* path — calling `get_insights` without mocking the recursive caller. The function blew the stack immediately. The fix was to extract a `_compute_domain_insights()` helper and break the cycle.

The unsettling part isn't that the bug existed. It's that the test suite was *concealing* it. Coverage said "this is fine." The branches were all hit, the assertions all passed, the CI was green for years. The protection wasn't holding the bug out — it was holding the bug in, where no one would notice.

Class 3 is the rarest of the three. It's also the one that should keep you up at night, because it implies your tests-passing signal is sometimes inverted.

---

## What Coverage Is For

The pitch isn't "100% coverage prevents bugs." It doesn't, and chasing it for its own sake is how you end up with a test suite that's all assertions and no judgment. The pitch is that 100% coverage is a forcing function. It makes you read your code adversarially. It surfaces the four-line block that nobody can justify, the for-loop fallback that can't fire, and the recursive cycle the tests have been mocking around.

Most of the bugs you'll find aren't dramatic. They're often "remove these four lines." But they compound: a codebase full of dead defensive code teaches the next engineer to write more dead defensive code, because that's the local convention. The pattern propagates.

Fifteen bugs across 78 modules is a small sample — enough to claim the pattern, not the rate. My guess: 19% is higher in older code and lower in newer code, and roughly constant across teams, because the four sub-patterns of Class 2 are deep human reflexes about what "good defensive code" looks like, not anything specific to this project.

If you try it on your own codebase, the bug log format that worked for me was simple: `(module, starting %, bugs found, bug class)` per session, appended to one markdown file. Three sessions in, you have a real dataset. No experiment overhead. The patterns name themselves.

---

*This post is based on a real coverage push across the [attune-ai](https://github.com/Smart-AI-Memory/attune-ai) codebase. The bug log lives in the repo at `docs/COVERAGE_BUG_LOG.md` and continues to grow.*
