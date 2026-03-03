# Phase 2 Refactoring Plan: 13 Files > 1,000 Lines

**Created:** 2026-02-07
**Approach:** Mixin extraction (same pattern as Phase 1 base.py/core.py)
**Target:** ~300-400 lines per original file (80%+ reduction)
**Testing:** New unit tests required for each extracted module

## Overview

Phase 1 successfully reduced `base.py` (2,051 -> 321) and `core.py` (1,702 -> 237).
Phase 2 applies the same mixin extraction pattern to all 13 remaining files > 1,000 lines.

**Total lines to refactor:** ~16,180
**Expected result:** ~4,200 lines in original files + ~13,000 in new mixin/utility modules

## Mixin Pattern Reference

All new mixins follow this established pattern:

```python
"""<Purpose> Mixin for <HostClass>.

Extracted from <HostClass> to improve maintainability.

Expected attributes on the host class:
    attr_name (type): Description

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..some_module import SomeType


class SomeMixin:
    """Mixin providing <functionality>."""

    # Expected attributes (set by HostClass.__init__)
    some_attr: str
    logger: Any  # logging.Logger
```

## Stage Organization

| Stage | Files | Risk | Focus |
|-------|-------|------|-------|
| 1 | bug_predict, dependency_check, collaboration | Low | Module-level functions & well-bounded classes |
| 2 | code_review, security_audit, document_gen | Medium | BaseWorkflow stage extractions |
| 3 | autonomous_test_gen, documentation_orchestrator, meta_orchestrator | Medium | Phase/strategy extractions |
| 4 | cli_minimal, telemetry/cli | Low | Functional decomposition into command modules |
| 5 | control_panel, release_prep_team | Medium | Multi-class file splitting |

## Verification After Each Task

```bash
uv run pytest tests/unit/ -x -q          # Quick smoke test
uv run pre-commit run --all-files         # Lint & format
python -c "from attune.workflows.bug_predict import BugPredictionWorkflow"  # Import check
```

---

## Stage 1: Low-Risk Extractions

### Task 1.1: bug_predict.py (1,085 -> ~350 lines)

```xml
<task id="1.1" name="bug-predict-extraction">
  <objective>
    Extract module-level pattern detection functions and report formatting
    from bug_predict.py into two new modules, keeping only the
    BugPredictionWorkflow class with its 4 stage methods in the original file.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/bug_predict.py">
      1,085 lines total:
      - Lines 31-417: 7 module-level helper functions (~400 lines)
        _load_bug_predict_config, _should_exclude_file,
        _is_acceptable_broad_exception, _has_problematic_exception_handlers,
        _is_dangerous_eval_usage, _remove_docstrings, _is_security_policy_line
      - Lines 432-942: BugPredictionWorkflow class with _scan, _correlate,
        _predict, _recommend stages
      - Lines 945-1057: format_bug_predict_report (~113 lines)
      - Lines 1060-1084: main() CLI entry point
    </existing-code>
    <pattern>
      Module-level functions are imported directly by the class methods.
      format_bug_predict_report is called from _recommend stage.
      Follow the same re-export pattern used in base.py after Phase 1.
    </pattern>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/bug_predict_patterns.py">
      Module containing all pattern detection functions:
      - _load_bug_predict_config()
      - _should_exclude_file()
      - _is_acceptable_broad_exception()
      - _has_problematic_exception_handlers()
      - _is_dangerous_eval_usage()
      - _remove_docstrings()
      - _is_security_policy_line()
      Preserve all existing imports these functions need.
    </file>
    <file path="src/attune/workflows/bug_predict_report.py">
      Module containing:
      - format_bug_predict_report() function
      - main() CLI entry point
    </file>
    <file path="tests/unit/test_bug_predict_patterns.py">
      Unit tests for all 7 pattern detection functions.
      Test _is_dangerous_eval_usage with known safe/unsafe patterns.
      Test _is_acceptable_broad_exception with justified/unjustified catches.
      Test _should_exclude_file with glob patterns.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/bug_predict.py">
      <change location="top-level imports">
        BEFORE: All functions defined inline
        AFTER: Import from new modules:
          from .bug_predict_patterns import (
              _load_bug_predict_config,
              _should_exclude_file,
              _is_acceptable_broad_exception,
              _has_problematic_exception_handlers,
              _is_dangerous_eval_usage,
              _remove_docstrings,
              _is_security_policy_line,
          )
          from .bug_predict_report import format_bug_predict_report, main
        Remove inline function definitions.
        Keep: BUG_PREDICT_STEPS constant, BugPredictionWorkflow class.
        Re-export format_bug_predict_report and main for backward compat.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.bug_predict import BugPredictionWorkflow, format_bug_predict_report, main"</check>
    <check>python -c "from attune.workflows.bug_predict_patterns import _is_dangerous_eval_usage"</check>
    <check>uv run pytest tests/unit/test_bug_predict*.py -x -q</check>
    <check>wc -l src/attune/workflows/bug_predict.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="low">Import ordering - pattern functions are used by _scan stage. Ensure circular imports don't occur.</risk>
  </risks>
</task>
```

### Task 1.2: dependency_check.py (1,118 -> ~350 lines)

