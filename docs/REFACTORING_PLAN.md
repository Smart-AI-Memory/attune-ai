# Large File Refactoring Plan

**Created:** 2026-02-02
**Status:** Planning
**Owner:** Engineering Team

---

<refactoring-overview>
  <description>
    Staged refactoring of 4 large files to improve maintainability, testability, and code organization.
  </description>

  <candidates>
    <candidate priority="1">
      <file>src/attune/memory/short_term.py</file>
      <lines>2197</lines>
      <issue>God class with 50+ methods covering multiple concerns</issue>
      <imports>28</imports>
      <impact>highest</impact>
    </candidate>
    <candidate priority="2">
      <file>src/attune/workflows/base.py</file>
      <lines>2672</lines>
      <issue>Mixed data models and workflow logic</issue>
      <imports>13</imports>
      <impact>high</impact>
    </candidate>
    <candidate priority="3">
      <file>src/attune/core.py</file>
      <lines>1701</lines>
      <issue>Multiple classes that could be separate modules</issue>
      <imports>core-module</imports>
      <impact>medium</impact>
    </candidate>
    <candidate priority="4">
      <file>src/attune/orchestration/execution_strategies.py</file>
      <lines>2112</lines>
      <issue>Large file with multiple strategy classes</issue>
      <imports>specialized</imports>
      <impact>lower</impact>
    </candidate>
  </candidates>
</refactoring-overview>

---

## Stage 1: memory/short_term.py

<stage id="1" priority="highest">
  <goal>Split god class into focused, single-responsibility modules</goal>

  <current-state>
    <file>src/attune/memory/short_term.py</file>
    <class>RedisShortTermMemory</class>
    <methods>50+</methods>
    <concerns>
      <concern>CRUD operations (store, retrieve, delete)</concern>
      <concern>Caching layer</concern>
      <concern>Pattern staging</concern>
      <concern>Session management</concern>
      <concern>Pub/Sub messaging</concern>
      <concern>Redis Streams</concern>
      <concern>Timeline management</concern>
      <concern>Queue operations</concern>
    </concerns>
  </current-state>

  <target-structure>
    <directory>src/attune/memory/short_term/</directory>
    <modules>
      <module name="__init__.py">Re-exports RedisShortTermMemory for backward compatibility</module>
      <module name="base.py">Core CRUD operations (store, retrieve, delete)</module>
      <module name="caching.py">Cache layer (get_cached, invalidate, ttl)</module>
      <module name="patterns.py">Pattern staging (stage_pattern, get_staged)</module>
      <module name="sessions.py">Session management (create_session, end_session)</module>
      <module name="pubsub.py">Pub/Sub messaging (publish, subscribe)</module>
      <module name="streams.py">Redis Streams (add_to_stream, read_stream)</module>
      <module name="timelines.py">Timeline management (add_event, get_timeline)</module>
      <module name="queues.py">Queue operations (enqueue, dequeue)</module>
    </modules>
    <facade>src/attune/memory/short_term.py → thin facade composing all modules</facade>
  </target-structure>

  <phases>
    <phase number="1" name="analysis" risk="none">
      <tasks>
        <task>Map all methods to concern categories</task>
        <task>Identify method dependencies and shared state</task>
        <task>Document public API for backward compatibility</task>
        <task>Create test coverage report</task>
      </tasks>
    </phase>

    <phase number="2" name="structure" risk="low">
      <tasks>
        <task>Create short_term/ directory</task>
        <task>Create empty module files with docstrings</task>
        <task>Set up __init__.py with re-exports</task>
      </tasks>
    </phase>

    <phase number="3" name="extract-base" risk="low">
      <tasks>
        <task>Move core store/retrieve/delete to base.py</task>
        <task>Keep original methods as delegation calls</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="4" name="extract-caching" risk="medium">
      <tasks>
        <task>Move cache-related methods to caching.py</task>
        <task>Update internal references</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="5" name="extract-patterns" risk="medium">
      <tasks>
        <task>Move pattern staging to patterns.py</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="6" name="extract-sessions" risk="medium">
      <tasks>
        <task>Move session management to sessions.py</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="7" name="extract-isolated" risk="low">
      <tasks>
        <task>Move pub/sub to pubsub.py</task>
        <task>Move Redis Streams to streams.py</task>
        <task>Move timeline operations to timelines.py</task>
        <task>Move queue operations to queues.py</task>
        <task>Run tests after each</task>
      </tasks>
    </phase>

    <phase number="8" name="facade" risk="low">
      <tasks>
        <task>Convert RedisShortTermMemory to thin facade</task>
        <task>Compose all extracted modules</task>
        <task>Verify all 28 import sites work</task>
        <task>Full test suite</task>
      </tasks>
    </phase>
  </phases>

  <success-criteria>
    <criterion>All existing tests pass</criterion>
    <criterion>No breaking changes to public API</criterion>
    <criterion>Each module less than 300 lines</criterion>
    <criterion>Clear separation of concerns</criterion>
    <criterion>Import statements unchanged for consumers</criterion>
  </success-criteria>
