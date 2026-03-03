---
description: Test Creation Plan - Attune AI: **Created:** January 22, 2026 **Total Files Needing Tests:** 184 **Target Coverage:** 80%+ --- ## Executive Summary This
---

# Test Creation Plan - Attune AI

**Created:** January 22, 2026
**Total Files Needing Tests:** 184
**Target Coverage:** 80%+

---

## Executive Summary

This plan outlines the phased approach to create tests for all 184 files currently lacking test coverage. Files are prioritized by:
1. **Critical path** - Core functionality users depend on
2. **Security surface** - Files handling user input, file I/O, or authentication
3. **Complexity** - Higher complexity = higher risk of bugs
4. **Dependencies** - Files used by many other modules

---

## Phase 1: Core Models & Foundation (Priority: CRITICAL)
**Estimated: 25 files | Target: Week 1**

### 1.1 Models Module (12 files)
| File | Priority | Reason |
|------|----------|--------|
| `models/registry.py` | HIGH | Central model configuration |
| `models/executor.py` | HIGH | LLM execution interface |
| `models/empathy_executor.py` | HIGH | Main executor implementation |
| `models/fallback.py` | HIGH | Resilience patterns |
| `models/tasks.py` | MEDIUM | Task type definitions |
| `models/telemetry.py` | MEDIUM | Telemetry data structures |
| `models/validation.py` | MEDIUM | Config validation |
| `models/provider_config.py` | MEDIUM | Provider settings |
| `models/cli.py` | LOW | CLI wrapper |
| `models/__init__.py` | LOW | Exports only |
| `models/__main__.py` | LOW | Entry point |

### 1.2 Config Module (2 files)
| File | Priority | Reason |
|------|----------|--------|
| `config/__init__.py` | HIGH | Core config with security functions |
| `config/xml_config.py` | MEDIUM | XML configuration handling |

### 1.3 Core Files (3 files)
| File | Priority | Reason |
|------|----------|--------|
| `core.py` | HIGH | Central EmpathyOS class |
| `cli.py` | HIGH | Main CLI entry point |
| `config.py` | HIGH | Configuration management |

---

## Phase 2: Workflows (Priority: HIGH)
**Estimated: 37 files | Target: Week 2**

### 2.1 Core Workflow Infrastructure
| File | Priority | Reason |
|------|----------|--------|
| `workflows/base.py` | HIGH | Base workflow class |
| `workflows/config.py` | HIGH | Workflow configuration |
| `workflows/registry.py` | HIGH | Workflow registration |
| `workflows/runners.py` | MEDIUM | Execution runners |

### 2.2 Specific Workflows (33 files)
| File | Priority | Reason |
|------|----------|--------|
| `workflows/test_runner.py` | HIGH | Test execution |
| `workflows/test_gen.py` | HIGH | Test generation |
| `workflows/bug_predict.py` | HIGH | Bug prediction |
| `workflows/code_review_pipeline.py` | MEDIUM | Code review |
| `workflows/document_gen.py` | MEDIUM | Documentation |
| `workflows/batch_processing.py` | MEDIUM | Batch jobs |
| ... | ... | ... |

---

## Phase 3: Memory System (Priority: HIGH)
**Estimated: 12 files | Target: Week 2-3**

| File | Priority | Reason |
|------|----------|--------|
| `memory/unified.py` | HIGH | Main memory interface |
| `memory/graph.py` | HIGH | Graph data structure |
| `memory/nodes.py` | HIGH | Node types |
| `memory/edges.py` | HIGH | Edge relationships |
| `memory/long_term.py` | MEDIUM | Persistence |
| `memory/short_term.py` | MEDIUM | Session memory |
| `memory/cross_session.py` | MEDIUM | Cross-session |
| `memory/claude_memory.py` | MEDIUM | Claude integration |
| `memory/control_panel.py` | LOW | Admin UI |
| `memory/security/__init__.py` | HIGH | Security checks |
| `memory/storage/__init__.py` | MEDIUM | Storage backends |

---

## Phase 4: CLI & User Interface (Priority: MEDIUM)
**Estimated: 15 files | Target: Week 3**

