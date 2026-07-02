"""Tests for memory graph (cross-workflow intelligence).

Covers:
- Node and edge operations
- Graph traversal and path finding
- Similarity search
- Persistence and loading
- Statistics

Copyright 2025 Smart AI Memory, LLC
"""

import pytest

from attune.memory.edges import EdgeType
from attune.memory.graph import MemoryGraph
from attune.memory.nodes import NodeType

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_graph_path(tmp_path):
    """Create temporary path for graph storage."""
    return tmp_path / "test_memory_graph.json"


@pytest.fixture
def graph(temp_graph_path):
    """Create a fresh MemoryGraph instance."""
    return MemoryGraph(path=temp_graph_path)


@pytest.fixture
def populated_graph(graph):
    """Create a graph with some nodes and edges."""
    # Add bug finding
    bug_id = graph.add_finding(
        workflow="bug-predict",
        finding={
            "type": "bug",
            "name": "Null pointer in auth.py",
            "description": "Missing null check on user object",
            "file": "src/auth.py",
            "line": 42,
            "severity": "high",
        },
    )

    # Add fix finding
    fix_id = graph.add_finding(
        workflow="bug-predict",
        finding={
            "type": "pattern",
            "name": "Add null guard",
            "description": "Added guard clause for null check",
            "file": "src/auth.py",
        },
    )

    # Add vulnerability
    vuln_id = graph.add_finding(
        workflow="security-audit",
        finding={
            "type": "vulnerability",
            "name": "SQL injection risk",
            "description": "User input not sanitized in query",
            "file": "src/db/query.py",
            "line": 156,
            "severity": "critical",
        },
    )

    # Connect bug to fix
    graph.add_edge(bug_id, fix_id, EdgeType.FIXED_BY, workflow="bug-predict")

    return graph, bug_id, fix_id, vuln_id


# =============================================================================
# INITIALIZATION AND PERSISTENCE
# =============================================================================


class TestGraphInitialization:
    """Test graph initialization and loading."""

    def test_creates_empty_graph(self, graph):
        """Test creating an empty graph."""
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_creates_storage_directory(self, tmp_path):
        """Test that graph creates parent directories."""
        path = tmp_path / "nested" / "dir" / "graph.json"
        _graph = MemoryGraph(path=path)
        assert path.parent.exists()

    def test_loads_existing_graph(self, temp_graph_path):
        """Test loading an existing graph file."""
        # Create and populate first graph
        graph1 = MemoryGraph(path=temp_graph_path)
        node_id = graph1.add_finding(
            workflow="test",
            finding={"type": "bug", "name": "Test bug"},
        )

        # Create second instance - should load existing data
        graph2 = MemoryGraph(path=temp_graph_path)
        assert len(graph2.nodes) == 1
        assert node_id in graph2.nodes

    def test_handles_corrupt_json(self, temp_graph_path):
        """Test handling of corrupt JSON file."""
        # Write invalid JSON
        temp_graph_path.write_text("{invalid json")

        # Should create empty graph without crashing
        graph = MemoryGraph(path=temp_graph_path)
        assert len(graph.nodes) == 0

    def test_loads_curated_memory_node_via_real_add_finding(self, temp_graph_path):
        """Regression guard: before NodeType.FEEDBACK/USER_CONTEXT/
        PROJECT_CONTEXT/REFERENCE existed, reloading a graph containing one
        of these types raised
        ``ValueError: 'feedback' is not a valid NodeType`` inside
        MemoryGraph._load() -> Node.from_dict() -> NodeType(data["type"]).
        Exercises the real public API (add_finding, not manual Node
        construction) end to end: add, save, reload in a fresh instance,
        traverse via find_related."""
        graph1 = MemoryGraph(path=temp_graph_path)
        feedback_id = graph1.add_finding(
            workflow="",
            finding={
                "type": "feedback",
                "name": "Standing commitments to Patrick",
                "status": "active",
            },
        )
        project_id = graph1.add_finding(
            workflow="",
            finding={"type": "project_context", "name": "Memory subsystem motivation"},
        )
        graph1.add_edge(project_id, feedback_id, EdgeType.RELATED_TO)

        # A fresh instance must reload without raising.
        graph2 = MemoryGraph(path=temp_graph_path)

        assert graph2.nodes[feedback_id].type == NodeType.FEEDBACK
        assert graph2.nodes[feedback_id].status == "active"
        assert graph2.nodes[project_id].type == NodeType.PROJECT_CONTEXT
        related = graph2.find_related(project_id, edge_types=[EdgeType.RELATED_TO])
        assert [n.id for n in related] == [feedback_id]


