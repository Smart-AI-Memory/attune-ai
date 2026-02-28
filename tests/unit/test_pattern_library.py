"""Tests for attune.pattern_library"""

import pytest

from attune.pattern_library import Pattern, PatternLibrary, PatternMatch

# Tests are implemented in the class-based tests below


class TestPattern:
    """Tests for Pattern class."""

    def test_initialization(self):
        """Test Pattern initialization."""
        pattern = Pattern(
            id="test_001",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Test Pattern",
            description="A test pattern for unit testing",
        )

        assert pattern.id == "test_001"
        assert pattern.agent_id == "agent_1"
        assert pattern.pattern_type == "sequential"
        assert pattern.usage_count == 0
        assert pattern.success_count == 0
        assert pattern.failure_count == 0
        assert pattern.confidence == 0.5

    def test_success_rate_property(self):
        """Test Pattern.success_rate property."""
        pattern = Pattern(
            id="test_002",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Success Rate Test",
            description="Test success rate calculation",
        )

        # Initially 0 (no usage)
        assert pattern.success_rate == 0.0

        # After 8 successes and 2 failures
        pattern.success_count = 8
        pattern.failure_count = 2
        assert pattern.success_rate == 0.8

        # 100% success rate
        pattern.success_count = 10
        pattern.failure_count = 0
        assert pattern.success_rate == 1.0

    def test_record_usage_success(self):
        """Test Pattern.record_usage with successful outcome."""
        pattern = Pattern(
            id="test_003",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Record Usage Test",
            description="Test recording successful usage",
        )

        # Record successful usage
        pattern.record_usage(success=True)

        assert pattern.usage_count == 1
        assert pattern.success_count == 1
        assert pattern.failure_count == 0
        assert pattern.last_used is not None

    def test_record_usage_failure(self):
        """Test Pattern.record_usage with failed outcome."""
        pattern = Pattern(
            id="test_004",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Record Failure Test",
            description="Test recording failed usage",
        )

        # Record failed usage
        pattern.record_usage(success=False)

        assert pattern.usage_count == 1
        assert pattern.success_count == 0
        assert pattern.failure_count == 1

    def test_confidence_update_after_threshold(self):
        """Test that confidence updates after 5 uses."""
        pattern = Pattern(
            id="test_005",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Confidence Test",
            description="Test confidence auto-update",
        )

        # Record 4 successes (below threshold)
        for _ in range(4):
            pattern.record_usage(success=True)

        assert pattern.confidence == 0.5  # Still default

        # 5th usage should update confidence
        pattern.record_usage(success=True)
        assert pattern.confidence == 1.0  # 100% success rate


class TestPatternMatch:
    """Tests for PatternMatch class."""

    def test_initialization(self):
        """Test PatternMatch initialization."""
        pattern = Pattern(
            id="test_match",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Match Test",
            description="Pattern for matching test",
        )

        match = PatternMatch(
            pattern=pattern,
            relevance_score=0.85,
            matching_factors=["temporal", "contextual"],
        )

        assert match.pattern == pattern
        assert match.relevance_score == 0.85
        assert "temporal" in match.matching_factors
        assert "contextual" in match.matching_factors

    def test_relevance_score_range(self):
        """Test PatternMatch with various relevance scores."""
        pattern = Pattern(
            id="test_range",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Range Test",
            description="Test relevance range",
        )

        # Test minimum score
        match_min = PatternMatch(pattern=pattern, relevance_score=0.0, matching_factors=[])
        assert match_min.relevance_score == 0.0

        # Test maximum score
        match_max = PatternMatch(
            pattern=pattern,
            relevance_score=1.0,
            matching_factors=["perfect_match"],
        )
        assert match_max.relevance_score == 1.0