### 4.1 Main CLI (8 files)
| File | Priority | Reason |
|------|----------|--------|
| `cli/core.py` | HIGH | CLI framework |
| `cli/commands/memory.py` | MEDIUM | Memory commands |
| `cli/commands/provider.py` | MEDIUM | Provider commands |
| `cli/commands/inspection.py` | LOW | Debug commands |
| `cli/commands/utilities.py` | LOW | Utility commands |

### 4.2 Telemetry CLI (3 files)
| File | Priority | Reason |
|------|----------|--------|
| `telemetry/cli.py` | MEDIUM | Telemetry commands |
| `telemetry/usage_tracker.py` | MEDIUM | Usage tracking |

### 4.3 Dashboard (2 files)
| File | Priority | Reason |
|------|----------|--------|
| `dashboard/server.py` | LOW | Web dashboard |

---

## Phase 5: Socratic Engine (Priority: MEDIUM)
**Estimated: 19 files | Target: Week 3-4**

| File | Priority | Reason |
|------|----------|--------|
| `socratic/engine.py` | HIGH | Main engine |
| `socratic/blueprint.py` | HIGH | Blueprint system |
| `socratic/collaboration.py` | MEDIUM | Multi-agent |
| `socratic/embeddings.py` | MEDIUM | Vector embeddings |
| `socratic/explainer.py` | MEDIUM | Explanations |
| `socratic/feedback.py` | MEDIUM | Feedback loop |
| `socratic/persistence.py` | MEDIUM | Data persistence |
| `socratic/ab_testing.py` | LOW | A/B testing |
| `socratic/domain_templates.py` | LOW | Templates |

---

## Phase 6: Infrastructure (Priority: MEDIUM)
**Estimated: 30 files | Target: Week 4**

### 6.1 Caching (5 files)
| File | Priority | Reason |
|------|----------|--------|
| `cache/storage.py` | MEDIUM | Cache storage |
| `cache/hybrid.py` | MEDIUM | Hybrid caching |
| `cache/hash_only.py` | LOW | Hash-based cache |
| `cache/dependency_manager.py` | LOW | Dependencies |

### 6.2 Resilience (4 files)
| File | Priority | Reason |
|------|----------|--------|
| `resilience/circuit_breaker.py` | HIGH | Circuit breaker |
| `resilience/retry.py` | HIGH | Retry logic |
| `resilience/health.py` | MEDIUM | Health checks |

### 6.3 Monitoring (5 files)
| File | Priority | Reason |
|------|----------|--------|
| `monitoring/alerts.py` | MEDIUM | Alert system |
| `monitoring/multi_backend.py` | MEDIUM | Multi-backend |
| `monitoring/otel_backend.py` | LOW | OpenTelemetry |

### 6.4 Routing (4 files)
| File | Priority | Reason |
|------|----------|--------|
| `routing/classifier.py` | HIGH | Task classification |
| `routing/chain_executor.py` | MEDIUM | Chain execution |
| `routing/wizard_registry.py` | LOW | Wizard routing |

---

## Phase 7: Orchestration & Meta (Priority: MEDIUM)
**Estimated: 19 files | Target: Week 4-5**

### 7.1 Orchestration (7 files)
| File | Priority | Reason |
|------|----------|--------|
| `orchestration/meta_orchestrator.py` | HIGH | Main orchestrator |
| `orchestration/execution_strategies.py` | HIGH | Execution |
| `orchestration/agent_templates.py` | MEDIUM | Templates |
| `orchestration/config_store.py` | MEDIUM | Config storage |
| `orchestration/pattern_learner.py` | LOW | Learning |
| `orchestration/real_tools.py` | LOW | Tool integration |

### 7.2 Meta Workflows (12 files)
| File | Priority | Reason |
|------|----------|--------|
| `meta_workflows/agent_creator.py` | HIGH | Agent creation |
| `meta_workflows/intent_detector.py` | HIGH | Intent detection |
| `meta_workflows/plan_generator.py` | MEDIUM | Plan generation |
| `meta_workflows/pattern_learner.py` | MEDIUM | Pattern learning |
| `meta_workflows/form_engine.py` | LOW | Form handling |
| `meta_workflows/session_context.py` | LOW | Session context |