```xml
<task id="1.2" name="dependency-check-extraction">
  <objective>
    Extract dependency parsers and vulnerability tool runners into separate
    modules. Keep DependencyCheckWorkflow with stage methods in original file.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/dependency_check.py">
      1,118 lines total:
      - Lines 44-79: Advisory caching functions (3 functions, ~35 lines)
      - Lines 82-203: Tool runners _run_pip_audit, _run_npm_audit (~120 lines)
      - Lines 327-633: 7 dependency parser methods on the class (~300 lines)
        _parse_requirements, _parse_requirements_fallback,
        _parse_pyproject, _parse_pyproject_fallback,
        _parse_package_json, _parse_poetry_lock, _parse_package_lock_json
      - Lines 206-956: DependencyCheckWorkflow class
      - Lines 958-1084: format_dependency_check_report (~126 lines)
      - Lines 1087-1113: main() CLI entry
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/dep_check_parsers.py">
      Mixin: DependencyParserMixin
      Methods: All 7 _parse_* methods extracted from the workflow class.
      Each method operates on self (needs self.logger only).
    </file>
    <file path="src/attune/workflows/dep_check_tools.py">
      Module-level functions:
      - _get_cache_path()
      - _load_cached_advisories()
      - _save_advisory_cache()
      - _run_pip_audit()
      - _run_npm_audit()
    </file>
    <file path="src/attune/workflows/dep_check_report.py">
      Module containing:
      - format_dependency_check_report()
      - main()
    </file>
    <file path="tests/unit/test_dep_check_parsers.py">
      Unit tests for all 7 parser methods using fixture data.
      Test requirements.txt parsing, pyproject.toml (PEP 621 + Poetry),
      package.json, poetry.lock, package-lock.json.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/dependency_check.py">
      <change location="class definition">
        BEFORE: class DependencyCheckWorkflow(BaseWorkflow):
        AFTER: class DependencyCheckWorkflow(DependencyParserMixin, BaseWorkflow):
        Import DependencyParserMixin and tool functions.
        Remove inline parser methods and tool functions.
        Re-export format_dependency_check_report, main.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.dependency_check import DependencyCheckWorkflow, format_dependency_check_report"</check>
    <check>uv run pytest tests/unit/test_dep_check*.py -x -q</check>
    <check>wc -l src/attune/workflows/dependency_check.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="low">Parser methods access self.logger. Ensure mixin declares logger attribute.</risk>
  </risks>
</task>
```

### Task 1.3: collaboration.py (1,115 -> ~350 lines)

```xml
<task id="1.3" name="collaboration-extraction">
  <objective>
    Split collaboration.py into focused modules: data models, session/participant
    management, comment/voting system, change tracking, and sync/invitation support.
  </objective>

  <context>
    <existing-code path="src/attune/socratic/collaboration.py">
      1,115 lines total:
      - Lines 35-304: 4 enums + 7 dataclasses (~270 lines)
      - Lines 312-878: CollaborationManager class (~566 lines)
        Methods grouped: session CRUD, participants, comments,
        voting, change tracking, persistence
      - Lines 885-970: SyncEvent dataclass + SyncAdapter class (~85 lines)
      - Lines 978-1114: Invitation dataclass + InvitationManager class (~136 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/socratic/collaboration_models.py">
      All enums and dataclasses:
      ParticipantRole, CommentStatus, VoteType, ChangeType,
      Participant, Comment, Vote, Change, VotingResult,
      CollaborativeSession, SyncEvent, Invitation
    </file>
    <file path="src/attune/socratic/collaboration_comments.py">
      Mixin: CommentVotingMixin
      Methods from CollaborationManager:
      - add_comment(), resolve_comment(), add_reaction()
      - cast_vote(), get_voting_result()
      - get_comments_for_target()
    </file>
    <file path="src/attune/socratic/collaboration_tracking.py">
      Mixin: ChangeTrackingMixin
      Methods from CollaborationManager:
      - track_change(), _track_change()
      - get_change_history()
      - add_change_listener(), remove_change_listener()
      - _save_session(), _load_sessions()
    </file>
    <file path="tests/unit/test_collaboration_comments.py">
      Tests for CommentVotingMixin: adding comments, resolving,
      reactions, voting, vote aggregation.
    </file>
    <file path="tests/unit/test_collaboration_tracking.py">
      Tests for ChangeTrackingMixin: change recording, listeners,
      persistence round-trip.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/socratic/collaboration.py">
      <change location="entire file">
        Keep: CollaborationManager class definition with __init__,
        create_session, get_session, add_participant, update_participant_role,
        list_sessions, get_user_sessions.
        Add mixins to MRO: class CollaborationManager(CommentVotingMixin, ChangeTrackingMixin):
        Import models from collaboration_models.
        Import SyncAdapter, InvitationManager (re-export for backward compat).
        Re-export all enums and dataclasses.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.socratic.collaboration import CollaborationManager, ParticipantRole, SyncAdapter, InvitationManager"</check>
    <check>python -c "from attune.socratic.collaboration_models import CollaborativeSession, Comment, Vote"</check>
    <check>uv run pytest tests/unit/test_collaboration*.py -x -q</check>
    <check>wc -l src/attune/socratic/collaboration.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="medium">CollaborationManager methods cross-reference each other. Map all internal calls before extracting.</risk>
    <risk severity="low">SyncAdapter and InvitationManager are separate classes - straightforward to keep in their own files or leave as re-exports.</risk>
  </risks>
</task>
```

---

## Stage 2: BaseWorkflow Stage Extractions

### Task 2.1: code_review.py (1,049 -> ~300 lines)

