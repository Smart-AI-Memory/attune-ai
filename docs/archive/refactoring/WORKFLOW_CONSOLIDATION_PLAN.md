# Workflow Consolidation Plan

**Version:** 1.0
**Created:** 2026-02-02
**Status:** Proposed
**Goal:** Reduce 31 workflows to 17 (45% reduction)

---

## Executive Summary

This plan addresses workflow redundancy through three priority phases using XML-enhanced prompting for clear task definitions.

---

## Priority 1: High Priority (Remove Immediately)

### Phase 1A: Remove Test Artifacts

<task_description>
Remove test artifacts and stubs that should never have been registered as workflows.
</task_description>

<context>
<workflows_to_remove>
- test5 (Test5Workflow) - Test artifact, not a real workflow
- manage-docs (ManageDocsWorkflow) - Incomplete stub with TODO comments
</workflows_to_remove>

<files_affected>
- src/attune/workflows/__init__.py (remove from _LAZY_WORKFLOW_IMPORTS and __all__)
- src/attune/workflows/test5.py (delete file)
- src/attune/workflows/manage_docs.py (delete file)
- scripts/test_all_workflows.sh (update expected count)
</files_affected>
</context>

<expected_output>
1. Delete workflow files
2. Remove from __init__.py registry
3. Update test script to expect 29 workflows
4. Verify all tests pass
</expected_output>

<implementation_steps>
1. Delete src/attune/workflows/test5.py
2. Delete src/attune/workflows/manage_docs.py
3. Edit __init__.py:
   - Remove "test5" from _DEFAULT_WORKFLOW_NAMES
   - Remove "manage-docs" from _DEFAULT_WORKFLOW_NAMES
   - Remove Test5Workflow from _LAZY_WORKFLOW_IMPORTS
   - Remove ManageDocsWorkflow from _LAZY_WORKFLOW_IMPORTS
   - Remove from __all__
4. Update test script workflow count from 31 to 29
5. Run: ./scripts/test_all_workflows.sh
</implementation_steps>

---

### Phase 1B: Remove Deprecated Workflows

<task_description>
Remove workflows explicitly marked as deprecated in code comments.
</task_description>

<context>
<workflows_to_remove>
- release-prep-legacy (ReleasePreparationWorkflow) - Superseded by OrchestratedReleasePrepWorkflow
</workflows_to_remove>

<deprecation_evidence>
File: src/attune/workflows/release_prep.py
Comment: "Legacy release preparation - use orchestrated-release-prep for new projects"
</deprecation_evidence>

<files_affected>
- src/attune/workflows/__init__.py
- src/attune/workflows/release_prep.py (keep file, remove legacy registration)
</files_affected>
</context>

<expected_output>
1. Remove legacy workflow registration (keep class for backward compatibility imports)
2. Add deprecation warning to class
3. Update test count to 28
</expected_output>

<implementation_steps>
1. Edit src/attune/workflows/release_prep.py:
   - Add deprecation warning to ReleasePreparationWorkflow.__init__
   ```python
   import warnings
   warnings.warn(
       "ReleasePreparationWorkflow is deprecated. Use OrchestratedReleasePrepWorkflow instead.",
       DeprecationWarning,
       stacklevel=2
   )
   ```
2. Edit __init__.py:
   - Remove "release-prep-legacy" from _DEFAULT_WORKFLOW_NAMES
   - Keep class in __all__ for backward compatibility
3. Update test script workflow count to 28
</implementation_steps>

---

### Phase 1C: Remove Experimental Workflows

<task_description>
Remove experimental workflow variants that duplicate production workflows.
</task_description>

<context>
<workflows_to_remove>
- orchestrated-health-check-experimental
- orchestrated-release-prep-experimental
</workflows_to_remove>

<rationale>
Experimental variants should be feature flags on main workflows, not separate registrations.
The production versions (orchestrated-health-check, orchestrated-release-prep) are stable.
</rationale>

<files_affected>
- src/attune/workflows/__init__.py
- Experimental workflow files (if separate)
</files_affected>
</context>

<expected_output>
1. Remove experimental registrations
2. Merge any unique experimental features into main workflows
3. Update test count to 26
</expected_output>

<implementation_steps>
1. Audit experimental workflows for unique features not in production versions
2. If unique features exist, add as flags to production workflow:
   ```python
   class OrchestratedHealthCheckWorkflow:
       def __init__(self, experimental_mode: bool = False):
           self.experimental_mode = experimental_mode
   ```
3. Remove experimental entries from _DEFAULT_WORKFLOW_NAMES
4. Update test script workflow count to 26
</implementation_steps>