---

## Phase 8: Remaining Modules (Priority: LOW)
**Estimated: 47 files | Target: Week 5-6**

### 8.1 Project Index (5 files)
- `project_index/scanner.py` - File scanning
- `project_index/index.py` - Index management
- `project_index/models.py` - Data models
- `project_index/reports.py` - Report generation
- `project_index/cli.py` - CLI commands

### 8.2 Test Generator (5 files)
- `test_generator/generator.py` - Test generation
- `test_generator/risk_analyzer.py` - Risk analysis
- `test_generator/cli.py` - CLI interface

### 8.3 Scaffolding (5 files)
- `scaffolding/cli.py` - Scaffolding CLI
- `scaffolding/methodologies/*.py` - TDD, patterns

### 8.4 Validation (2 files)
- `validation/xml_validator.py` - XML validation

### 8.5 Hot Reload (5 files)
- `hot_reload/reloader.py` - Hot reloading
- `hot_reload/watcher.py` - File watching
- `hot_reload/websocket.py` - WebSocket

### 8.6 Workflow Patterns (4 files)
- `workflow_patterns/structural.py`
- `workflow_patterns/behavior.py`
- `workflow_patterns/output.py`

### 8.7 Other (20 files)
- Various utility files, __init__.py files, adapters

---

## Testing Strategy

### Test Types by Priority

1. **Unit Tests** (All files)
   - Test individual functions/methods
   - Mock external dependencies
   - Fast execution (<1s per test)

2. **Integration Tests** (Core modules)
   - Test component interactions
   - Use real dependencies where safe
   - Moderate execution (<10s per test)

3. **Security Tests** (File I/O, user input handling)
   - Path traversal prevention
   - Input validation
   - Exception handling

### Test Template

```python
"""Tests for {module_name}.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest
from unittest.mock import Mock, patch

from attune.{module_path} import {class_or_function}


class Test{ClassName}:
    """Tests for {ClassName}."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return {ClassName}()

    def test_basic_functionality(self, instance):
        """Test basic operation."""
        result = instance.method()
        assert result is not None

    def test_error_handling(self, instance):
        """Test error cases."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)

    def test_edge_cases(self, instance):
        """Test edge cases."""
        assert instance.method(None) == expected
        assert instance.method([]) == expected
```

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 4 | Final |
|--------|---------|---------|---------|-------|
| Files with tests | 69 | 94 | 150 | 253 |
| Files without tests | 184 | 159 | 103 | 0 |
| Test coverage | ~53% | 60% | 75% | 85%+ |
| Tests passing | 127 | 180 | 350 | 500+ |

---

## Execution Plan

### Week 1: Phase 1 (Foundation)
- [ ] Models module tests (12 files)
- [ ] Config module tests (2 files)
- [ ] Core file tests (3 files)
- **Target: 17 new test files**

### Week 2: Phase 2-3 (Workflows & Memory)
- [ ] Workflow infrastructure tests
- [ ] Workflow-specific tests
- [ ] Memory system tests
- **Target: 49 new test files**

### Week 3: Phase 4-5 (CLI & Socratic)
- [ ] CLI command tests
- [ ] Telemetry tests
- [ ] Socratic engine tests
- **Target: 34 new test files**

### Week 4: Phase 6-7 (Infrastructure)
- [ ] Caching tests
- [ ] Resilience tests
- [ ] Monitoring tests
- [ ] Orchestration tests
- **Target: 49 new test files**

### Week 5-6: Phase 8 (Remaining)
- [ ] Project index tests
- [ ] Test generator tests
- [ ] All remaining modules
- **Target: 35 new test files**

---

## Notes

1. **Prioritize by risk**: Security-sensitive files first
2. **Test incrementally**: Run tests after each file
3. **Update coverage**: Track progress with file-test-dashboard
4. **Review patterns**: Use existing test files as templates
5. **Mock expensive operations**: LLM calls, file I/O where appropriate
