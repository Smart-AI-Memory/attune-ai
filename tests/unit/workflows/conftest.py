"""Pytest configuration for workflow tests.

Provides shared fixtures for workflow testing with proper isolation.
"""

import pytest

from attune.cost_tracker import CostTracker


@pytest.fixture
def cost_tracker(tmp_path):
    """Create isolated CostTracker for testing.

    Uses tmp_path to ensure tests don't interfere with each other
    or pollute the project directory.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        CostTracker instance with isolated storage

    """
    storage_dir = tmp_path / ".empathy"
    return CostTracker(storage_dir=str(storage_dir))


@pytest.fixture
def security_audit_workflow(cost_tracker):
    """Create SecurityAuditWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        SecurityAuditWorkflow instance ready for testing

    """
    from attune.workflows.security_audit import SecurityAuditWorkflow

    return SecurityAuditWorkflow(
        cost_tracker=cost_tracker,
        use_crew_for_assessment=False,
        use_crew_for_remediation=False,
    )


@pytest.fixture
def code_review_workflow(cost_tracker):
    """Create CodeReviewWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        CodeReviewWorkflow instance ready for testing

    """
    from attune.workflows.code_review import CodeReviewWorkflow

    return CodeReviewWorkflow(cost_tracker=cost_tracker)


@pytest.fixture
def bug_predict_workflow(cost_tracker):
    """Create BugPredictWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        BugPredictWorkflow instance ready for testing

    """
    from attune.workflows.bug_predict import BugPredictionWorkflow

    return BugPredictionWorkflow(cost_tracker=cost_tracker)


@pytest.fixture
def dependency_check_workflow(cost_tracker):
    """Create DependencyCheckWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        DependencyCheckWorkflow instance ready for testing

    """
    from attune.workflows.dependency_check import DependencyCheckWorkflow

    return DependencyCheckWorkflow(cost_tracker=cost_tracker)


@pytest.fixture
def parallel_test_gen_workflow(cost_tracker):
    """Create ParallelTestGenerationWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        ParallelTestGenerationWorkflow instance ready for testing

    """
    import logging

    from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow

    wf = ParallelTestGenerationWorkflow(cost_tracker=cost_tracker)
    # Workflow uses self.logger but BaseWorkflow doesn't provide it
    wf.logger = logging.getLogger("attune.workflows.test_gen_parallel")
    return wf


@pytest.fixture
def research_synthesis_workflow(cost_tracker):
    """Create ResearchSynthesisWorkflow with isolated storage.

    Args:
        cost_tracker: Isolated CostTracker fixture

    Returns:
        ResearchSynthesisWorkflow instance ready for testing

    """
    from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

    return ResearchSynthesisWorkflow(cost_tracker=cost_tracker)


@pytest.fixture
def seo_optimization_workflow():
    """Create SEOOptimizationWorkflow for testing.

    Returns:
        SEOOptimizationWorkflow instance ready for testing

    """
    from attune.workflows.seo_optimization import SEOOptimizationWorkflow

    return SEOOptimizationWorkflow()


@pytest.fixture
def test_maintenance_workflow(tmp_path):
    """Create TestMaintenanceWorkflow with isolated project root.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        TestMaintenanceWorkflow instance ready for testing

    """
    from unittest.mock import MagicMock

    from attune.workflows.test_maintenance import TestMaintenanceWorkflow

    mock_index = MagicMock()
    mock_index.load.return_value = True
    return TestMaintenanceWorkflow(project_root=str(tmp_path), index=mock_index)