</stage>

---

## Stage 2: workflows/base.py

<stage id="2" priority="high">
  <goal>Separate data models from workflow execution logic</goal>

  <current-state>
    <file>src/attune/workflows/base.py</file>
    <classes>
      <class type="enum">ModelTier</class>
      <class type="enum">ModelProvider</class>
      <class type="dataclass">WorkflowStage</class>
      <class type="dataclass">CostReport</class>
      <class type="dataclass">StageQualityMetrics</class>
      <class type="dataclass">WorkflowResult</class>
      <class type="base">BaseWorkflow</class>
    </classes>
  </current-state>

  <target-structure>
    <directory>src/attune/workflows/base/</directory>
    <modules>
      <module name="__init__.py">Re-exports all classes for backward compatibility</module>
      <module name="models.py">ModelTier, ModelProvider, WorkflowStage</module>
      <module name="cost.py">CostReport and cost calculation logic</module>
      <module name="quality.py">StageQualityMetrics</module>
      <module name="result.py">WorkflowResult</module>
      <module name="workflow.py">BaseWorkflow class</module>
    </modules>
    <facade>src/attune/workflows/base.py → from .base import *</facade>
  </target-structure>

  <phases>
    <phase number="1" name="analysis" risk="none">
      <tasks>
        <task>Catalog all classes and their relationships</task>
        <task>Map external dependencies</task>
        <task>Identify circular dependency risks</task>
      </tasks>
    </phase>

    <phase number="2" name="extract-models" risk="low">
      <tasks>
        <task>Create base/ directory structure</task>
        <task>Move ModelTier, ModelProvider to models.py</task>
        <task>Move WorkflowStage to models.py</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="3" name="extract-dataclasses" risk="low">
      <tasks>
        <task>Move CostReport to cost.py</task>
        <task>Move StageQualityMetrics to quality.py</task>
        <task>Move WorkflowResult to result.py</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="4" name="refactor-workflow" risk="medium">
      <tasks>
        <task>Keep BaseWorkflow in workflow.py</task>
        <task>Update imports from other modules</task>
        <task>Resolve any circular imports</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="5" name="facade" risk="low">
      <tasks>
        <task>Update base.py as re-export facade</task>
        <task>Verify all 13 import sites work</task>
        <task>Full workflow test suite</task>
      </tasks>
    </phase>
  </phases>

  <success-criteria>
    <criterion>All workflow tests pass</criterion>
    <criterion>No changes needed in workflow implementations</criterion>
    <criterion>Data models independently importable</criterion>
    <criterion>BaseWorkflow less than 500 lines</criterion>
  </success-criteria>
</stage>

---

## Stage 3: core.py

<stage id="3" priority="medium">
  <goal>Split into logical, single-purpose modules</goal>

  <current-state>
    <file>src/attune/core.py</file>
    <classes>
      <class type="dataclass">InteractionResponse</class>
      <class type="dataclass">CollaborationState</class>
      <class type="orchestrator">EmpathyOS</class>
    </classes>
  </current-state>

  <target-structure>
    <directory>src/attune/core/</directory>
    <modules>
      <module name="__init__.py">Re-exports EmpathyOS and key classes</module>
      <module name="response.py">InteractionResponse</module>
      <module name="state.py">CollaborationState</module>
      <module name="attune.py">EmpathyOS main orchestrator</module>
    </modules>
    <facade>src/attune/core.py → from .core import *</facade>
  </target-structure>

  <phases>
    <phase number="1" name="analysis" risk="none">
      <tasks>
        <task>Document InteractionResponse usage patterns</task>
        <task>Document CollaborationState usage patterns</task>
        <task>Map EmpathyOS responsibilities</task>
      </tasks>
    </phase>

    <phase number="2" name="extract" risk="low">
      <tasks>
        <task>Create core/ directory structure</task>
        <task>Extract InteractionResponse to response.py</task>
        <task>Extract CollaborationState to state.py</task>
        <task>Keep EmpathyOS in attune.py</task>
        <task>Run tests</task>
      </tasks>
    </phase>

    <phase number="3" name="facade" risk="low">
      <tasks>
        <task>Update core.py as re-export facade</task>
        <task>Verify all import sites work</task>
        <task>Full test suite</task>
      </tasks>
    </phase>
  </phases>

  <success-criteria>
    <criterion>Core functionality unchanged</criterion>
    <criterion>Clear module boundaries</criterion>
    <criterion>Each file less than 600 lines</criterion>
  </success-criteria>
