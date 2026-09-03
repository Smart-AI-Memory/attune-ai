"""`_parse_response` returns a dict or nothing — never an array or scalar.

Found by the 15.1.0 post-release self-review (`bug-predict` run
`ca0c52c6c121`, HIGH). Strategies 1 and 2 returned `json.loads` output
directly from a function typed `-> dict` and documented "never returns
None". A model emitting a fenced JSON ARRAY parses fine, returns a list,
and TypeErrors in `quality_agent.py` / `security_agent.py` — where the
error is swallowed and surfaces as a spurious release-gate failure with
`quality_score 0.0`. The failure mode fires DURING a release, which is
the worst place for it.

Strategy 3 was already safe behind `text.startswith("{")`; it carries a
guard anyway so the contract holds at every return, not only where it
currently must.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.agents.release.release_parsing import _parse_response

# Payloads that are VALID JSON but not objects, in each delimiter shape.
NON_DICT_BODIES = ["[1, 2, 3]", '"a bare string"', "42", "true", "null"]


@pytest.mark.unit
@pytest.mark.parametrize("body", NON_DICT_BODIES)
@pytest.mark.parametrize(
    "wrap",
    [
        lambda b: f"<analysis>{b}</analysis>",  # strategy 1
        lambda b: f"```json\n{b}\n```",  # strategy 2
        lambda b: f"```\n{b}\n```",  # strategy 2, unlabelled
    ],
    ids=["xml", "fenced-json", "fenced-bare"],
)
def test_non_dict_json_never_escapes_as_the_return_value(wrap, body) -> None:
    """A parsable non-dict must fall through, not be returned."""
    result = _parse_response(wrap(body))
    assert isinstance(result, dict), f"{type(result).__name__} escaped the dict contract"


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        '<analysis>{"score": 91}</analysis>',
        '```json\n{"score": 91}\n```',
        '{"score": 91}',
    ],
    ids=["xml", "fenced", "raw"],
)
def test_dict_payloads_still_parse_through_every_strategy(text: str) -> None:
    """The guard must not break the happy path it wraps."""
    assert _parse_response(text)["score"] == 91


@pytest.mark.unit
def test_array_in_xml_falls_through_to_a_later_strategy() -> None:
    """Falling through is the point — a later strategy may still succeed.

    An array inside <analysis> with a regex-extractable metric in the
    surrounding prose should yield the regex result, not the array.
    """
    result = _parse_response("<analysis>[1,2,3]</analysis>\nQuality score: 77")
    assert isinstance(result, dict)
    assert result.get("score") == 77.0


@pytest.mark.unit
def test_unparseable_input_still_returns_a_dict() -> None:
    """The documented floor: never None, always a dict."""
    assert isinstance(_parse_response("no json here at all"), dict)
    assert isinstance(_parse_response(""), dict)