---

## Priority 2: Medium Priority (Merge Within 1-2 Sprints)

### Phase 2A: Consolidate Code Review Workflows

<task_description>
Merge pro-review into code-review as a --premium flag option.
</task_description>

<context>
<current_state>
- code-review: Standard tiered code review (CodeReviewWorkflow)
- pro-review: Premium multi-agent review (CodeReviewPipeline)
</current_state>

<overlap_analysis>
Both workflows:
- Analyze code changes
- Use tiered LLM routing
- Support crew integration
- Produce similar output formats

pro-review adds:
- Always uses premium tier
- More extensive multi-agent analysis
</overlap_analysis>

<proposed_merge>
code-review --mode standard (default)
code-review --mode premium (absorbs pro-review)
</proposed_merge>
</context>

<expected_output>
1. Single code-review workflow with mode selection
2. Deprecation warning on pro-review CLI name
3. Backward compatible imports for CodeReviewPipeline
</expected_output>

<implementation_steps>
1. Edit src/attune/workflows/code_review.py:
   ```python
   class CodeReviewWorkflow(BaseWorkflow):
       workflow_name = "code-review"

       def __init__(self, mode: str = "standard", **kwargs):
           """
           Args:
               mode: "standard" (default) or "premium" (replaces pro-review)
           """
           super().__init__(**kwargs)
           self.mode = mode
           if mode == "premium":
               self._configure_premium_mode()

       def _configure_premium_mode(self):
           """Configure premium mode (formerly pro-review)."""
           self.file_threshold = 0  # Always trigger premium
           self.use_crew = True
           # ... merge CodeReviewPipeline logic
   ```

2. Update CLI parser to accept --mode flag:
   ```python
   # src/attune/cli/parsers/workflow.py
   parser.add_argument("--mode", choices=["standard", "premium"], default="standard")
   ```

3. Add backward compatibility alias:
   ```python
   # src/attune/workflows/__init__.py
   # Keep pro-review as alias pointing to code-review --mode premium
   "pro-review": ("code_review", "CodeReviewWorkflow", {"mode": "premium"}),
   ```

4. Update test script to verify both modes work
5. Update workflow count to 25 (pro-review becomes alias, not separate)
</implementation_steps>

---

### Phase 2B: Consolidate Test Generation Workflows

<task_description>
Reduce 7 test generation workflows to 3 distinct workflows.
</task_description>

<context>
<current_state>
1. test-gen - Standard test generation
2. test-gen-behavioral - Behavioral test templates
3. test-gen-parallel - Parallel batch processing
4. test-coverage-boost - Coverage improvement focus
5. test-maintenance - Fix flaky tests
6. autonomous-test-gen - Dashboard + phases
7. progressive-test-gen - Tier escalation
</current_state>

<consolidation_plan>
KEEP (3 distinct purposes):
- test-gen: Single-file/module test generation
- test-gen-parallel: Batch processing (absorbs autonomous-test-gen, progressive features)
- test-maintenance: Fix existing tests (distinct purpose)

MERGE into test-gen:
- test-gen-behavioral → test-gen --style behavioral
- test-coverage-boost → test-gen --target coverage

MERGE into test-gen-parallel:
- autonomous-test-gen → test-gen-parallel --autonomous
- progressive-test-gen → test-gen-parallel --progressive
</consolidation_plan>
</context>

<expected_output>
1. test-gen with --style and --target flags
2. test-gen-parallel with --autonomous and --progressive flags
3. test-maintenance unchanged
4. Aliases for backward compatibility
</expected_output>

<implementation_steps>
1. Enhance test-gen workflow:
   ```python
   class TestGenerationWorkflow(BaseWorkflow):
       workflow_name = "test-gen"

       def __init__(
           self,
           style: str = "standard",  # standard, behavioral
           target: str = "gaps",      # gaps, coverage, bugs
           **kwargs
       ):
           super().__init__(**kwargs)
           self.style = style
           self.target = target
   ```

2. Enhance test-gen-parallel workflow:
   ```python
   class ParallelTestGenerationWorkflow(BaseWorkflow):
       workflow_name = "test-gen-parallel"

       def __init__(
           self,
           autonomous: bool = False,   # Dashboard + phases
           progressive: bool = False,  # Tier escalation
           batch_size: int = 10,
           **kwargs
       ):
           super().__init__(**kwargs)
           self.autonomous = autonomous
           self.progressive = progressive
   ```