# =============================================================================
# NODE OPERATIONS
# =============================================================================


class TestNodeOperations:
    """Test adding and retrieving nodes."""

    def test_add_finding_creates_node(self, graph):
        """Test adding a finding creates a node."""
        node_id = graph.add_finding(
            workflow="test-workflow",
            finding={
                "type": "bug",
                "name": "Test bug",
                "description": "A test bug",
            },
        )

        assert node_id in graph.nodes
        node = graph.nodes[node_id]
        assert node.name == "Test bug"
        assert node.type == NodeType.BUG
        assert node.source_workflow == "test-workflow"

    def test_add_finding_with_all_fields(self, graph):
        """Test adding a finding with all optional fields."""
        node_id = graph.add_finding(
            workflow="security-audit",
            finding={
                "type": "vulnerability",
                "name": "XSS vulnerability",
                "description": "Cross-site scripting in form",
                "file": "src/web/forms.py",
                "line": 100,
                "severity": "high",
                "confidence": 0.95,
                "tags": ["web", "security", "xss"],
                "metadata": {"cwe": "CWE-79"},
            },
        )

        node = graph.nodes[node_id]
        assert node.source_file == "src/web/forms.py"
        assert node.source_line == 100
        assert node.severity == "high"
        assert node.confidence == 0.95
        assert "xss" in node.tags
        assert node.metadata.get("cwe") == "CWE-79"

    def test_add_finding_unknown_type_defaults_to_pattern(self, graph):
        """Test unknown node types default to PATTERN."""
        node_id = graph.add_finding(
            workflow="test",
            finding={"type": "unknown_type", "name": "Test"},
        )

        assert graph.nodes[node_id].type == NodeType.PATTERN

    def test_get_node_returns_node(self, populated_graph):
        """Test getting a node by ID."""
        graph, bug_id, _, _ = populated_graph
        node = graph.get_node(bug_id)

        assert node is not None
        assert node.id == bug_id
        assert node.name == "Null pointer in auth.py"

    def test_get_node_returns_none_for_missing(self, graph):
        """Test getting non-existent node returns None."""
        assert graph.get_node("nonexistent_id") is None

    def test_update_node_modifies_properties(self, populated_graph):
        """Test updating node properties."""
        graph, bug_id, _, _ = populated_graph

        result = graph.update_node(
            bug_id,
            {
                "status": "resolved",
                "severity": "medium",
                "tags": ["fixed"],
                "metadata": {"resolved_by": "patch-123"},
            },
        )

        assert result is True
        node = graph.nodes[bug_id]
        assert node.status == "resolved"
        assert node.severity == "medium"
        assert "fixed" in node.tags

    def test_update_node_returns_false_for_missing(self, graph):
        """Test updating non-existent node returns False."""
        assert graph.update_node("nonexistent", {"status": "test"}) is False

    def test_delete_node_removes_node(self, populated_graph):
        """Test deleting a node."""
        graph, bug_id, _, _ = populated_graph

        result = graph.delete_node(bug_id)

        assert result is True
        assert bug_id not in graph.nodes

    def test_delete_node_removes_connected_edges(self, populated_graph):
        """Test deleting a node removes its edges."""
        graph, bug_id, fix_id, _ = populated_graph

        # Initially has edge
        initial_edges = len(graph.edges)

        graph.delete_node(bug_id)

        # Edge should be removed
        assert len(graph.edges) < initial_edges
        # No edges should reference deleted node
        for edge in graph.edges:
            assert edge.source_id != bug_id
            assert edge.target_id != bug_id

    def test_delete_node_returns_false_for_missing(self, graph):
        """Test deleting non-existent node returns False."""
        assert graph.delete_node("nonexistent") is False


# =============================================================================
# EDGE OPERATIONS
# =============================================================================


class TestEdgeOperations:
    """Test adding and querying edges."""

    def test_add_edge_creates_edge(self, populated_graph):
        """Test adding an edge between nodes."""
        graph, _, fix_id, vuln_id = populated_graph

        edge_id = graph.add_edge(
            fix_id,
            vuln_id,
            EdgeType.RELATED_TO,
            description="Fix also addresses vulnerability",
            workflow="analysis",
        )

        assert edge_id is not None
        assert any(e.source_id == fix_id and e.target_id == vuln_id for e in graph.edges)

    def test_add_edge_raises_for_invalid_source(self, graph):
        """Test adding edge with invalid source raises ValueError."""
        node_id = graph.add_finding(workflow="test", finding={"type": "bug", "name": "Test"})

        with pytest.raises(ValueError, match="Source node not found"):
            graph.add_edge("nonexistent", node_id, EdgeType.RELATED_TO)

    def test_add_edge_raises_for_invalid_target(self, graph):
        """Test adding edge with invalid target raises ValueError."""
        node_id = graph.add_finding(workflow="test", finding={"type": "bug", "name": "Test"})

        with pytest.raises(ValueError, match="Target node not found"):
            graph.add_edge(node_id, "nonexistent", EdgeType.RELATED_TO)

    def test_add_bidirectional_edge(self, populated_graph):
        """Test adding bidirectional edges."""
        graph, bug_id, fix_id, _ = populated_graph
        initial_edges = len(graph.edges)

        graph.add_edge(bug_id, fix_id, EdgeType.RELATED_TO, bidirectional=True)

        # Should create two edges
        assert len(graph.edges) >= initial_edges + 2


