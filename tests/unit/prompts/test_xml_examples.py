"""Tests for one-shot example rendering in XML prompts.

Verifies that examples flow from PromptContext through XmlPromptTemplate
and that factory methods include defaults.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.prompts.context import PromptContext
from attune.prompts.examples import (
    BUG_PREDICT_EXAMPLES,
    CODE_REVIEW_EXAMPLES,
    DEPENDENCY_CHECK_EXAMPLES,
    PERF_AUDIT_EXAMPLES,
    REFACTOR_PLAN_EXAMPLES,
    RELEASE_PREP_EXAMPLES,
    SECURITY_AUDIT_EXAMPLES,
)
from attune.prompts.templates import XmlPromptTemplate


@pytest.mark.unit
class TestXmlExamplesRendering:
    """Tests for <examples> rendering in XmlPromptTemplate."""

    def test_renders_examples_section(self) -> None:
        """Verify <examples> tag appears when examples are provided."""
        ctx = PromptContext(
            role="tester",
            goal="test examples",
            examples=[{"input": "x = 1", "output": "Looks fine"}],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        assert "<examples>" in rendered
        assert "</examples>" in rendered
        assert "<sample_input>" in rendered
        assert "<expected_output>" in rendered

    def test_no_examples_section_when_empty(self) -> None:
        """Verify no <examples> tag when examples list is empty."""
        ctx = PromptContext(
            role="tester",
            goal="test no examples",
            examples=[],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        assert "<examples>" not in rendered

    def test_no_examples_section_by_default(self) -> None:
        """Verify no <examples> tag when examples not provided at all."""
        ctx = PromptContext(
            role="tester",
            goal="test default",
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        assert "<examples>" not in rendered

    def test_example_content_in_cdata(self) -> None:
        """Verify example input/output are wrapped in CDATA."""
        ctx = PromptContext(
            role="tester",
            goal="test cdata",
            examples=[{"input": "eval(x)", "output": "Finding: eval usage"}],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        assert "<![CDATA[eval(x)]]>" in rendered
        assert "<![CDATA[Finding: eval usage]]>" in rendered

    def test_cdata_escaping_in_examples(self) -> None:
        """Verify ]]> in example content is properly escaped."""
        ctx = PromptContext(
            role="tester",
            goal="test cdata escape",
            examples=[{"input": "data]]>more", "output": "ok"}],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        # ]]> should be escaped as ]]]]><![CDATA[>
        assert "data]]]]><![CDATA[>more" in rendered

    def test_multiple_examples(self) -> None:
        """Verify multiple examples render with sequential numbering."""
        ctx = PromptContext(
            role="tester",
            goal="test multi",
            examples=[
                {"input": "a", "output": "1"},
                {"input": "b", "output": "2"},
            ],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        assert 'example number="1"' in rendered
        assert 'example number="2"' in rendered

    def test_examples_appear_before_input(self) -> None:
        """Verify examples section comes before the <input> section."""
        ctx = PromptContext(
            role="tester",
            goal="test ordering",
            input_payload="actual task data",
            examples=[{"input": "sample", "output": "expected"}],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        examples_pos = rendered.index("<examples>")
        input_pos = rendered.index('<input type="code">')
        assert examples_pos < input_pos

    def test_examples_appear_after_constraints(self) -> None:
        """Verify examples section comes after the </constraints> section."""
        ctx = PromptContext(
            role="tester",
            goal="test ordering",
            constraints=["rule 1"],
            examples=[{"input": "sample", "output": "expected"}],
        )
        template = XmlPromptTemplate(name="test")
        rendered = template.render(ctx)

        constraints_pos = rendered.index("</constraints>")
        examples_pos = rendered.index("<examples>")
        assert constraints_pos < examples_pos


@pytest.mark.unit
class TestPromptContextExamples:
    """Tests for examples field on PromptContext."""

    def test_examples_default_empty(self) -> None:
        """Verify examples defaults to empty list."""
        ctx = PromptContext(role="tester", goal="test")
        assert ctx.examples == []

    def test_examples_round_trip(self) -> None:
        """Verify examples field round-trips through construction."""
        examples = [{"input": "x", "output": "y"}]
        ctx = PromptContext(role="tester", goal="test", examples=examples)
        assert ctx.examples == examples

    def test_with_extra_preserves_examples(self) -> None:
        """Verify with_extra() carries examples to the new context."""
        examples = [{"input": "a", "output": "b"}]
        ctx = PromptContext(role="tester", goal="test", examples=examples)
        new_ctx = ctx.with_extra(foo="bar")

        assert new_ctx.examples == examples
        assert new_ctx.extra["foo"] == "bar"
        # Verify it's a copy, not the same reference
        assert new_ctx.examples is not ctx.examples


@pytest.mark.unit
class TestFactoryMethodDefaults:
    """Tests that factory methods include default one-shot examples."""

    def test_security_audit_includes_examples(self) -> None:
        """Verify for_security_audit() includes SECURITY_AUDIT_EXAMPLES."""
        ctx = PromptContext.for_security_audit(code="x = 1")
        assert ctx.examples == SECURITY_AUDIT_EXAMPLES
        assert len(ctx.examples) >= 1

    def test_code_review_includes_examples(self) -> None:
        """Verify for_code_review() includes CODE_REVIEW_EXAMPLES."""
        ctx = PromptContext.for_code_review(code_or_diff="x = 1")
        assert ctx.examples == CODE_REVIEW_EXAMPLES
        assert len(ctx.examples) >= 1

    def test_perf_audit_includes_examples(self) -> None:
        """Verify for_perf_audit() includes PERF_AUDIT_EXAMPLES."""
        ctx = PromptContext.for_perf_audit(code="x = 1")
        assert ctx.examples == PERF_AUDIT_EXAMPLES
        assert len(ctx.examples) >= 1

    def test_research_has_no_examples(self) -> None:
        """Verify for_research() has empty examples (too open-ended)."""
        ctx = PromptContext.for_research(question="Why?")
        assert ctx.examples == []

    def test_security_audit_custom_examples(self) -> None:
        """Verify for_security_audit() accepts custom examples override."""
        custom = [{"input": "custom", "output": "custom"}]
        ctx = PromptContext.for_security_audit(code="x = 1", examples=custom)
        assert ctx.examples == custom

    def test_code_review_custom_examples(self) -> None:
        """Verify for_code_review() accepts custom examples override."""
        custom = [{"input": "custom", "output": "custom"}]
        ctx = PromptContext.for_code_review(code_or_diff="x = 1", examples=custom)
        assert ctx.examples == custom

    def test_perf_audit_custom_examples(self) -> None:
        """Verify for_perf_audit() accepts custom examples override."""
        custom = [{"input": "custom", "output": "custom"}]
        ctx = PromptContext.for_perf_audit(code="x = 1", examples=custom)
        assert ctx.examples == custom


@pytest.mark.unit
class TestExampleConstants:
    """Tests that example constants are well-formed."""

    @pytest.mark.parametrize(
        "examples",
        [
            SECURITY_AUDIT_EXAMPLES,
            CODE_REVIEW_EXAMPLES,
            BUG_PREDICT_EXAMPLES,
            PERF_AUDIT_EXAMPLES,
            RELEASE_PREP_EXAMPLES,
            DEPENDENCY_CHECK_EXAMPLES,
            REFACTOR_PLAN_EXAMPLES,
        ],
        ids=[
            "security",
            "code-review",
            "bug-predict",
            "perf",
            "release-prep",
            "dependency-check",
            "refactor-plan",
        ],
    )
    def test_examples_have_input_and_output(self, examples: list[dict[str, str]]) -> None:
        """Verify each example constant has input and output keys."""
        assert len(examples) >= 1
        for example in examples:
            assert "input" in example, "Example missing 'input' key"
            assert "output" in example, "Example missing 'output' key"
            assert len(example["input"]) > 0, "Example input is empty"
            assert len(example["output"]) > 0, "Example output is empty"