</stage>

---

## Stage 4: orchestration/execution_strategies.py

<stage id="4" priority="lower">
  <goal>Split strategies into separate, focused modules</goal>

  <current-state>
    <file>src/attune/orchestration/execution_strategies.py</file>
    <description>Multiple execution strategy classes in single file</description>
  </current-state>

  <target-structure>
    <directory>src/attune/orchestration/execution_strategies/</directory>
    <modules>
      <module name="__init__.py">Re-exports all strategies</module>
      <module name="base.py">Base strategy class and interfaces</module>
      <module name="sequential.py">Sequential execution strategies</module>
      <module name="parallel.py">Parallel execution strategies</module>
      <module name="adaptive.py">Adaptive/dynamic strategies</module>
      <module name="fallback.py">Fallback and retry strategies</module>
    </modules>
    <facade>src/attune/orchestration/execution_strategies.py → re-export facade</facade>
  </target-structure>

  <phases>
    <phase number="1" name="analysis" risk="none">
      <tasks>
        <task>Identify all strategy classes</task>
        <task>Map inheritance hierarchy</task>
        <task>Document commonly used strategies</task>
      </tasks>
    </phase>

    <phase number="2" name="extract" risk="low">
      <tasks>
        <task>Create execution_strategies/ directory</task>
        <task>Extract base strategy class</task>
        <task>Extract each strategy type to own module</task>
        <task>Run tests after each extraction</task>
      </tasks>
    </phase>

    <phase number="3" name="facade" risk="low">
      <tasks>
        <task>Update facade for backward compatibility</task>
        <task>Full orchestration test suite</task>
      </tasks>
    </phase>
  </phases>

  <success-criteria>
    <criterion>All orchestration tests pass</criterion>
    <criterion>Strategy selection unchanged</criterion>
    <criterion>Each file less than 400 lines</criterion>
  </success-criteria>
</stage>

---

## Timeline

<timeline>
  <stage-estimate stage="1" file="memory/short_term.py" sessions="2-3" depends-on="none"/>
  <stage-estimate stage="2" file="workflows/base.py" sessions="1-2" depends-on="none"/>
  <stage-estimate stage="3" file="core.py" sessions="1" depends-on="none"/>
  <stage-estimate stage="4" file="execution_strategies.py" sessions="1" depends-on="none"/>
  <total-estimate>5-7 sessions</total-estimate>
</timeline>

---

## Risk Mitigation

<risk-mitigation>
  <strategy name="backward-compatibility">
    <rule>All original imports MUST continue to work</rule>
    <rule>Use facade pattern: old file imports from new modules</rule>
    <rule>Run full test suite after each extraction</rule>
    <example>
      # Old import still works:
      from attune.memory.short_term import RedisShortTermMemory

      # New granular import also available:
      from attune.memory.short_term.caching import CacheManager
    </example>
  </strategy>

  <strategy name="circular-imports">
    <rule>Extract data classes first (no dependencies)</rule>
    <rule>Use TYPE_CHECKING for type hints if needed</rule>
    <rule>Delay imports inside functions if necessary</rule>
    <example>
      from typing import TYPE_CHECKING

      if TYPE_CHECKING:
          from .workflow import BaseWorkflow
    </example>
  </strategy>

  <strategy name="testing">
    <rule>Never proceed without passing tests</rule>
    <rule>Add tests before extraction if coverage is low</rule>
    <rule>Integration tests for each refactored module</rule>
  </strategy>
</risk-mitigation>

---

## Rollback Plan

<rollback>
  <description>Each stage can be rolled back independently</description>
  <steps>
    <step>Delete new module directory</step>
    <step>Restore original file from git: git checkout HEAD -- path/to/file.py</step>
    <step>Run tests to verify restoration</step>
  </steps>
</rollback>

---

## Next Steps

<next-steps>
  <step status="pending">Review and approve this plan</step>
  <step status="pending">Start Stage 1: memory/short_term.py analysis phase</step>
  <step status="pending">Create GitHub tracking issue for each stage</step>
</next-steps>