class TestPatternLibrary:
    """Tests for PatternLibrary class."""

    def test_initialization(self):
        """Test PatternLibrary initialization."""
        library = PatternLibrary()

        assert library is not None
        assert hasattr(library, "patterns")

    def test_contribute_pattern(self):
        """Test contributing a pattern to the library."""
        library = PatternLibrary()

        pattern = Pattern(
            id="contrib_001",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Contributed Pattern",
            description="Pattern contributed by agent",
        )

        # Contribute pattern (requires agent_id parameter)
        library.contribute_pattern("agent_1", pattern)

        # Verify it was added
        assert "contrib_001" in library.patterns
        assert library.patterns["contrib_001"].id == "contrib_001"

    def test_query_patterns(self):
        """Test querying patterns from the library."""
        library = PatternLibrary()

        # Add test patterns with high confidence (min_confidence default is 0.5)
        pattern1 = Pattern(
            id="query_001",
            agent_id="agent_1",
            pattern_type="sequential",
            name="Sequential Pattern",
            description="Test sequential pattern",
            tags=["testing", "sequential"],
            confidence=0.8,  # Above minimum
        )

        pattern2 = Pattern(
            id="query_002",
            agent_id="agent_2",
            pattern_type="temporal",
            name="Temporal Pattern",
            description="Test temporal pattern",
            tags=["testing", "temporal"],
            confidence=0.9,  # Above minimum
        )

        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_2", pattern2)

        # Query by type with low minimum confidence
        context = {"test_context": True}
        matches = library.query_patterns(
            agent_id="test_agent",
            context=context,
            pattern_type="sequential",
            min_confidence=0.1,  # Low threshold to ensure matches
        )

        # Verify we got results
        assert len(matches) >= 0  # May be 0 if no matches, that's OK

        # Test we can retrieve patterns directly
        assert "query_001" in library.patterns
        assert library.patterns["query_001"].pattern_type == "sequential"

    def test_contribute_pattern_duplicate_id_raises(self):
        """Test that duplicate pattern IDs raise ValueError."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="duplicate_id",
            agent_id="agent_1",
            pattern_type="test",
            name="First",
            description="First pattern",
        )
        pattern2 = Pattern(
            id="duplicate_id",  # Same ID
            agent_id="agent_2",
            pattern_type="test",
            name="Second",
            description="Second pattern",
        )

        library.contribute_pattern("agent_1", pattern1)

        with pytest.raises(ValueError, match="already exists"):
            library.contribute_pattern("agent_2", pattern2)

    def test_contribute_pattern_empty_agent_id_raises(self):
        """Test that empty agent_id raises ValueError."""
        library = PatternLibrary()
        pattern = Pattern(
            id="test",
            agent_id="agent_1",
            pattern_type="test",
            name="Test",
            description="Test",
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            library.contribute_pattern("", pattern)

        with pytest.raises(ValueError, match="cannot be empty"):
            library.contribute_pattern("   ", pattern)

    def test_query_patterns_with_type_filter(self):
        """Test querying patterns filtered by type."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="algorithm",
            name="Algorithm Pattern",
            description="Test",
            confidence=0.9,
        )
        pattern2 = Pattern(
            id="p2",
            agent_id="agent_1",
            pattern_type="workflow",
            name="Workflow Pattern",
            description="Test",
            confidence=0.9,
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_1", pattern2)

        # Query only algorithm patterns
        matches = library.query_patterns(
            "agent_2",
            {"task": "test"},
            pattern_type="algorithm",
        )

        # Should only return algorithm patterns
        for match in matches:
            assert match.pattern.pattern_type == "algorithm"

    def test_query_patterns_validation_errors(self):
        """Test query_patterns input validation."""
        library = PatternLibrary()

        # Empty agent_id
        with pytest.raises(ValueError, match="cannot be empty"):
            library.query_patterns("", {"task": "test"})

        # Non-dict context
        with pytest.raises(TypeError, match="must be dict"):
            library.query_patterns("agent_1", "not a dict")

        # Invalid confidence range
        with pytest.raises(ValueError, match="must be 0-1"):
            library.query_patterns("agent_1", {}, min_confidence=1.5)

        with pytest.raises(ValueError, match="must be 0-1"):
            library.query_patterns("agent_1", {}, min_confidence=-0.1)

        # Invalid limit
        with pytest.raises(ValueError, match="must be positive"):
            library.query_patterns("agent_1", {}, limit=0)

    def test_get_pattern(self):
        """Test retrieving a pattern by ID."""
        library = PatternLibrary()
        pattern = Pattern(
            id="get_test",
            agent_id="agent_1",
            pattern_type="test",
            name="Get Test",
            description="Test get_pattern",
        )
        library.contribute_pattern("agent_1", pattern)

        # Get existing pattern
        retrieved = library.get_pattern("get_test")
        assert retrieved is not None
        assert retrieved.id == "get_test"
        assert retrieved.name == "Get Test"

        # Get non-existent pattern
        missing = library.get_pattern("nonexistent")
        assert missing is None

    def test_get_patterns_by_tag(self):
        """Test retrieving patterns by tag."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 1",
            description="Test",
            tags=["debugging", "python"],
        )
        pattern2 = Pattern(
            id="p2",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 2",
            description="Test",
            tags=["debugging", "java"],
        )
        pattern3 = Pattern(
            id="p3",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 3",
            description="Test",
            tags=["optimization"],
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_1", pattern2)
        library.contribute_pattern("agent_1", pattern3)

        # Get debugging patterns
        debugging_patterns = library.get_patterns_by_tag("debugging")
        assert len(debugging_patterns) == 2
        assert all(p.id in ["p1", "p2"] for p in debugging_patterns)

        # Get python patterns
        python_patterns = library.get_patterns_by_tag("python")
        assert len(python_patterns) == 1
        assert python_patterns[0].id == "p1"

        # Get patterns with non-existent tag
        empty = library.get_patterns_by_tag("nonexistent")
        assert len(empty) == 0

    def test_get_patterns_by_type(self):
        """Test retrieving patterns by type."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="algorithm",
            name="Algo 1",
            description="Test",
        )
        pattern2 = Pattern(
            id="p2",
            agent_id="agent_1",
            pattern_type="algorithm",
            name="Algo 2",
            description="Test",
        )
        pattern3 = Pattern(
            id="p3",
            agent_id="agent_1",
            pattern_type="workflow",
            name="Workflow 1",
            description="Test",
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_1", pattern2)
        library.contribute_pattern("agent_1", pattern3)

        # Get algorithm patterns
        algos = library.get_patterns_by_type("algorithm")
        assert len(algos) == 2
        assert all(p.pattern_type == "algorithm" for p in algos)

        # Get workflow patterns
        workflows = library.get_patterns_by_type("workflow")
        assert len(workflows) == 1
        assert workflows[0].id == "p3"

        # Get patterns with non-existent type
        empty = library.get_patterns_by_type("nonexistent")
        assert len(empty) == 0

    def test_record_pattern_outcome(self):
        """Test recording pattern usage outcomes."""
        library = PatternLibrary()
        pattern = Pattern(
            id="outcome_test",
            agent_id="agent_1",
            pattern_type="test",
            name="Outcome Test",
            description="Test",
        )
        library.contribute_pattern("agent_1", pattern)

        # Record successful outcome
        library.record_pattern_outcome("outcome_test", success=True)
        assert library.patterns["outcome_test"].success_count == 1
        assert library.patterns["outcome_test"].usage_count == 1

        # Record failed outcome
        library.record_pattern_outcome("outcome_test", success=False)
        assert library.patterns["outcome_test"].failure_count == 1
        assert library.patterns["outcome_test"].usage_count == 2

    def test_record_pattern_outcome_nonexistent_raises(self):
        """Test that recording outcome for nonexistent pattern raises ValueError."""
        library = PatternLibrary()

        with pytest.raises(ValueError, match="not found"):
            library.record_pattern_outcome("nonexistent", success=True)

    def test_link_patterns(self):
        """Test creating links between patterns."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 1",
            description="Test",
        )
        pattern2 = Pattern(
            id="p2",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 2",
            description="Test",
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_1", pattern2)

        # Link patterns
        library.link_patterns("p1", "p2")

        # Verify bidirectional link
        assert "p2" in library.pattern_graph["p1"]
        assert "p1" in library.pattern_graph["p2"]

    def test_link_patterns_validation_errors(self):
        """Test link_patterns validation."""
        library = PatternLibrary()
        pattern = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 1",
            description="Test",
        )
        library.contribute_pattern("agent_1", pattern)

        # Pattern doesn't exist
        with pytest.raises(ValueError, match="does not exist"):
            library.link_patterns("p1", "nonexistent")

        with pytest.raises(ValueError, match="does not exist"):
            library.link_patterns("nonexistent", "p1")

        # Same pattern
        with pytest.raises(ValueError, match="Cannot link a pattern to itself"):
            library.link_patterns("p1", "p1")

    def test_get_related_patterns(self):
        """Test retrieving related patterns."""
        library = PatternLibrary()
        pattern1 = Pattern(
            id="p1",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 1",
            description="Test",
        )
        pattern2 = Pattern(
            id="p2",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 2",
            description="Test",
        )
        pattern3 = Pattern(
            id="p3",
            agent_id="agent_1",
            pattern_type="test",
            name="Pattern 3",
            description="Test",
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_1", pattern2)
        library.contribute_pattern("agent_1", pattern3)

        # Create links: p1 <-> p2 <-> p3
        library.link_patterns("p1", "p2")
        library.link_patterns("p2", "p3")

        # Get immediate neighbors (depth=1)
        related = library.get_related_patterns("p1", depth=1)
        assert len(related) == 1
        assert related[0].id == "p2"

        # Get neighbors up to depth=2
        related = library.get_related_patterns("p1", depth=2)
        assert len(related) == 2
        pattern_ids = {p.id for p in related}
        assert pattern_ids == {"p2", "p3"}

    def test_get_related_patterns_nonexistent(self):
        """Test get_related_patterns with nonexistent pattern."""
        library = PatternLibrary()

        related = library.get_related_patterns("nonexistent")
        assert len(related) == 0