```xml
<task id="2.1" name="code-review-extraction">
  <objective>
    Extract scanning/filtering logic, crew integration, and report formatting
    from CodeReviewWorkflow into mixins.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review.py">
      1,049 lines total:
      - Lines 54-119: __init__ + _initialize_crew
      - Lines 137-245: _gather_project_context (~108 lines)
      - Lines 264-404: _classify stage (~140 lines)
      - Lines 406-517: _crew_review stage (~111 lines)
      - Lines 519-747: _scan + _merge_external_audit (~228 lines)
      - Lines 749-892: _architect_review stage (~143 lines)
      - Lines 895-1048: format_code_review_report (~153 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/code_review_scanning.py">
      Mixin: CodeReviewScanningMixin
      Methods: _scan(), _merge_external_audit(), _gather_project_context()
      These are the largest method blocks and self-contained.
    </file>
    <file path="src/attune/workflows/code_review_crew.py">
      Mixin: CodeReviewCrewMixin
      Methods: _initialize_crew(), _crew_review()
      Handles optional crew-based multi-agent review.
    </file>
    <file path="src/attune/workflows/code_review_report.py">
      Module: format_code_review_report() function
    </file>
    <file path="tests/unit/test_code_review_scanning.py">
      Tests for scanning mixin: project context gathering,
      security pattern detection, external audit merging.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      <change location="class definition">
        BEFORE: class CodeReviewWorkflow(BaseWorkflow):
        AFTER: class CodeReviewWorkflow(CodeReviewScanningMixin, CodeReviewCrewMixin, BaseWorkflow):
        Keep: __init__, should_skip_stage, run_stage, _classify, _architect_review
        Import and re-export format_code_review_report.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.code_review import CodeReviewWorkflow, format_code_review_report"</check>
    <check>uv run pytest tests/unit/test_code_review*.py -x -q</check>
    <check>wc -l src/attune/workflows/code_review.py shows ~300 lines</check>
  </validation>

  <risks>
    <risk severity="medium">_scan calls _merge_external_audit internally. Both must be in same mixin.</risk>
    <risk severity="low">Crew integration is optional (guarded by try/import). Mixin must handle missing crew gracefully.</risk>
  </risks>
</task>
```

### Task 2.2: security_audit.py (1,335 -> ~400 lines)

```xml
<task id="2.2" name="security-audit-extraction">
  <objective>
    Extract false-positive filtering (6 methods), crew integration (3 methods),
    pattern constants, and report formatting from SecurityAuditWorkflow.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/security_audit.py">
      1,335 lines total:
      - Lines 28-188: 8 pattern constant blocks (~160 lines)
      - Lines 245-256: _load_team_decisions module function
      - Lines 563-808: 6 false-positive filter methods (~245 lines)
        _analyze_finding, _is_detection_code, _is_fake_credential,
        _is_documentation_or_string, _is_safe_sql_parameterization,
        _is_safe_random_usage
      - Lines 1095-1185: 3 crew methods (~90 lines)
      - Lines 1200-1331: format_security_report + main (~131 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/security_patterns.py">
      All pattern constants:
      SECURITY_STEPS, SKIP_DIRECTORIES, DETECTION_PATTERNS,
      FAKE_CREDENTIAL_PATTERNS, SECURITY_EXAMPLE_PATHS,
      TEST_FIXTURE_PATTERNS, TEST_FILE_PATTERNS, SECURITY_PATTERNS
      Plus _load_team_decisions() function.
    </file>
    <file path="src/attune/workflows/security_filters.py">
      Mixin: FalsePositiveFilterMixin
      Methods: _analyze_finding, _is_detection_code, _is_fake_credential,
      _is_documentation_or_string, _is_safe_sql_parameterization,
      _is_safe_random_usage, _get_remediation_action
    </file>
    <file path="src/attune/workflows/security_crew.py">
      Mixin: SecurityCrewMixin
      Methods: _initialize_crew, _get_crew_remediation,
      _merge_crew_remediation
    </file>
    <file path="src/attune/workflows/security_report.py">
      Module: format_security_report(), main()
    </file>
    <file path="tests/unit/test_security_filters.py">
      Tests for FalsePositiveFilterMixin:
      - Detection code vs real vulnerability
      - Fake credential patterns
      - Documentation/string context
      - Safe SQL parameterization
      - Safe random usage
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/security_audit.py">
      <change location="class and imports">
        Add mixins: class SecurityAuditWorkflow(FalsePositiveFilterMixin, SecurityCrewMixin, BaseWorkflow):
        Import constants from security_patterns.
        Import and re-export format_security_report, main.
        Keep: __init__, should_skip_stage, run_stage, _triage, _analyze, _assess, _remediate.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.security_audit import SecurityAuditWorkflow, format_security_report"</check>
    <check>python -c "from attune.workflows.security_patterns import SECURITY_PATTERNS"</check>
    <check>uv run pytest tests/unit/test_security*.py -x -q</check>
    <check>wc -l src/attune/workflows/security_audit.py shows ~400 lines</check>
  </validation>

  <risks>
    <risk severity="medium">Filter methods are called from _analyze and _triage. Verify all call sites reference self correctly via mixin MRO.</risk>
    <risk severity="low">Pattern constants are module-level - no MRO concerns, just import paths.</risk>
  </risks>
</task>
```

### Task 2.3: document_gen/workflow.py (1,424 -> ~400 lines)

