"""Command-owned adapters for renderer-backed workflow workspaces."""

from attune.workspaces.bug_predict import (
    BugFindingReceipt,
    BugPredictWorkspaceAdapter,
    BugPredictWorkspaceState,
)
from attune.workspaces.bulk import BulkRequest, BulkWorkspaceAdapter, BulkWorkspaceState
from attune.workspaces.doc_gen import (
    DocGenWorkspaceAdapter,
    DocGenWorkspaceState,
    DocumentationFileReceipt,
)
from attune.workspaces.image_analysis import (
    ImageAnalysisWorkspaceAdapter,
    ImageAnalysisWorkspaceState,
)
from attune.workspaces.memory_context import (
    MemoryContextWorkspaceAdapter,
    MemoryContextWorkspaceState,
)
from attune.workspaces.release_prep import (
    ReleaseGateReceipt,
    ReleasePrepWorkspaceAdapter,
    ReleasePrepWorkspaceState,
)
from attune.workspaces.security_audit import (
    SecurityAuditWorkspaceAdapter,
    SecurityAuditWorkspaceState,
    SecurityFindingReceipt,
)
from attune.workspaces.smart_test import (
    SmartTestWorkspaceAdapter,
    SmartTestWorkspaceState,
    TestGapReceipt,
    WrittenTestReceipt,
)
from attune.workspaces.verify import (
    VerificationFinding,
    VerifyWorkspaceAdapter,
    VerifyWorkspaceState,
)
from attune.workspaces.workflow_orchestration import (
    ChildWorkflowReceipt,
    WorkflowOrchestrationAdapter,
    WorkflowOrchestrationState,
)

COHORT_ADAPTER_ORDER = (
    "release-prep",
    "bug-predict",
    "bulk",
    "memory-and-context",
    "smart-test",
    "doc-gen",
    "workflow-orchestration",
    "image-analysis",
    "verify",
    "security-audit",
)

__all__ = [
    "COHORT_ADAPTER_ORDER",
    "BugFindingReceipt",
    "BugPredictWorkspaceAdapter",
    "BugPredictWorkspaceState",
    "BulkRequest",
    "BulkWorkspaceAdapter",
    "BulkWorkspaceState",
    "DocGenWorkspaceAdapter",
    "DocGenWorkspaceState",
    "DocumentationFileReceipt",
    "ImageAnalysisWorkspaceAdapter",
    "ImageAnalysisWorkspaceState",
    "MemoryContextWorkspaceAdapter",
    "MemoryContextWorkspaceState",
    "ReleaseGateReceipt",
    "ReleasePrepWorkspaceAdapter",
    "ReleasePrepWorkspaceState",
    "SecurityAuditWorkspaceAdapter",
    "SecurityAuditWorkspaceState",
    "SecurityFindingReceipt",
    "SmartTestWorkspaceAdapter",
    "SmartTestWorkspaceState",
    "TestGapReceipt",
    "WrittenTestReceipt",
    "ChildWorkflowReceipt",
    "WorkflowOrchestrationAdapter",
    "WorkflowOrchestrationState",
    "VerificationFinding",
    "VerifyWorkspaceAdapter",
    "VerifyWorkspaceState",
]