# =============================================================================
# GRAPH TRAVERSAL
# =============================================================================


class TestGraphTraversal:
    """Test graph traversal operations."""

    def test_find_related_outgoing(self, populated_graph):
        """Test finding related nodes via outgoing edges."""
        graph, bug_id, fix_id, _ = populated_graph

        related = graph.find_related(bug_id, direction="outgoing")

        assert len(related) >= 1
        assert any(n.id == fix_id for n in related)

    def test_find_related_incoming(self, populated_graph):
        """Test finding related nodes via incoming edges."""
        graph, bug_id, fix_id, _ = populated_graph

        related = graph.find_related(fix_id, direction="incoming")

        assert len(related) >= 1
        assert any(n.id == bug_id for n in related)

    def test_find_related_both_directions(self, populated_graph):
        """Test finding related nodes in both directions."""
        graph, bug_id, fix_id, _ = populated_graph

        related = graph.find_related(fix_id, direction="both")

        # Should find the bug via incoming edge
        assert any(n.id == bug_id for n in related)

    def test_find_related_with_edge_type_filter(self, populated_graph):
        """Test filtering related nodes by edge type."""
        graph, bug_id, fix_id, _ = populated_graph

        # Should find with FIXED_BY
        related = graph.find_related(bug_id, edge_types=[EdgeType.FIXED_BY], direction="outgoing")
        assert any(n.id == fix_id for n in related)

        # Should not find with CAUSES
        related = graph.find_related(bug_id, edge_types=[EdgeType.CAUSES], direction="outgoing")
        assert not any(n.id == fix_id for n in related)

    def test_find_related_max_depth(self, graph):
        """Test limiting traversal depth."""
        # Create chain: A -> B -> C -> D
        a = graph.add_finding(workflow="test", finding={"type": "bug", "name": "A"})
        b = graph.add_finding(workflow="test", finding={"type": "bug", "name": "B"})
        c = graph.add_finding(workflow="test", finding={"type": "bug", "name": "C"})
        d = graph.add_finding(workflow="test", finding={"type": "bug", "name": "D"})

        graph.add_edge(a, b, EdgeType.CAUSES)
        graph.add_edge(b, c, EdgeType.CAUSES)
        graph.add_edge(c, d, EdgeType.CAUSES)

        # Depth 1 should only find B
        related = graph.find_related(a, max_depth=1)
        assert len(related) == 1
        assert related[0].name == "B"

        # Depth 2 should find B and C
        related = graph.find_related(a, max_depth=2)
        assert len(related) == 2

        # Depth 3 should find all
        related = graph.find_related(a, max_depth=3)
        assert len(related) == 3

    def test_find_related_nonexistent_node(self, graph):
        """Test finding related for non-existent node returns empty."""
        assert graph.find_related("nonexistent") == []


# =============================================================================
# PATH FINDING
# =============================================================================