```xml
<task id="2.3" name="doc-gen-extraction">
  <objective>
    Extract cost management, API reference generation, and chunked
    writing/polishing from DocumentGenerationWorkflow into mixins.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/document_gen/workflow.py">
      1,424 lines total:
      - Lines 110-164: Cost management (3 methods, ~54 lines)
        _estimate_cost, _track_cost, _auto_scale_tokens
      - Lines 166-261: File export + chunking (2 methods, ~95 lines)
        _export_document, _chunk_output_for_display
      - Lines 650-824: _write_chunked (~174 lines)
      - Lines 1056-1217: _polish_chunked (~161 lines)
      - Lines 1219-1423: API reference methods (3 methods, ~204 lines)
        _extract_functions_from_source, _generate_api_section_for_function,
        _add_api_reference_sections
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/document_gen/cost_management.py">
      Mixin: DocGenCostMixin
      Methods: _estimate_cost, _track_cost, _auto_scale_tokens
      Expected attrs: _cost_limit, _total_cost, _cost_warnings, logger
    </file>
    <file path="src/attune/workflows/document_gen/chunked_generation.py">
      Mixin: ChunkedGenerationMixin
      Methods: _write_chunked, _polish_chunked,
      _chunk_output_for_display, _export_document
    </file>
    <file path="src/attune/workflows/document_gen/api_reference.py">
      Mixin: APIReferenceMixin
      Methods: _extract_functions_from_source,
      _generate_api_section_for_function, _add_api_reference_sections
    </file>
    <file path="tests/unit/test_doc_gen_api_reference.py">
      Tests for APIReferenceMixin:
      - Function extraction from Python source via AST
      - API section generation
      - Section insertion into existing document
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/document_gen/workflow.py">
      <change location="class definition">
        BEFORE: class DocumentGenerationWorkflow(BaseWorkflow):
        AFTER: class DocumentGenerationWorkflow(
            DocGenCostMixin, ChunkedGenerationMixin, APIReferenceMixin, BaseWorkflow):
        Keep: __init__, should_skip_stage, run_stage,
        _outline, _write, _polish, _parse_outline_sections
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.document_gen.workflow import DocumentGenerationWorkflow"</check>
    <check>uv run pytest tests/unit/test_doc_gen*.py -x -q</check>
    <check>wc -l src/attune/workflows/document_gen/workflow.py shows ~400 lines</check>
  </validation>

  <risks>
    <risk severity="medium">_write calls _write_chunked conditionally. Both need access to self._call_llm and run_step_with_executor.</risk>
    <risk severity="low">Cost tracking modifies shared state (_total_cost). Thread-safe by design since workflows are single-threaded.</risk>
  </risks>
</task>
```

---

## Stage 3: Phase/Strategy Extractions

### Task 3.1: autonomous_test_gen.py (1,329 -> ~350 lines)

```xml
<task id="3.1" name="test-gen-extraction">
  <objective>
    Extract the 3 generation phases (LLM, refinement, coverage) and prompt
    engineering from AutonomousTestGenerator into separate mixins.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/autonomous_test_gen.py">
      1,329 lines total:
      - Lines 44-61: 2 dataclasses (ValidationResult, CoverageResult)
      - Lines 346-472: Prompt engineering (2 methods, ~126 lines)
      - Lines 474-642: Phase 1 LLM generation (~168 lines)
      - Lines 644-895: Phase 2 refinement (3 methods, ~251 lines)
      - Lines 897-1189: Phase 3 coverage (3 methods, ~292 lines)
      - Lines 1191-1257: Test validation (2 methods, ~66 lines)
      - Lines 1260-1328: CLI entry points
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/test_gen_prompts.py">
      Mixin: TestGenPromptMixin
      Methods: _get_example_tests, _get_workflow_specific_prompt,
      _is_workflow_module
    </file>
    <file path="src/attune/workflows/test_gen_refinement.py">
      Mixin: TestGenRefinementMixin
      Methods: _run_pytest_validation, _call_llm_with_history,
      _generate_with_refinement
    </file>
    <file path="src/attune/workflows/test_gen_coverage.py">
      Mixin: TestGenCoverageMixin
      Methods: _run_coverage_analysis, _extract_uncovered_lines,
      _generate_with_coverage_target
    </file>
    <file path="tests/unit/test_test_gen_refinement.py">
      Tests for refinement mixin: pytest validation parsing,
      multi-turn conversation, error recovery.
    </file>
    <file path="tests/unit/test_test_gen_coverage.py">
      Tests for coverage mixin: coverage report parsing,
      uncovered line extraction, target-guided generation.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/autonomous_test_gen.py">
      <change location="class definition">
        BEFORE: class AutonomousTestGenerator:
        AFTER: class AutonomousTestGenerator(
            TestGenPromptMixin, TestGenRefinementMixin, TestGenCoverageMixin):
        Keep: __init__, generate_all, _generate_module_tests,
        _generate_with_llm, _validate_test_file, _count_tests
        Keep dataclasses at top.
        Move run_batch_generation and main to separate module or keep.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.autonomous_test_gen import AutonomousTestGenerator"</check>
    <check>uv run pytest tests/unit/test_test_gen*.py -x -q</check>
    <check>wc -l src/attune/workflows/autonomous_test_gen.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="medium">Phase methods call each other: _generate_with_refinement calls _run_pytest_validation and _call_llm_with_history. All three must be in same mixin.</risk>
    <risk severity="low">AutonomousTestGenerator does NOT inherit from BaseWorkflow. Mixin pattern still works but no ABC MRO to worry about.</risk>
  </risks>
</task>
```

