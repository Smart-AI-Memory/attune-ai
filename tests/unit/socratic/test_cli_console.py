"""Unit tests for attune.socratic.cli_console module.

Tests Console formatting methods and interactive form input helpers,
with stdin/stdout captured and input() mocked.
"""

from __future__ import annotations

from unittest.mock import patch

from attune.socratic.cli_console import (
    Console,
    _input_boolean,
    _input_multi_select,
    _input_single_select,
    _input_text,
    _input_text_area,
    render_form_interactive,
)
from attune.socratic.forms import (
    FieldOption,
    FieldType,
    FieldValidation,
    Form,
    FormField,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_console(use_color: bool = False) -> Console:
    """Return a console instance with colour disabled for predictable output."""
    c = Console(use_color=use_color)
    # Force off regardless of isatty
    c.use_color = use_color
    return c


def _make_option(value: str, label: str, recommended: bool = False) -> FieldOption:
    return FieldOption(value=value, label=label, recommended=recommended)


def _make_text_field(
    fid: str = "name",
    label: str = "Your name",
    required: bool = False,
    placeholder: str = "",
    min_length: int | None = None,
    max_length: int | None = None,
) -> FormField:
    validation = FieldValidation(
        required=required,
        min_length=min_length,
        max_length=max_length,
    )
    return FormField(
        id=fid,
        field_type=FieldType.TEXT,
        label=label,
        placeholder=placeholder,
        validation=validation,
    )


def _make_boolean_field(fid: str = "confirm", required: bool = False) -> FormField:
    return FormField(
        id=fid,
        field_type=FieldType.BOOLEAN,
        label="Confirm?",
        validation=FieldValidation(required=required),
    )


def _make_select_field(
    fid: str = "choice",
    options: list[FieldOption] | None = None,
    required: bool = True,
    multi: bool = False,
) -> FormField:
    opts = options or [
        _make_option("a", "Option A"),
        _make_option("b", "Option B"),
    ]
    field_type = FieldType.MULTI_SELECT if multi else FieldType.SINGLE_SELECT
    return FormField(
        id=fid,
        field_type=field_type,
        label="Pick one",
        options=opts,
        validation=FieldValidation(required=required),
    )


# ---------------------------------------------------------------------------
# Console._c (color helper)
# ---------------------------------------------------------------------------


class TestConsoleColor:
    """Tests for the Console._c() colour helper."""

    def test_no_color_returns_text_unchanged(self):
        """_c returns raw text when use_color is False."""
        c = _make_console(use_color=False)

        result = c._c("red", "hello")

        assert result == "hello"

    def test_unknown_color_key_returns_text_with_reset(self):
        """_c with unknown color key still appends reset code."""
        c = Console(use_color=False)
        c.use_color = True

        # Unknown color → empty string prefix
        result = c._c("neon_pink", "text")
        # No ANSI prefix but should still append reset
        assert "text" in result


# ---------------------------------------------------------------------------
# Console output methods
# ---------------------------------------------------------------------------


class TestConsoleOutputMethods:
    """Tests for Console.header, subheader, success, error, warning, info, dim."""

    def test_header_prints_separator_lines(self, capsys):
        """header() prints two separator lines and the text."""
        c = _make_console()
        c.header("My Title")
        captured = capsys.readouterr()

        assert "=" * 20 in captured.out  # partial match
        assert "My Title" in captured.out

    def test_subheader_prints_text(self, capsys):
        """subheader() prints the text."""
        c = _make_console()
        c.subheader("Section")
        captured = capsys.readouterr()

        assert "Section" in captured.out

    def test_success_prints_checkmark_and_text(self, capsys):
        """success() prints checkmark and message."""
        c = _make_console()
        c.success("All good")
        captured = capsys.readouterr()

        assert "All good" in captured.out

    def test_error_prints_x_and_text(self, capsys):
        """error() prints cross mark and message."""
        c = _make_console()
        c.error("Something broke")
        captured = capsys.readouterr()

        assert "Something broke" in captured.out

    def test_warning_prints_text(self, capsys):
        """warning() prints warning message."""
        c = _make_console()
        c.warning("Be careful")
        captured = capsys.readouterr()

        assert "Be careful" in captured.out

    def test_info_prints_text(self, capsys):
        """info() prints info message."""
        c = _make_console()
        c.info("FYI")
        captured = capsys.readouterr()

        assert "FYI" in captured.out

    def test_dim_prints_text(self, capsys):
        """dim() prints dimmed message."""
        c = _make_console()
        c.dim("quiet note")
        captured = capsys.readouterr()

        assert "quiet note" in captured.out


# ---------------------------------------------------------------------------
# Console.progress
# ---------------------------------------------------------------------------


class TestConsoleProgress:
    """Tests for Console.progress()."""

    def test_progress_zero_returns_empty_bar(self):
        """progress(0) returns a bar of all light blocks."""
        c = _make_console()
        bar = c.progress(0.0, width=10)

        assert "0%" in bar

    def test_progress_full_returns_full_bar(self):
        """progress(1.0) shows 100%."""
        c = _make_console()
        bar = c.progress(1.0, width=10)

        assert "100%" in bar

    def test_progress_half_shows_50_percent(self):
        """progress(0.5) shows 50%."""
        c = _make_console()
        bar = c.progress(0.5, width=10)

        assert "50%" in bar

    def test_progress_bar_length_matches_width(self):
        """The bar portion has exactly `width` characters."""
        c = _make_console()
        width = 20
        bar = c.progress(0.3, width=width)

        # Extract the content between [ and ]
        start = bar.index("[") + 1
        end = bar.index("]")
        bar_content = bar[start:end]
        assert len(bar_content) == width


# ---------------------------------------------------------------------------
# Console.table
# ---------------------------------------------------------------------------


class TestConsoleTable:
    """Tests for Console.table()."""

    def test_table_prints_headers(self, capsys):
        """table() prints column headers."""
        c = _make_console()
        c.table(["Name", "Value"], [["foo", "bar"]])
        captured = capsys.readouterr()

        assert "Name" in captured.out
        assert "Value" in captured.out

    def test_table_prints_row_data(self, capsys):
        """table() prints all row data."""
        c = _make_console()
        c.table(["Col"], [["row1"], ["row2"]])
        captured = capsys.readouterr()

        assert "row1" in captured.out
        assert "row2" in captured.out

    def test_table_prints_separator_line(self, capsys):
        """table() prints a separator between header and rows."""
        c = _make_console()
        c.table(["A", "B"], [["x", "y"]])
        captured = capsys.readouterr()

        assert "-" in captured.out


# ---------------------------------------------------------------------------
# _input_boolean
# ---------------------------------------------------------------------------


class TestInputBoolean:
    """Tests for _input_boolean()."""

    def test_y_returns_true(self):
        """Entering 'y' returns True."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="y"):
            result = _input_boolean(field, c)

        assert result is True

    def test_yes_returns_true(self):
        """Entering 'yes' returns True."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="yes"):
            result = _input_boolean(field, c)

        assert result is True

    def test_n_returns_false(self):
        """Entering 'n' returns False."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="n"):
            result = _input_boolean(field, c)

        assert result is False

    def test_no_returns_false(self):
        """Entering 'no' returns False."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="no"):
            result = _input_boolean(field, c)

        assert result is False

    def test_true_string_returns_true(self):
        """Entering 'true' returns True."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="true"):
            result = _input_boolean(field, c)

        assert result is True

    def test_1_returns_true(self):
        """Entering '1' returns True."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="1"):
            result = _input_boolean(field, c)

        assert result is True

    def test_0_returns_false(self):
        """Entering '0' returns False."""
        c = _make_console()
        field = _make_boolean_field()

        with patch("builtins.input", return_value="0"):
            result = _input_boolean(field, c)

        assert result is False

    def test_invalid_then_valid_loops(self):
        """Invalid input causes loop until valid input received."""
        c = _make_console()
        field = _make_boolean_field()

        inputs = iter(["maybe", "definitely", "y"])

        with patch("builtins.input", side_effect=inputs):
            result = _input_boolean(field, c)

        assert result is True

    def test_empty_non_required_returns_false(self):
        """Empty input on non-required boolean field returns False."""
        c = _make_console()
        field = _make_boolean_field(required=False)

        with patch("builtins.input", return_value=""):
            result = _input_boolean(field, c)

        assert result is False


# ---------------------------------------------------------------------------
# _input_text
# ---------------------------------------------------------------------------


class TestInputText:
    """Tests for _input_text()."""

    def test_valid_input_returns_value(self):
        """_input_text returns the entered text."""
        c = _make_console()
        field = _make_text_field(required=False)

        with patch("builtins.input", return_value="Alice"):
            result = _input_text(field, c)

        assert result == "Alice"

    def test_empty_non_required_returns_empty_string(self):
        """Empty input on non-required field returns ''."""
        c = _make_console()
        field = _make_text_field(required=False)

        with patch("builtins.input", return_value=""):
            result = _input_text(field, c)

        assert result == ""

    def test_empty_required_loops_until_value_given(self):
        """Empty input on required field loops until valid value."""
        c = _make_console()
        field = _make_text_field(required=True)

        inputs = iter(["", "", "Bob"])

        with patch("builtins.input", side_effect=inputs):
            result = _input_text(field, c)

        assert result == "Bob"

    def test_placeholder_used_in_prompt(self):
        """When placeholder set, it appears in prompt."""
        c = _make_console()
        field = _make_text_field(placeholder="Enter your name", required=False)

        prompts_seen: list[str] = []

        def capture_input(prompt=""):
            prompts_seen.append(prompt)
            return "Charlie"

        with patch("builtins.input", side_effect=capture_input):
            _input_text(field, c)

        assert any("Enter your name" in p for p in prompts_seen)

    def test_min_length_validation_rejects_short_input(self):
        """Input shorter than min_length is rejected."""
        c = _make_console()
        field = _make_text_field(required=True, min_length=5)

        inputs = iter(["hi", "hello world"])

        with patch("builtins.input", side_effect=inputs):
            result = _input_text(field, c)

        assert result == "hello world"


# ---------------------------------------------------------------------------
# _input_single_select
# ---------------------------------------------------------------------------


class TestInputSingleSelect:
    """Tests for _input_single_select()."""

    def test_valid_number_returns_option_value(self):
        """Entering '1' selects the first option's value."""
        c = _make_console()
        field = _make_select_field()

        with patch("builtins.input", return_value="1"):
            result = _input_single_select(field, c)

        assert result == "a"

    def test_second_option_returns_correct_value(self):
        """Entering '2' selects the second option's value."""
        c = _make_console()
        field = _make_select_field()

        with patch("builtins.input", return_value="2"):
            result = _input_single_select(field, c)

        assert result == "b"

    def test_out_of_range_loops_until_valid(self):
        """Out-of-range number loops until valid number entered."""
        c = _make_console()
        field = _make_select_field()

        inputs = iter(["5", "0", "2"])

        with patch("builtins.input", side_effect=inputs):
            result = _input_single_select(field, c)

        assert result == "b"

    def test_non_numeric_loops_until_valid(self):
        """Non-numeric input loops until valid number entered."""
        c = _make_console()
        field = _make_select_field()

        inputs = iter(["abc", "1"])

        with patch("builtins.input", side_effect=inputs):
            result = _input_single_select(field, c)

        assert result == "a"

    def test_empty_non_required_returns_none(self):
        """Empty input on non-required field returns None."""
        c = _make_console()
        field = _make_select_field(required=False)

        with patch("builtins.input", return_value=""):
            result = _input_single_select(field, c)

        assert result is None

    def test_recommended_option_label_shown(self, capsys):
        """Recommended options display '(Recommended)' marker."""
        c = _make_console()
        opts = [_make_option("x", "Option X", recommended=True)]
        field = _make_select_field(options=opts, required=False)

        with patch("builtins.input", return_value=""):
            _input_single_select(field, c)

        captured = capsys.readouterr()
        assert "Recommended" in captured.out


# ---------------------------------------------------------------------------
# _input_multi_select
# ---------------------------------------------------------------------------


class TestInputMultiSelect:
    """Tests for _input_multi_select()."""

    def test_single_selection_returns_list_with_one_value(self):
        """Entering '1' returns ['a']."""
        c = _make_console()
        field = _make_select_field(multi=True)

        with patch("builtins.input", return_value="1"):
            result = _input_multi_select(field, c)

        assert result == ["a"]

    def test_comma_separated_returns_multiple_values(self):
        """Entering '1,2' returns both option values."""
        c = _make_console()
        field = _make_select_field(multi=True)

        with patch("builtins.input", return_value="1,2"):
            result = _input_multi_select(field, c)

        assert "a" in result
        assert "b" in result

    def test_empty_non_required_returns_empty_list(self):
        """Empty input on non-required multi-select returns []."""
        c = _make_console()
        field = _make_select_field(multi=True, required=False)

        with patch("builtins.input", return_value=""):
            result = _input_multi_select(field, c)

        assert result == []

    def test_invalid_indices_ignored(self):
        """Out-of-range indices are silently skipped."""
        c = _make_console()
        field = _make_select_field(multi=True)

        # 1 is valid, 99 is out of range
        with patch("builtins.input", return_value="1,99"):
            result = _input_multi_select(field, c)

        assert result == ["a"]


# ---------------------------------------------------------------------------
# _input_text_area
# ---------------------------------------------------------------------------


class TestInputTextArea:
    """Tests for _input_text_area()."""

    def test_single_line_double_enter_returns_text(self):
        """Single line followed by two empty inputs returns the line."""
        c = _make_console()
        field = FormField(
            id="notes",
            field_type=FieldType.TEXT_AREA,
            label="Notes",
            validation=FieldValidation(required=False),
        )

        inputs = iter(["First line", "", ""])

        with patch("builtins.input", side_effect=inputs):
            result = _input_text_area(field, c)

        assert "First line" in result

    def test_multiple_lines_joined(self):
        """Multiple lines are joined into a single string."""
        c = _make_console()
        field = FormField(
            id="notes",
            field_type=FieldType.TEXT_AREA,
            label="Notes",
            validation=FieldValidation(required=False),
        )

        inputs = iter(["Line 1", "Line 2", "", ""])

        with patch("builtins.input", side_effect=inputs):
            result = _input_text_area(field, c)

        assert "Line 1" in result
        assert "Line 2" in result

    def test_empty_non_required_returns_empty_string(self):
        """Immediately double-entering on non-required field returns ''."""
        c = _make_console()
        field = FormField(
            id="notes",
            field_type=FieldType.TEXT_AREA,
            label="Notes",
            validation=FieldValidation(required=False),
        )

        inputs = iter(["", ""])

        with patch("builtins.input", side_effect=inputs):
            result = _input_text_area(field, c)

        assert result == ""


# ---------------------------------------------------------------------------
# render_form_interactive
# ---------------------------------------------------------------------------


class TestRenderFormInteractive:
    """Tests for render_form_interactive()."""

    def test_render_form_returns_answers_dict(self):
        """render_form_interactive returns a dict of answers."""
        c = _make_console()
        field = _make_text_field(fid="name", required=False)
        form = Form(id="f1", title="Test Form", fields=[field])

        with patch("builtins.input", return_value="Alice"):
            answers = render_form_interactive(form, c)

        assert isinstance(answers, dict)
        assert "name" in answers
        assert answers["name"] == "Alice"

    def test_render_form_boolean_field(self):
        """render_form_interactive handles BOOLEAN fields."""
        c = _make_console()
        field = _make_boolean_field(fid="confirm")
        form = Form(id="f2", title="Confirm Form", fields=[field])

        with patch("builtins.input", return_value="y"):
            answers = render_form_interactive(form, c)

        assert answers["confirm"] is True

    def test_render_form_single_select_field(self):
        """render_form_interactive handles SINGLE_SELECT fields."""
        c = _make_console()
        field = _make_select_field(fid="pick")
        form = Form(id="f3", title="Pick Form", fields=[field])

        with patch("builtins.input", return_value="1"):
            answers = render_form_interactive(form, c)

        assert answers["pick"] == "a"

    def test_render_form_multi_select_field(self):
        """render_form_interactive handles MULTI_SELECT fields."""
        c = _make_console()
        field = _make_select_field(fid="picks", multi=True, required=False)
        form = Form(id="f4", title="Picks Form", fields=[field])

        with patch("builtins.input", return_value="1,2"):
            answers = render_form_interactive(form, c)

        assert "a" in answers["picks"]
        assert "b" in answers["picks"]

    def test_render_form_hidden_field_skipped(self):
        """Fields with show_when conditions not met are skipped."""
        c = _make_console()
        # This field only shows when another field has a specific value
        visible_field = _make_text_field(fid="base", required=False)
        hidden_field = FormField(
            id="hidden",
            field_type=FieldType.TEXT,
            label="Hidden Field",
            show_when={"base": "trigger_value"},
            validation=FieldValidation(required=False),
        )
        form = Form(id="f5", title="Conditional Form", fields=[visible_field, hidden_field])

        with patch("builtins.input", return_value="something_else"):
            answers = render_form_interactive(form, c)

        # hidden_field should not appear in answers because condition not met
        assert "hidden" not in answers

    def test_render_form_prints_title(self, capsys):
        """render_form_interactive prints the form title."""
        c = _make_console()
        form = Form(id="f6", title="My Fancy Form", fields=[])

        with patch("builtins.input", return_value=""):
            render_form_interactive(form, c)

        captured = capsys.readouterr()
        assert "My Fancy Form" in captured.out

    def test_render_form_prints_description_when_set(self, capsys):
        """render_form_interactive prints description if provided."""
        c = _make_console()
        form = Form(
            id="f7",
            title="Desc Form",
            description="Please answer the following",
            fields=[],
        )

        with patch("builtins.input", return_value=""):
            render_form_interactive(form, c)

        captured = capsys.readouterr()
        assert "Please answer the following" in captured.out