3. Create aliases in __init__.py:
   ```python
   _WORKFLOW_ALIASES = {
       "test-gen-behavioral": ("test-gen", {"style": "behavioral"}),
       "test-coverage-boost": ("test-gen", {"target": "coverage"}),
       "autonomous-test-gen": ("test-gen-parallel", {"autonomous": True}),
       "progressive-test-gen": ("test-gen-parallel", {"progressive": True}),
   }
   ```

4. Update test script - verify aliases work
5. Update workflow count to 22 (4 become aliases)
</implementation_steps>

---

### Phase 2C: Consolidate Release Workflows

<task_description>
Merge release workflow variants into single configurable workflow.
</task_description>

<context>
<current_state>
- release-prep: Standard release preparation
- secure-release: Security-focused pipeline
- orchestrated-release-prep: Multi-agent comprehensive
</current_state>

<consolidation_plan>
Single workflow with modes:
- release-prep --mode standard (default, quick checks)
- release-prep --mode secure (adds security pipeline)
- release-prep --mode full (multi-agent comprehensive)
</consolidation_plan>
</context>

<expected_output>
1. Unified release-prep workflow with mode flag
2. Aliases for backward compatibility
3. Clear documentation of mode differences
</expected_output>

<implementation_steps>
1. Enhance release-prep workflow:
   ```python
   class ReleasePreparationWorkflow(BaseWorkflow):
       workflow_name = "release-prep"

       MODES = {
           "standard": ["health", "changelog"],
           "secure": ["health", "security", "changelog", "approve"],
           "full": ["health", "security", "code_review", "docs", "changelog", "approve"],
       }

       def __init__(self, mode: str = "standard", **kwargs):
           super().__init__(**kwargs)
           self.mode = mode
           self.stages = self.MODES[mode]
   ```

2. Create aliases:
   ```python
   _WORKFLOW_ALIASES = {
       "secure-release": ("release-prep", {"mode": "secure"}),
       "orchestrated-release-prep": ("release-prep", {"mode": "full"}),
   }
   ```

3. Update workflow count to 20 (2 become aliases)
</implementation_steps>

---

### Phase 2D: Consolidate Documentation Workflows

<task_description>
Remove duplicate documentation workflows, keeping distinct purposes.
</task_description>

<context>
<current_state>
- doc-gen: Generate documentation
- doc-orchestrator: Find and fix stale docs
- document-manager: Duplicate of doc-gen
- seo-optimization: SEO-specific
</current_state>

<consolidation_plan>
KEEP (distinct purposes):
- doc-gen: Generate documentation for code
- doc-orchestrator: Orchestrate doc maintenance
- seo-optimization: Marketing/SEO focus

REMOVE:
- document-manager: Duplicates doc-gen
</consolidation_plan>
</context>

<expected_output>
1. Remove document-manager
2. Keep 3 distinct documentation workflows
3. Update workflow count to 19
</expected_output>

<implementation_steps>
1. Add deprecation warning to DocumentManagerWorkflow
2. Remove from _DEFAULT_WORKFLOW_NAMES
3. Keep in __all__ for import compatibility
4. Update test script
</implementation_steps>

---

## Priority 3: Low Priority (Future Cleanup)

### Phase 3A: Remove Niche Workflows

<task_description>
Remove workflows with very narrow use cases.
</task_description>

<context>
<workflows_to_evaluate>
- keyboard-shortcuts: Only useful for vim/editor customization
</workflows_to_evaluate>

<decision_criteria>
- Is this used by >5% of users?
- Does this serve the core developer workflow?
- Can this be a separate plugin instead?
</decision_criteria>
</context>

<expected_output>
1. Move to plugin/optional module
2. Remove from core workflow list
3. Final workflow count: 18
</expected_output>

<implementation_steps>
1. Create plugin directory structure:
   ```
   plugins/
   └── keyboard-shortcuts/
       ├── __init__.py
       └── workflow.py
   ```
2. Move KeyboardShortcutWorkflow to plugin
3. Remove from core _DEFAULT_WORKFLOW_NAMES
4. Document as optional plugin in README
</implementation_steps>

---

### Phase 3B: Final Cleanup and Documentation

<task_description>
Update all documentation to reflect consolidated workflow structure.
</task_description>

<context>
<documentation_to_update>
- docs/WORKFLOW_INVENTORY.md - Update with final 17-18 workflows
- README.md - Update workflow quick reference
- docs/WORKFLOW_TESTING_GUIDE.md - Update test expectations
- .claude/CLAUDE.md - Update available workflows section
</documentation_to_update>
</context>