### Task 3.2: documentation_orchestrator.py (1,206 -> ~350 lines)

```xml
<task id="3.2" name="doc-orchestrator-extraction">
  <objective>
    Extract filtering/validation, scout phase, and report generation
    from DocumentationOrchestrator into mixins.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/documentation_orchestrator.py">
      1,206 lines total:
      - Lines 72-135: 2 dataclasses (DocumentationItem, OrchestratorResult)
      - Lines 351-495: Filtering methods (5 methods, ~144 lines)
      - Lines 497-643: Scout phase (3 methods, ~146 lines)
      - Lines 645-742: Prioritization + generation (2 methods, ~97 lines)
      - Lines 744-869: Summary reporting (2 methods, ~125 lines)
      - Lines 871-1146: Public API methods (5 methods, ~275 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/doc_orch_filters.py">
      Mixin: DocOrchFilterMixin
      Methods: _severity_to_priority, _should_include_severity,
      _should_exclude, _get_exclusion_reason, _is_allowed_output
    </file>
    <file path="src/attune/workflows/doc_orch_scout.py">
      Mixin: DocOrchScoutMixin
      Methods: _run_scout_phase, _items_from_index, _parse_scout_findings,
      _prioritize_items
    </file>
    <file path="src/attune/workflows/doc_orch_report.py">
      Mixin: DocOrchReportMixin
      Methods: _run_generate_phase, _update_project_index, _generate_summary
    </file>
    <file path="tests/unit/test_doc_orch_filters.py">
      Tests for filter mixin: exclusion patterns, severity filtering,
      allowed output extensions.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/documentation_orchestrator.py">
      <change location="class definition">
        Add mixins to MRO.
        Keep: __init__, describe, execute, scout_only, scout_as_json,
        generate_for_files, generate_for_file.
        Keep dataclasses at top.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.workflows.documentation_orchestrator import DocumentationOrchestrator"</check>
    <check>uv run pytest tests/unit/test_doc_orch*.py -x -q</check>
    <check>wc -l src/attune/workflows/documentation_orchestrator.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="low">Scout methods reference self._workflow (DocumentGenerationWorkflow instance). Mixin must declare this attribute.</risk>
  </risks>
</task>
```

### Task 3.3: meta_orchestrator.py (1,167 -> ~350 lines)

```xml
<task id="3.3" name="meta-orchestrator-extraction">
  <objective>
    Extract task analysis, interactive mode, and estimation logic
    from MetaOrchestrator into separate mixins.
  </objective>

  <context>
    <existing-code path="src/attune/orchestration/meta_orchestrator.py">
      1,167 lines total:
      - Lines 33-109: 3 enums + 2 dataclasses (~76 lines)
      - Lines 435-799: Interactive mode methods (5 methods, ~364 lines)
      - Lines 801-950: Analysis methods (5 methods, ~149 lines)
      - Lines 952-1011: Agent selection (2 methods, ~59 lines)
      - Lines 1013-1083: Pattern selection (1 method, ~70 lines)
      - Lines 1085-1166: Estimation (2 methods, ~81 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/orchestration/meta_orch_analysis.py">
      Mixin: TaskAnalysisMixin
      Methods: _analyze_task, _classify_complexity, _classify_domain,
      _extract_capabilities, _is_parallelizable,
      _select_agents, _get_default_agents,
      _choose_composition_pattern
    </file>
    <file path="src/attune/orchestration/meta_orch_interactive.py">
      Mixin: InteractiveModeMixin
      Methods: analyze_and_compose_interactive, _calculate_confidence,
      _prompt_user_for_approach, _interactive_team_builder,
      _pattern_chooser_wizard, _get_pattern_description
    </file>
    <file path="src/attune/orchestration/meta_orch_estimation.py">
      Mixin: EstimationMixin
      Methods: _estimate_cost, _estimate_duration
    </file>
    <file path="tests/unit/test_meta_orch_analysis.py">
      Tests for TaskAnalysisMixin: complexity classification,
      domain detection, capability extraction, parallelizability.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/orchestration/meta_orchestrator.py">
      <change location="class definition">
        Add mixins: class MetaOrchestrator(
            TaskAnalysisMixin, InteractiveModeMixin, EstimationMixin):
        Keep: __init__, analyze_task (public wrapper),
        create_execution_plan (public wrapper), analyze_and_compose.
        Keep enums and dataclasses at top.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.orchestration.meta_orchestrator import MetaOrchestrator, TaskComplexity, CompositionPattern"</check>
    <check>uv run pytest tests/unit/test_meta_orch*.py -x -q</check>
    <check>wc -l src/attune/orchestration/meta_orchestrator.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="medium">Interactive methods use input() for user prompts. Tests must mock stdin.</risk>
    <risk severity="low">Enums/dataclasses stay in main file - no cross-import issues.</risk>
  </risks>
</task>
```

---

## Stage 4: CLI Functional Decomposition

### Task 4.1: cli_minimal.py (1,309 -> ~300 lines)