class TestPathFinding:
    """Test BFS path finding."""

    def test_get_path_finds_direct_path(self, populated_graph):
        """Test finding direct path between nodes."""
        graph, bug_id, fix_id, _ = populated_graph

        path = graph.get_path(bug_id, fix_id)

        assert len(path) == 2
        assert path[0][0].id == bug_id
        assert path[1][0].id == fix_id

    def test_get_path_finds_multi_hop_path(self, graph):
        """Test finding multi-hop path."""
        # Create chain: A -> B -> C
        a = graph.add_finding(workflow="test", finding={"type": "bug", "name": "A"})
        b = graph.add_finding(workflow="test", finding={"type": "bug", "name": "B"})
        c = graph.add_finding(workflow="test", finding={"type": "bug", "name": "C"})

        graph.add_edge(a, b, EdgeType.CAUSES)
        graph.add_edge(b, c, EdgeType.CAUSES)

        path = graph.get_path(a, c)

        assert len(path) == 3
        assert path[0][0].id == a
        assert path[1][0].id == b
        assert path[2][0].id == c

    def test_get_path_respects_max_depth(self, graph):
        """Test path finding respects max depth."""
        # Create long chain
        nodes = []
        for i in range(10):
            n = graph.add_finding(workflow="test", finding={"type": "bug", "name": f"Node{i}"})
            nodes.append(n)
            if i > 0:
                graph.add_edge(nodes[i - 1], n, EdgeType.CAUSES)

        # Path exists but too deep
        path = graph.get_path(nodes[0], nodes[9], max_depth=3)
        assert path == []

    def test_get_path_returns_empty_for_no_path(self, populated_graph):
        """Test returns empty for disconnected nodes."""
        graph, bug_id, _, vuln_id = populated_graph

        # Bug and vulnerability are not connected
        path = graph.get_path(bug_id, vuln_id)
        assert path == []

    def test_get_path_nonexistent_nodes(self, graph):
        """Test path finding with non-existent nodes."""
        assert graph.get_path("nonexistent1", "nonexistent2") == []


# =============================================================================
# SIMILARITY SEARCH
# =============================================================================


class TestSimilaritySearch:
    """Test similarity-based search."""

    def test_find_similar_by_name(self, populated_graph):
        """Test finding similar nodes by name."""
        graph, bug_id, _, _ = populated_graph

        similar = graph.find_similar({"name": "Null pointer"}, threshold=0.3)

        assert len(similar) >= 1
        assert any(node.id == bug_id for node, score in similar)

    def test_find_similar_by_description(self, populated_graph):
        """Test finding similar nodes by description."""
        graph, bug_id, _, _ = populated_graph

        similar = graph.find_similar({"description": "null check user object"}, threshold=0.2)

        assert len(similar) >= 1

    def test_find_similar_by_type(self, populated_graph):
        """Test type matching boosts similarity."""
        graph, bug_id, _, vuln_id = populated_graph

        # Search for vulnerability type
        similar = graph.find_similar({"type": "vulnerability", "name": "injection"}, threshold=0.1)

        # Vulnerability should rank higher due to type match
        for node, score in similar:
            if node.id == vuln_id:
                assert score > 0  # Has type match bonus
                break

    def test_find_similar_by_file(self, populated_graph):
        """Test file matching boosts similarity."""
        graph, bug_id, fix_id, _ = populated_graph

        similar = graph.find_similar({"name": "test", "file": "src/auth.py"}, threshold=0.0)

        # Should find nodes related to auth.py
        auth_nodes = [n for n, s in similar if n.source_file == "src/auth.py"]
        assert len(auth_nodes) >= 1

    def test_find_similar_respects_limit(self, graph):
        """Test similarity search respects limit."""
        # Add many nodes
        for i in range(20):
            graph.add_finding(
                workflow="test",
                finding={"type": "bug", "name": f"Bug number {i}"},
            )

        similar = graph.find_similar({"name": "Bug"}, threshold=0.1, limit=5)

        assert len(similar) <= 5

    def test_find_similar_returns_scores(self, populated_graph):
        """Test similarity results include scores."""
        graph, _, _, _ = populated_graph

        similar = graph.find_similar({"name": "null"}, threshold=0.0)

        for _node, score in similar:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0


# =============================================================================
# INDEX OPERATIONS
# =============================================================================


class TestIndexOperations:
    """Test indexed lookups."""

    def test_find_by_type(self, populated_graph):
        """Test finding nodes by type."""
        graph, bug_id, _, vuln_id = populated_graph

        bugs = graph.find_by_type(NodeType.BUG)
        assert len(bugs) >= 1
        assert any(n.id == bug_id for n in bugs)

        vulns = graph.find_by_type(NodeType.VULNERABILITY)
        assert len(vulns) >= 1
        assert any(n.id == vuln_id for n in vulns)

    def test_find_by_workflow(self, populated_graph):
        """Test finding nodes by workflow."""
        graph, bug_id, fix_id, vuln_id = populated_graph

        bug_predict_nodes = graph.find_by_workflow("bug-predict")
        assert len(bug_predict_nodes) >= 2

        security_nodes = graph.find_by_workflow("security-audit")
        assert len(security_nodes) >= 1
        assert any(n.id == vuln_id for n in security_nodes)

    def test_find_by_file(self, populated_graph):
        """Test finding nodes by file."""
        graph, bug_id, fix_id, _ = populated_graph

        auth_nodes = graph.find_by_file("src/auth.py")
        assert len(auth_nodes) >= 2
        assert any(n.id == bug_id for n in auth_nodes)