<expected_output>
1. Complete documentation refresh
2. Clear migration guide for deprecated workflows
3. Updated CLI help text
</expected_output>

<implementation_steps>
1. Update WORKFLOW_INVENTORY.md with final list
2. Create WORKFLOW_MIGRATION_GUIDE.md for users of deprecated workflows
3. Update all README references
4. Verify CLI --help shows correct workflows
</implementation_steps>

---

## Implementation Checklist

### Phase 1 (High Priority) - Week 1

- [ ] Delete test5.py and manage_docs.py
- [ ] Add deprecation warning to release-prep-legacy
- [ ] Remove experimental workflow registrations
- [ ] Update __init__.py registry
- [ ] Update test script (expect 26 workflows)
- [ ] Verify all tests pass

### Phase 2 (Medium Priority) - Weeks 2-3

- [ ] Merge pro-review into code-review --mode premium
- [ ] Add style/target flags to test-gen
- [ ] Add autonomous/progressive flags to test-gen-parallel
- [ ] Add mode flag to release-prep
- [ ] Remove document-manager
- [ ] Create _WORKFLOW_ALIASES mapping
- [ ] Update CLI parsers for new flags
- [ ] Update test script (expect 17-19 workflows)
- [ ] Verify backward compatibility

### Phase 3 (Low Priority) - Week 4+

- [ ] Move keyboard-shortcuts to plugin
- [ ] Update all documentation
- [ ] Create migration guide
- [ ] Final verification

---

## Final Workflow Structure

```
attune workflow list

Code Quality (4):
  code-review      - Comprehensive code analysis (--mode standard|premium)
  security-audit   - OWASP vulnerability scanning
  bug-predict      - Predictive bug detection
  perf-audit       - Performance analysis

Testing (3):
  test-gen         - Test generation (--style standard|behavioral, --target gaps|coverage)
  test-gen-parallel - Batch test generation (--autonomous, --progressive)
  test-maintenance - Fix flaky/failing tests

Documentation (3):
  doc-gen          - Generate documentation
  doc-orchestrator - Find and fix stale docs
  seo-optimization - SEO-focused content

Release (2):
  release-prep     - Release readiness (--mode standard|secure|full)
  dependency-check - Dependency vulnerability scanning

Planning (2):
  refactor-plan    - Plan large refactoring efforts
  research-synthesis - Synthesize research for decisions

Operations (3):
  orchestrated-health-check - Comprehensive project health
  batch-processing          - Large-scale automated operations
  pr-review                 - Combined PR review (code + security)

Total: 17 workflows
```

---

## Success Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Workflows | 31 | 17 | -45% |
| Test Generation Variants | 7 | 3 | -57% |
| Documentation Variants | 5 | 3 | -40% |
| Release Variants | 5 | 2 | -60% |
| Experimental | 3 | 0 | -100% |
| Stubs/Test Artifacts | 2 | 0 | -100% |

---

## Risk Mitigation

### Backward Compatibility

<mitigation_strategy>
1. All removed workflow names become aliases pointing to consolidated workflows
2. Deprecation warnings guide users to new syntax
3. Import paths remain valid via __all__ exports
4. 6-month deprecation period before alias removal
</mitigation_strategy>

### Testing

<mitigation_strategy>
1. All existing tests must pass after each phase
2. Add tests for new flags/modes
3. Add tests for backward compatibility aliases
4. Integration tests verify CLI commands
</mitigation_strategy>

### Documentation

<mitigation_strategy>
1. Migration guide created before any removal
2. CHANGELOG documents all consolidations
3. CLI help text updated with new syntax
4. README examples updated
</mitigation_strategy>

---

## Appendix: Alias Mapping Reference

```python
# src/attune/workflows/__init__.py

_WORKFLOW_ALIASES = {
    # Code Review aliases
    "pro-review": ("code-review", {"mode": "premium"}),

    # Test Generation aliases
    "test-gen-behavioral": ("test-gen", {"style": "behavioral"}),
    "test-coverage-boost": ("test-gen", {"target": "coverage"}),
    "autonomous-test-gen": ("test-gen-parallel", {"autonomous": True}),
    "progressive-test-gen": ("test-gen-parallel", {"progressive": True}),

    # Release aliases
    "secure-release": ("release-prep", {"mode": "secure"}),
    "orchestrated-release-prep": ("release-prep", {"mode": "full"}),

    # Deprecated (show warning)
    "release-prep-legacy": ("release-prep", {"mode": "standard", "_deprecated": True}),
    "document-manager": ("doc-gen", {"_deprecated": True}),
}
```