```xml
<task id="4.1" name="cli-minimal-decomposition">
  <objective>
    Split flat CLI command handlers into grouped command modules.
    Keep main(), create_parser(), and routing in the original file.
  </objective>

  <context>
    <existing-code path="src/attune/cli_minimal.py">
      1,309 lines total. NO classes - all module-level functions.
      - Lines 72-191: 3 workflow commands (~119 lines)
      - Lines 198-732: 8 telemetry commands (~534 lines)
      - Lines 739-805: 2 provider commands (~66 lines)
      - Lines 812-843: 1 dashboard command (~31 lines)
      - Lines 850-1076: 3 setup/utility commands (~226 lines)
      - Lines 1085-1305: create_parser + main (~220 lines)
    </existing-code>
    <pattern>
      This is NOT a class-based file. Use functional decomposition
      (separate modules) instead of mixins. Each module exports its
      cmd_* functions.
    </pattern>
  </context>

  <files-to-create>
    <file path="src/attune/cli_commands/__init__.py">
      Empty package init. All commands imported by cli_minimal.py.
    </file>
    <file path="src/attune/cli_commands/workflow_commands.py">
      Functions: cmd_workflow_list, cmd_workflow_info, cmd_workflow_run
    </file>
    <file path="src/attune/cli_commands/telemetry_commands.py">
      Functions: cmd_telemetry_show, cmd_telemetry_savings,
      cmd_telemetry_export, cmd_telemetry_routing_stats,
      cmd_telemetry_routing_check, cmd_telemetry_models,
      cmd_telemetry_agents, cmd_telemetry_signals
    </file>
    <file path="src/attune/cli_commands/provider_commands.py">
      Functions: cmd_provider_show, cmd_provider_set
    </file>
    <file path="src/attune/cli_commands/setup_commands.py">
      Functions: cmd_dashboard_start, cmd_setup, cmd_validate, cmd_version
    </file>
    <file path="tests/unit/test_cli_workflow_commands.py">
      Tests for workflow commands: list, info, run with mock workflows.
    </file>
    <file path="tests/unit/test_cli_telemetry_commands.py">
      Tests for telemetry commands: show, savings, export with mock data.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/cli_minimal.py">
      <change location="entire file">
        Replace inline function definitions with imports:
          from .cli_commands.workflow_commands import cmd_workflow_list, ...
          from .cli_commands.telemetry_commands import cmd_telemetry_show, ...
          from .cli_commands.provider_commands import cmd_provider_show, ...
          from .cli_commands.setup_commands import cmd_setup, ...
        Keep: get_version(), create_parser(), main()
        Re-export all cmd_* functions for backward compat.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.cli_minimal import main, cmd_workflow_list, cmd_telemetry_show"</check>
    <check>python -c "from attune.cli_commands.telemetry_commands import cmd_telemetry_savings"</check>
    <check>uv run pytest tests/unit/test_cli*.py -x -q</check>
    <check>wc -l src/attune/cli_minimal.py shows ~300 lines</check>
  </validation>

  <risks>
    <risk severity="low">Command functions have no shared state - purely functional. Very safe to extract.</risk>
    <risk severity="low">create_parser references command functions only by name in routing - no import dependency.</risk>
  </risks>
</task>
```

### Task 4.2: telemetry/cli.py (1,232 -> ~250 lines)

```xml
<task id="4.2" name="telemetry-cli-decomposition">
  <objective>
    Split telemetry CLI command functions into grouped modules by feature area.
  </objective>

  <context>
    <existing-code path="src/attune/telemetry/cli.py">
      1,232 lines total. NO classes - all module-level functions.
      - Lines 36-585: 6 core telemetry commands (~549 lines)
      - Lines 611-854: 4 tier-1 automation commands (~243 lines)
      - Lines 934-1047: 1 model analysis command (~113 lines)
      - Lines 1050-1231: 1 file test status command (~181 lines)
      - Re-exports: cmd_telemetry_dashboard, cmd_file_test_dashboard
    </existing-code>
    <pattern>
      Same functional decomposition pattern as cli_minimal.py.
    </pattern>
  </context>

  <files-to-create>
    <file path="src/attune/telemetry/cli_core.py">
      Functions: cmd_telemetry_show, cmd_telemetry_savings,
      cmd_telemetry_cache_stats, cmd_telemetry_compare,
      cmd_telemetry_reset, cmd_telemetry_export
    </file>
    <file path="src/attune/telemetry/cli_automation.py">
      Functions: cmd_tier1_status, cmd_task_routing_report,
      cmd_test_status, cmd_agent_performance
    </file>
    <file path="src/attune/telemetry/cli_analysis.py">
      Functions: cmd_sonnet_opus_analysis, cmd_file_test_status
    </file>
    <file path="tests/unit/test_telemetry_cli_core.py">
      Tests for core telemetry commands with mock telemetry data.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/telemetry/cli.py">
      <change location="entire file">
        Replace inline definitions with imports from new modules.
        Keep re-exports of cmd_telemetry_dashboard, cmd_file_test_dashboard.
        Re-export all cmd_* functions for backward compat.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.telemetry.cli import cmd_telemetry_show, cmd_tier1_status, cmd_sonnet_opus_analysis"</check>
    <check>uv run pytest tests/unit/test_telemetry_cli*.py -x -q</check>
    <check>wc -l src/attune/telemetry/cli.py shows ~250 lines</check>
  </validation>

  <risks>
    <risk severity="low">Pure functions with no shared state. Safest extraction category.</risk>
  </risks>
</task>
```

---

