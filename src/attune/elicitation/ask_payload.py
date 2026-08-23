"""Tool-ready ``AskUserQuestion`` payloads with this repo's conventions applied.

``attune_forms.form_to_askuserquestion`` renders a :class:`FormSchema` to
BATCHES of question dicts. Turning a batch into an actual tool call still
takes two local conventions, both enforced by the user-level
``ask_question_format_guard`` hook and neither expressible in the shared
package:

1. a batch of more than one question must opt in via ``metadata.source``
   containing ``"form"``; and
2. the FIRST option must be the recommended one and its label must end
   with ``"(Recommended)"``.

Those are host policy, not form semantics — baking them into
``attune-forms`` would impose one consumer's hook on every consumer. So
they live here, in the layer that already registers the host seams.

The point is that a caller cannot forget them. Both rules cost a
round-trip each when missed (observed 2026-08-22: two consecutive guard
rejections on one form), and a convention that holds only when
remembered is a habit, not a convention.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

RECOMMENDED_SUFFIX = "(Recommended)"

#: Marks a payload as a deliberate multi-question form. The guard looks
#: for "form" as a substring, so this value opts in by construction.
DEFAULT_SOURCE = "elicit-form"

#: AskUserQuestion renders this as a short chip; longer values are
#: rejected, so derived headers are truncated to fit.
MAX_HEADER_CHARS = 12

_MULTI_TYPES = frozenset({"multi_select"})


def _header_for(question: dict[str, Any]) -> str:
    """Derive the short chip label from a question's text.

    Prefers the question's own words over its id — ``"Binding"`` reads
    better than ``"binding_surface"`` — and truncates rather than
    raising, because a too-long header is a rejected tool call.
    """
    label = str(question.get("question") or question.get("question_id") or "Choose")
    label = label.strip().rstrip("?:").strip()
    if len(label) <= MAX_HEADER_CHARS:
        return label
    # Keep whole words where one fits; a hard slice is the fallback.
    words = label.split()
    if words and len(words[0]) <= MAX_HEADER_CHARS:
        out = words[0]
        for word in words[1:]:
            if len(out) + 1 + len(word) > MAX_HEADER_CHARS:
                break
            out = f"{out} {word}"
        return out
    return label[:MAX_HEADER_CHARS]


def mark_recommended(label: str) -> str:
    """Return ``label`` carrying the recommendation marker exactly once."""
    label = label.strip()
    if label.endswith(RECOMMENDED_SUFFIX):
        return label
    return f"{label} {RECOMMENDED_SUFFIX}"


def _options_for(
    question: dict[str, Any],
    descriptions: dict[str, str] | None,
) -> list[dict[str, str]]:
    """Build the option objects, marking the FIRST as recommended.

    First-is-recommended is the guard's rule, so the ordering the caller
    chose IS the recommendation — this never reorders, it only labels.
    """
    out: list[dict[str, str]] = []
    for index, raw in enumerate(question.get("options") or []):
        label = str(raw)
        description = (descriptions or {}).get(label, "")
        out.append(
            {
                "label": mark_recommended(label) if index == 0 else label,
                "description": description,
            }
        )
    return out


def form_to_ask_payload(
    form: Any,
    *,
    source: str = DEFAULT_SOURCE,
    descriptions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Render ``form`` to tool-ready ``AskUserQuestion`` payloads.

    Args:
        form: The :class:`FormSchema` to render.
        source: Value for ``metadata.source``. Must contain ``"form"`` or
            the guard rejects any batch of more than one question.
        descriptions: Optional ``option label -> description`` map. Select
            options are plain strings in the schema, so per-option prose
            has nowhere else to live; unmapped options get ``""`` rather
            than invented text.

    Returns:
        One payload dict per batch, each ready to pass straight to the
        tool.

    Raises:
        ValueError: If ``source`` could not opt a batch in — failing here
            beats a guard rejection at call time, which costs a turn.
    """
    if "form" not in source:
        raise ValueError(
            f"source={source!r} does not contain 'form'; a batch of more than "
            "one question would be rejected by the format guard"
        )

    from attune.elicitation import form_to_askuserquestion

    payloads: list[dict[str, Any]] = []
    for batch in form_to_askuserquestion(form):
        questions = [
            {
                "question": str(q.get("question") or ""),
                "header": _header_for(q),
                "multiSelect": q.get("type") in _MULTI_TYPES,
                "options": _options_for(q, descriptions),
            }
            for q in batch
        ]
        payloads.append({"questions": questions, "metadata": {"source": source}})
    return payloads