# =============================================================================
# STATISTICS
# =============================================================================


class TestStatistics:
    """Test graph statistics."""

    def test_get_statistics_empty_graph(self, graph):
        """Test statistics for empty graph."""
        stats = graph.get_statistics()

        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0

    def test_get_statistics_populated_graph(self, populated_graph):
        """Test statistics for populated graph."""
        graph, _, _, _ = populated_graph

        stats = graph.get_statistics()

        assert stats["total_nodes"] >= 3
        assert stats["total_edges"] >= 1
        assert "bug" in stats["nodes_by_type"]
        assert "bug-predict" in stats["nodes_by_workflow"]
        assert stats["unique_files"] >= 2


# =============================================================================
# CLEAR OPERATION
# =============================================================================


class TestClearOperation:
    """Test clearing the graph."""

    def test_clear_removes_all_data(self, populated_graph):
        """Test clearing removes all nodes and edges."""
        graph, _, _, _ = populated_graph

        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        graph.clear()

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_clear_resets_indexes(self, populated_graph):
        """Test clearing resets all indexes."""
        graph, _, _, _ = populated_graph

        graph.clear()

        assert len(graph._nodes_by_type) == 0
        assert len(graph._nodes_by_workflow) == 0
        assert len(graph._edges_by_source) == 0


# =============================================================================
# CURATED MEMORY HOME (friction A) AND find_similar ERGONOMICS (friction C)
# =============================================================================


class TestCuratedGraphHome:
    """Test the durable home-directory factory for curated memory."""

    def test_curated_lives_under_home_attune_memory(self, monkeypatch, tmp_path):
        """Test curated() resolves to ~/.attune/memory/curated_graph.json."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        graph = MemoryGraph.curated()

        assert graph.path == tmp_path / ".attune" / "memory" / "curated_graph.json"
        assert graph.path.exists()

    def test_curated_round_trips_across_instances(self, monkeypatch, tmp_path):
        """Test a curated node written via one instance reloads in a fresh one."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        writer = MemoryGraph.curated()
        node_id = writer.add_finding(
            workflow="",
            finding={
                "type": "feedback",
                "name": "Prefer real round-trip tests over mocks",
                "description": "Mock-blind bugs in attune.memory, 2026-07-01",
                "status": "active",
            },
        )

        reader = MemoryGraph.curated()
        node = reader.get_node(node_id)

        assert node is not None
        assert node.type == NodeType.FEEDBACK
        assert node.status == "active"


class TestFindSimilarErgonomics:
    """Test find_similar's string forms and paraphrase-friendly default."""

    def test_accepts_node_id_and_excludes_self(self, populated_graph):
        """Test passing a node ID builds the query from that node."""
        graph, bug_id, fix_id, _ = populated_graph

        results = graph.find_similar(bug_id, threshold=0.0)

        returned_ids = [node.id for node, _score in results]
        assert bug_id not in returned_ids  # self-match excluded
        assert fix_id in returned_ids  # shares file + null-check wording

    def test_accepts_free_text_query(self, populated_graph):
        """Test a non-ID string is treated as free text."""
        graph, bug_id, _, _ = populated_graph

        results = graph.find_similar("null pointer in auth code", threshold=0.1)

        assert any(node.id == bug_id for node, _score in results)

    def test_empty_free_text_returns_no_results(self, populated_graph):
        """Test empty and whitespace-only free-text queries return []."""
        graph, _, _, _ = populated_graph

        assert graph.find_similar("") == []
        assert graph.find_similar("   ") == []

    def test_free_text_question_matches_at_default_threshold(self, populated_graph):
        """Test a question-shaped query clears the default threshold.

        Regression guard for the dogfood finding that free text scored
        by Jaccard tops out near 0.1 against verbose nodes (the union
        term dominates), silently returning [] at any sane threshold.
        Free text scores by query-word containment instead.
        """
        graph, bug_id, _, _ = populated_graph

        results = graph.find_similar("what fixed the null pointer")

        assert any(node.id == bug_id for node, _score in results)

    def test_default_threshold_admits_paraphrase(self, populated_graph):
        """Test a natural paraphrase clears the default threshold.

        Regression guard for the friction-log finding that the old
        default (0.5) muted realistic paraphrases: this query scores
        between 0.25 and 0.5 against the bug node, so it must match at
        the default but would have been silently filtered before.
        """
        graph, bug_id, _, _ = populated_graph

        results = graph.find_similar({"name": "null pointer error auth"})

        match = next(((node, score) for node, score in results if node.id == bug_id), None)
        assert match is not None
        assert match[1] < 0.5  # would have been filtered at the old default