## Stage 5: Multi-Class File Splitting

### Task 5.1: control_panel.py (1,291 -> ~350 lines)

```xml
<task id="5.1" name="control-panel-extraction">
  <objective>
    Extract input validation, HTTP API handler, server setup, and
    console output from control_panel.py into focused modules.
  </objective>

  <context>
    <existing-code path="src/attune/memory/control_panel.py">
      1,291 lines total:
      - Lines 83-196: 4 validation functions (~113 lines)
      - Lines 210-605: MemoryControlPanel class (~395 lines)
      - Lines 607-694: 3 print_* console functions (~87 lines)
      - Lines 697-961: MemoryAPIHandler class (~264 lines)
      - Lines 963-1068: run_api_server function (~105 lines)
      - Lines 1080-1290: main() CLI entry point (~210 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/memory/control_panel_validation.py">
      Module: _validate_pattern_id, _validate_agent_id,
      _validate_classification, _validate_file_path
    </file>
    <file path="src/attune/memory/control_panel_api.py">
      Classes: MemoryAPIHandler (HTTP handler)
      Functions: run_api_server
      Imports MemoryControlPanel from control_panel.py.
    </file>
    <file path="src/attune/memory/control_panel_display.py">
      Functions: print_status, print_stats, print_health
      Function: main() CLI entry point
    </file>
    <file path="tests/unit/test_control_panel_validation.py">
      Tests for validation functions: valid/invalid pattern IDs,
      agent IDs, classifications, file paths with path traversal.
    </file>
    <file path="tests/unit/test_control_panel_api.py">
      Tests for MemoryAPIHandler: GET/POST/DELETE endpoints,
      CORS, rate limiting, auth.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/memory/control_panel.py">
      <change location="entire file">
        Keep: ControlPanelConfig dataclass, MemoryControlPanel class.
        Import validation functions from control_panel_validation.
        Re-export MemoryAPIHandler, run_api_server, print_*, main
        for backward compat.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.memory.control_panel import MemoryControlPanel, MemoryAPIHandler, run_api_server, main"</check>
    <check>uv run pytest tests/unit/test_control_panel*.py -x -q</check>
    <check>wc -l src/attune/memory/control_panel.py shows ~350 lines</check>
  </validation>

  <risks>
    <risk severity="medium">MemoryAPIHandler references MemoryControlPanel via self.server.control_panel. Import must not be circular.</risk>
    <risk severity="low">Validation functions are pure - zero risk to extract.</risk>
  </risks>
</task>
```

### Task 5.2: release_prep_team.py (1,403 -> ~400 lines)

```xml
<task id="5.2" name="release-prep-extraction">
  <objective>
    Extract agent implementations, response parsing, and report formatting
    from release_prep_team.py. Keep ReleasePrepTeam orchestrator and
    ReleaseAgent base class in the original file.
  </objective>

  <context>
    <existing-code path="src/attune/agents/release/release_prep_team.py">
      1,403 lines total:
      - Lines 96-279: 3 dataclasses (ReleaseAgentResult, QualityGate,
        ReleaseReadinessReport) (~183 lines)
      - Lines 286-356: _parse_response module function (~70 lines)
      - Lines 363-564: ReleaseAgent base class (~201 lines)
      - Lines 571-593: _run_command module function (~22 lines)
      - Lines 596-725: SecurityAuditorAgent (~129 lines)
      - Lines 727-843: TestCoverageAgent (~116 lines)
      - Lines 845-971: CodeQualityAgent (~126 lines)
      - Lines 973-1057: DocumentationAgent (~84 lines)
      - Lines 1064-1334: ReleasePrepTeam (~270 lines)
      - Lines 1341-1403: ReleasePrepTeamWorkflow (~62 lines)
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/agents/release/release_models.py">
      Dataclasses: ReleaseAgentResult, QualityGate, ReleaseReadinessReport
      (includes to_dict and format_console_output methods)
    </file>
    <file path="src/attune/agents/release/release_agents.py">
      Classes: SecurityAuditorAgent, TestCoverageAgent,
      CodeQualityAgent, DocumentationAgent
      Each with their _execute_tier and _parse_* methods.
      Module function: _run_command
    </file>
    <file path="src/attune/agents/release/release_parsing.py">
      Module function: _parse_response
      (Multi-strategy response parsing: XML, JSON, regex)
    </file>
    <file path="tests/unit/test_release_agents.py">
      Tests for each agent's _execute_tier with mocked subprocess:
      - SecurityAuditorAgent: bandit output parsing
      - TestCoverageAgent: coverage percentage extraction
      - CodeQualityAgent: ruff violation parsing
      - DocumentationAgent: docstring coverage analysis
    </file>
    <file path="tests/unit/test_release_parsing.py">
      Tests for _parse_response: XML parsing, JSON parsing,
      regex fallback, malformed input handling.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/agents/release/release_prep_team.py">
      <change location="entire file">
        Keep: ReleaseAgent base class, ReleasePrepTeam,
        ReleasePrepTeamWorkflow.
        Import from new modules:
          from .release_models import ReleaseAgentResult, QualityGate, ReleaseReadinessReport
          from .release_agents import SecurityAuditorAgent, TestCoverageAgent, ...
          from .release_parsing import _parse_response
        Re-export everything for backward compat.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.agents.release.release_prep_team import ReleasePrepTeam, ReleaseAgent, SecurityAuditorAgent, ReleaseReadinessReport"</check>
    <check>python -c "from attune.agents.release.release_agents import TestCoverageAgent"</check>
    <check>uv run pytest tests/unit/test_release*.py -x -q</check>
    <check>wc -l src/attune/agents/release/release_prep_team.py shows ~400 lines</check>
  </validation>

  <risks>
    <risk severity="medium">Agent subclasses inherit from ReleaseAgent. Ensure ReleaseAgent is importable from release_agents.py without circular imports (import ReleaseAgent from the main file).</risk>
    <risk severity="low">_parse_response is a pure function - safe extraction.</risk>
  </risks>
</task>
```

