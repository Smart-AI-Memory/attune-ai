"""Unit tests for the Adaptive Friction Matrix system."""

from attune.orchestration.friction import (
    AmbiguityEvaluator,
    BlastRadiusClassifier,
    FrictionDirective,
    FrictionMatrix,
    FrictionZone,
)


class TestBlastRadiusClassifier:
    """Tests for BlastRadiusClassifier."""

    def test_read_only_command_low_risk(self) -> None:
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_command("ls -la") == 1
        assert classifier.evaluate_command("pytest tests/unit") == 1
        assert classifier.evaluate_command("git status") == 1

    def test_destructive_command_high_risk(self) -> None:
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_command("rm -rf src/attune") == 5
        assert classifier.evaluate_command("git reset --hard HEAD~1") == 5
        assert classifier.evaluate_command("DROP TABLE users;") == 5

    def test_destructive_flag_variants(self) -> None:
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_command("rm -fr build/") == 5
        assert classifier.evaluate_command("rm -r -f build/") == 5
        assert classifier.evaluate_command("git push --force origin main") == 5
        assert classifier.evaluate_command("git push -f origin main") == 5

    def test_chained_command_cannot_hide_behind_readonly_prefix(self) -> None:
        # Regression: a read-only first token must not short-circuit
        # classification of what comes after the chain operator.
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_command("ls && rm -rf /tmp/x") == 5
        assert classifier.evaluate_command("git status; git reset --hard") == 5
        assert classifier.evaluate_command("cat notes.md > /etc/hosts") >= 1
        assert classifier.evaluate_command("ls | xargs rm -rf") == 5

    def test_chained_readonly_is_not_scored_readonly(self) -> None:
        classifier = BlastRadiusClassifier()
        # Not destructive, but chained — must not take the read-only
        # fast path (score falls through to modification scoring).
        assert classifier.evaluate_command("git status && git commit -m x") == 3

    def test_critical_path_high_risk(self) -> None:
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_file_path("src/attune/auth/login.py") >= 4
        assert classifier.evaluate_file_path("database/migrations/001.sql") >= 4
        assert classifier.evaluate_file_path("AGENTS.md") >= 4
        assert classifier.evaluate_file_path(".env.production") >= 4

    def test_critical_path_requires_segment_boundary(self) -> None:
        # Regression: "oauth/" must not match the "auth/" rule.
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_file_path("docs/oauth/notes.md") == 1
        assert classifier.evaluate_file_path("docs/envelope.md") == 1

    def test_windows_style_path_normalized(self) -> None:
        # Backslash-separated paths must classify like POSIX paths.
        classifier = BlastRadiusClassifier(workspace_root="C:\\repo")
        rel = classifier._sanitize_and_relativize("src\\attune\\auth\\login.py")
        assert "\\" not in rel

    def test_normal_file_edit(self) -> None:
        classifier = BlastRadiusClassifier()
        assert classifier.evaluate_file_path("docs/readme.md") == 1

    def test_file_deletion_escalates_risk(self) -> None:
        classifier = BlastRadiusClassifier()
        normal_edit = classifier.evaluate_file_path("src/attune/utils.py", is_deletion=False)
        deletion = classifier.evaluate_file_path("src/attune/utils.py", is_deletion=True)
        assert deletion > normal_edit


class TestAmbiguityEvaluator:
    """Tests for AmbiguityEvaluator."""

    def test_specific_prompt_high_clarity(self) -> None:
        evaluator = AmbiguityEvaluator()
        prompt = (
            "Add type hints and docstring to function calculate_total " "in file utils.py line 45"
        )
        assert evaluator.evaluate_prompt(prompt, target_path="utils.py") >= 4

    def test_generic_prompt_low_clarity(self) -> None:
        evaluator = AmbiguityEvaluator()
        assert evaluator.evaluate_prompt("fix this") <= 2
        assert evaluator.evaluate_prompt("clean up") <= 2

    def test_empty_prompt_minimum_clarity(self) -> None:
        evaluator = AmbiguityEvaluator()
        assert evaluator.evaluate_prompt("") == 1

    def test_indicator_matching_uses_word_boundaries(self) -> None:
        # Regression: "pipeline"/"latest"/"prototype" must not count as
        # the indicators "line"/"test"/"type".
        evaluator = AmbiguityEvaluator()
        embedded = evaluator.evaluate_prompt("the latest pipeline prototype needs attention please")
        assert embedded == 3  # no indicator bonus


class TestFrictionMatrix:
    """Tests for FrictionMatrix zone mapping."""

    def test_zone_1_autonomous_routing(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(
            user_prompt="Format docstring in docs/readme.md with line references",
            target_path="docs/readme.md",
        )
        assert result["zone"] == FrictionZone.ZONE_1_AUTONOMOUS.value
        assert result["directive"] == FrictionDirective.ALLOW_AUTONOMOUS.value

    def test_zone_2_inform_proceed_routing(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(user_prompt="tidy up the docs a bit")
        assert result["zone"] == FrictionZone.ZONE_2_INFORM_PROCEED.value
        assert result["directive"] == FrictionDirective.INFORM_AND_PROCEED.value

    def test_zone_3_plan_gate_routing(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(
            user_prompt=(
                "Delete the deprecated helper function in module utils, "
                "file src/attune/auth/legacy.py, and update the test"
            ),
            target_path="src/attune/auth/legacy.py",
        )
        assert result["zone"] == FrictionZone.ZONE_3_PLAN_GATE.value
        assert result["directive"] == FrictionDirective.PLAN_REVIEW_GATE.value

    def test_zone_4_socratic_gate_routing(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(
            user_prompt="clean up",
            target_path="src/attune/auth/security.py",
            is_deletion=True,
        )
        assert result["zone"] == FrictionZone.ZONE_4_SOCRATIC_GATE.value
        assert result["directive"] == FrictionDirective.SOCRATIC_GATE.value

    def test_command_evaluation_matrix(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(
            user_prompt=(
                "Run pytest test suite on file "
                "tests/unit/orchestration/test_friction_matrix.py line 10"
            ),
            command_line="pytest tests/unit",
        )
        assert result["directive"] == FrictionDirective.ALLOW_AUTONOMOUS.value

    def test_result_contains_all_fields(self) -> None:
        matrix = FrictionMatrix()
        result = matrix.evaluate_action(user_prompt="check", command_line="ls")
        assert set(result) == {
            "blast_radius",
            "clarity",
            "zone",
            "directive",
            "reason",
        }
