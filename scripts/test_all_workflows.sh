#!/bin/bash
# Workflow Testing Script
# Verifies all 31 workflows are properly registered and can be loaded
# Also tests the workflow migration system
# Usage: ./scripts/test_all_workflows.sh

# Don't use set -e - we want to continue running tests even when some fail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

echo "=========================================="
echo "  Attune Workflow Testing Script"
echo "  Verifying all 26 workflows + migration"
echo "=========================================="
echo ""

# Function to run a test
test_check() {
    local name="$1"
    local cmd="$2"

    echo -n "Testing: $name... "

    if eval "$cmd" > /tmp/workflow_test_output.txt 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((PASSED++)) || true
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        ((FAILED++)) || true
        echo "  Output:"
        tail -5 /tmp/workflow_test_output.txt | sed 's/^/    /'
        return 1
    fi
}

# Function to verify workflow exists in list
test_workflow_registered() {
    local workflow_name="$1"
    echo -n "  $workflow_name... "

    if uv run attune workflow list 2>/dev/null | grep -q "^  $workflow_name\$\|^  $workflow_name "; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++)) || true
        return 0
    else
        echo -e "${RED}✗ NOT FOUND${NC}"
        ((FAILED++)) || true
        return 1
    fi
}

# Function to verify workflow can be imported
test_workflow_import() {
    local workflow_class="$1"
    echo -n "  Import $workflow_class... "

    if uv run python -c "from attune.workflows import $workflow_class; print('OK')" 2>/dev/null | grep -q "OK"; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++)) || true
        return 0
    else
        echo -e "${RED}✗ IMPORT FAILED${NC}"
        ((FAILED++)) || true
        return 1
    fi
}

# Function to test migration alias resolution
test_migration_alias() {
    local old_name="$1"
    local expected_new="$2"
    echo -n "  $old_name → $expected_new... "

    # Use CI mode for deterministic behavior
    result=$(CI=true uv run python -c "
from attune.workflows.migration import resolve_workflow_migration, MigrationConfig
config = MigrationConfig(mode='auto')
name, kwargs, _ = resolve_workflow_migration('$old_name', config)
print(name)
" 2>/dev/null)

    if [ "$result" = "$expected_new" ]; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++)) || true
        return 0
    else
        echo -e "${RED}✗ Got '$result'${NC}"
        ((FAILED++)) || true
        return 1
    fi
}

echo "=== 1. CLI Commands ==="
echo ""

test_check "attune version" \
    "uv run attune version"

test_check "attune workflow --help" \
    "uv run attune workflow --help"

test_check "workflow list shows 26 workflows" \
    "uv run attune workflow list | grep -q 'Total: 26'"

echo ""
echo "=== 2. Workflow Registration (26 workflows) ==="
echo ""
echo "Verifying each workflow appears in 'attune workflow list':"
echo ""

# Code Analysis (5)
echo "Code Analysis Workflows:"
test_workflow_registered "code-review"
test_workflow_registered "bug-predict"
test_workflow_registered "security-audit"
test_workflow_registered "perf-audit"
test_workflow_registered "pro-review"

# Test Generation (7)
echo ""
echo "Test Generation Workflows:"
test_workflow_registered "test-gen"
test_workflow_registered "test-gen-behavioral"
test_workflow_registered "test-gen-parallel"
test_workflow_registered "test-coverage-boost"
test_workflow_registered "test-maintenance"
test_workflow_registered "autonomous-test-gen"
test_workflow_registered "progressive-test-gen"

# Documentation (4) - manage-docs removed (handled by migration, was deprecated)
echo ""
echo "Documentation Workflows:"
test_workflow_registered "doc-gen"
test_workflow_registered "doc-orchestrator"
test_workflow_registered "document-manager"
test_workflow_registered "seo-optimization"

# Release & Deploy (4) - release-prep-legacy removed (deprecated)
echo ""
echo "Release & Deploy Workflows:"
test_workflow_registered "release-prep"
test_workflow_registered "secure-release"
test_workflow_registered "orchestrated-release-prep"
test_workflow_registered "dependency-check"

# Research & Planning (3)
echo ""
echo "Research & Planning Workflows:"
test_workflow_registered "research-synthesis"
test_workflow_registered "refactor-plan"
test_workflow_registered "keyboard-shortcuts"

# Meta/Orchestration (3)
echo ""
echo "Meta/Orchestration Workflows:"
test_workflow_registered "orchestrated-health-check"
test_workflow_registered "batch-processing"
test_workflow_registered "pr-review"

# Experimental workflows removed (test5 was test artifact, experimental aliases removed)
# Use production versions: orchestrated-health-check, orchestrated-release-prep

echo ""
echo "=== 3. Workflow Class Imports ==="
echo ""
echo "Verifying workflow classes can be imported from attune.workflows:"
echo ""

# Code Analysis Classes (5)
echo "Code Analysis:"
test_workflow_import "CodeReviewWorkflow"
test_workflow_import "BugPredictionWorkflow"
test_workflow_import "SecurityAuditWorkflow"
test_workflow_import "PerformanceAuditWorkflow"
test_workflow_import "CodeReviewPipeline"  # pro-review