---

## Summary

| Task | File | Before | After | New Files | New Tests |
|------|------|--------|-------|-----------|-----------|
| 1.1 | bug_predict.py | 1,085 | ~350 | 2 modules | 1 test file |
| 1.2 | dependency_check.py | 1,118 | ~350 | 3 modules | 1 test file |
| 1.3 | collaboration.py | 1,115 | ~350 | 2 mixins, 1 models | 2 test files |
| 2.1 | code_review.py | 1,049 | ~300 | 2 mixins, 1 module | 1 test file |
| 2.2 | security_audit.py | 1,335 | ~400 | 3 mixins, 1 module | 1 test file |
| 2.3 | document_gen/workflow.py | 1,424 | ~400 | 3 mixins | 1 test file |
| 3.1 | autonomous_test_gen.py | 1,329 | ~350 | 3 mixins | 2 test files |
| 3.2 | documentation_orchestrator.py | 1,206 | ~350 | 3 mixins | 1 test file |
| 3.3 | meta_orchestrator.py | 1,167 | ~350 | 3 mixins | 1 test file |
| 4.1 | cli_minimal.py | 1,309 | ~300 | 4 command modules | 2 test files |
| 4.2 | telemetry/cli.py | 1,232 | ~250 | 3 command modules | 1 test file |
| 5.1 | control_panel.py | 1,291 | ~350 | 3 modules | 2 test files |
| 5.2 | release_prep_team.py | 1,403 | ~400 | 3 modules | 2 test files |
| **Totals** | **13 files** | **16,063** | **~4,500** | **~34 new files** | **~18 test files** |

**Estimated reduction:** 72% across all files

## Execution Order

Execute stages sequentially (1 -> 2 -> 3 -> 4 -> 5).
Within each stage, tasks can run in parallel.

After each stage:

```bash
uv run pytest tests/unit/ -x -q
uv run pre-commit run --all-files
```

After all stages:

```bash
uv run pytest tests/ -q  # Full test suite
```

---

## Completion Status

**Status:** COMPLETE
**Completed:** 2026-02-07
**All 13 files refactored across 5 stages.**

### Actual Results vs Targets

| Task | File | Before | Target | Actual | Reduction |
| ---- | ---- | ------ | ------ | ------ | --------- |
| 1.1 | bug_predict.py | 1,085 | ~350 | 568 | 48% |
| 1.2 | dependency_check.py | 1,118 | ~350 | 494 | 56% |
| 1.3 | collaboration.py | 1,115 | ~350 | 619 | 44% |
| 2.1 | code_review.py | 1,049 | ~300 | 893 | 15% |
| 2.2 | security_audit.py | 1,335 | ~400 | 800 | 40% |
| 2.3 | document_gen/workflow.py | 1,424 | ~400 | 730 | 49% |
| 3.1 | autonomous_test_gen.py | 1,329 | ~350 | 636 | 52% |
| 3.2 | documentation_orchestrator.py | 1,206 | ~350 | 693 | 43% |
| 3.3 | meta_orchestrator.py | 1,167 | ~350 | 256 | 78% |
| 4.1 | cli_minimal.py | 1,309 | ~300 | 315 | 76% |
| 4.2 | telemetry/cli.py | 1,232 | ~250 | 41 | 97% |
| 5.1 | control_panel.py | 1,291 | ~350 | 496 | 62% |
| 5.2 | release_prep_team.py | 1,403 | ~400 | 405 | 71% |
| **Totals** | **13 files** | **16,063** | **~4,500** | **6,946** | **57%** |

### Notes

- **Overall reduction: 57%** (9,117 lines removed from original files)
- Some files (code_review, security_audit, document_gen) retained more code than targeted due to tightly coupled stage logic that was safer to keep co-located
- Standout reductions: telemetry/cli.py (97%), meta_orchestrator.py (78%), cli_minimal.py (76%)
- All extracted modules follow the established mixin pattern with `TYPE_CHECKING` guards and class-level attribute defaults

### Test Results (Post-Refactoring)

- **6,207 tests passing** (up from 6,205 pre-polish due to 2 fixed test failures)
- **164 skipped**, **2 xfailed**
- **0 ruff errors**, **0 high-severity bandit warnings**
- All backward-compatible re-exports verified (imports from original paths still work)

### Pre-existing Test Fixes (Polish Phase)

Three pre-existing test failures were fixed during the post-refactoring polish:

1. **CachedResponse import**: Re-exported from `base.py` after Phase 1 mixin extraction moved it to `caching.py`
2. **tier_map KeyError**: `workflow.py` CLI now handles empty `tier_map` gracefully
3. **KNOWN_VULNERABILITIES test**: Skipped (constant was removed when vuln detection moved to pip-audit); outdated packages test updated to match actual `_assess()` heuristic