# Test Generation Classes (7)
echo ""
echo "Test Generation:"
test_workflow_import "TestGenerationWorkflow"
test_workflow_import "BehavioralTestGenerationWorkflow"
test_workflow_import "ParallelTestGenerationWorkflow"
test_workflow_import "TestCoverageBoostCrew"
test_workflow_import "TestMaintenanceWorkflow"
test_workflow_import "AutonomousTestGenerator"
# ProgressiveTestGenWorkflow removed in v6.3.0 — deprecated since v5.3.0,
# users are routed via the "progressive-test-gen" -> "test-gen" migration alias.

# Documentation Classes (5)
echo ""
echo "Documentation:"
test_workflow_import "DocumentGenerationWorkflow"
test_workflow_import "DocumentationOrchestrator"
test_workflow_import "ManageDocumentationCrew"
test_workflow_import "DocumentManagerWorkflow"
test_workflow_import "SEOOptimizationWorkflow"

# Release & Deploy Classes (5)
echo ""
echo "Release & Deploy:"
test_workflow_import "OrchestratedReleasePrepWorkflow"  # release-prep (canonical)
test_workflow_import "ReleasePreparationWorkflow"       # release-prep-legacy
test_workflow_import "SecureReleasePipeline"            # secure-release
test_workflow_import "ReleasePreparationCrew"           # crew version
test_workflow_import "DependencyCheckWorkflow"

# Research & Planning Classes (3)
echo ""
echo "Research & Planning:"
test_workflow_import "ResearchSynthesisWorkflow"
test_workflow_import "RefactorPlanWorkflow"
test_workflow_import "KeyboardShortcutWorkflow"  # Note: singular "Shortcut"

# Meta/Orchestration Classes (3)
echo ""
echo "Meta/Orchestration:"
test_workflow_import "OrchestratedHealthCheckWorkflow"
test_workflow_import "BatchProcessingWorkflow"
test_workflow_import "PRReviewWorkflow"

# Experimental classes removed (test artifacts and deprecated aliases)

echo ""
echo -e "=== 4. ${CYAN}Workflow Migration System${NC} ==="
echo ""
echo "Testing migration module imports and alias resolution:"
echo ""

# Migration module imports
echo "Migration Module Imports:"
test_workflow_import "resolve_workflow_migration"
test_workflow_import "MigrationConfig"
test_workflow_import "WORKFLOW_ALIASES"
test_workflow_import "show_migration_tip"
test_workflow_import "list_migrations"

# Migration alias resolution
echo ""
echo "Migration Alias Resolution (CI mode):"
test_migration_alias "pro-review" "code-review"
test_migration_alias "test-gen-behavioral" "test-gen"
test_migration_alias "test-coverage-boost" "test-gen"
test_migration_alias "autonomous-test-gen" "test-gen-parallel"
test_migration_alias "progressive-test-gen" "test-gen-parallel"
test_migration_alias "secure-release" "release-prep"
test_migration_alias "orchestrated-release-prep" "release-prep"
test_migration_alias "document-manager" "doc-gen"

# Test non-migrated workflows pass through
echo ""
echo "Non-Migrated Workflows (pass-through):"
test_migration_alias "code-review" "code-review"
test_migration_alias "test-gen" "test-gen"
test_migration_alias "doc-gen" "doc-gen"
test_migration_alias "release-prep" "release-prep"

# Test list_migrations function
echo ""
echo "Migration Listing:"
test_check "list_migrations returns data" \
    "uv run python -c \"from attune.workflows.migration import list_migrations; m = list_migrations(); print(f'Found {len(m)} migrations'); assert len(m) >= 10\""

# Test MigrationConfig save/load
echo ""
echo "Migration Config:"
test_check "MigrationConfig save/load" \
    "uv run python -c \"
import tempfile
import os
from pathlib import Path
from attune.workflows.migration import MigrationConfig

# Create temp dir
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)
    config = MigrationConfig(mode='auto', remembered_choices={'test': 'new'})
    config.save()
    loaded = MigrationConfig.load()
    assert loaded.mode == 'auto'
    assert loaded.remembered_choices.get('test') == 'new'
    print('OK')
\""

echo ""
echo "=== 5. Unit Tests ==="
echo ""

test_check "Workflow unit tests" \
    "uv run pytest tests/ -k 'workflow' -x --tb=line -q 2>&1 | tail -20"

echo ""
echo "=== 6. Migration Unit Tests ==="
echo ""

test_check "Migration system tests" \
    "uv run pytest tests/unit/test_workflow_migration.py -v --tb=short 2>&1 | tail -30"

echo ""
echo "=== 7. Telemetry ==="
echo ""

test_check "telemetry show" \
    "uv run attune telemetry show 2>&1 | head -10"

echo ""
echo "=========================================="
echo "  Results Summary"
echo "=========================================="
echo ""
echo -e "  ${GREEN}Passed:${NC}  $PASSED"
echo -e "  ${RED}Failed:${NC}  $FAILED"
echo ""

# Summary of migration aliases
echo -e "${CYAN}Migration Aliases Configured:${NC}"
echo "  pro-review → code-review --mode premium"
echo "  test-gen-behavioral → test-gen --style behavioral"
echo "  test-coverage-boost → test-gen --target coverage"
echo "  autonomous-test-gen → test-gen-parallel --autonomous"
echo "  progressive-test-gen → test-gen-parallel --progressive"
echo "  secure-release → release-prep --mode secure"
echo "  orchestrated-release-prep → release-prep --mode full"
echo "  document-manager → doc-gen (deprecated)"
echo "  test5 → REMOVED"
echo "  manage-docs → REMOVED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All workflow tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Review output above.${NC}"
    exit 1
fi
