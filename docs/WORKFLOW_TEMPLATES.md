---
description: Workflow Templates Reference: **Version:** 4.2.0 **Last Updated:** 2026-01-17 **Total Templates:** 5 production-ready workflows --- ## Overview Empathy Framewor
---

# Workflow Templates Reference

**Version:** 4.2.0
**Last Updated:** 2026-01-17
**Total Templates:** 5 production-ready workflows

---

## Overview

Attune AI v4.2.0 includes 5 comprehensive, production-ready workflow templates designed for enterprise-level software development tasks. Each template creates a specialized agent team through interactive forms and progressive tier escalation.

---

## Template Catalog

### 1. Python Package Publishing Workflow

**ID:** `python_package_publish`
**File:** `.empathy/meta_workflows/templates/python_package_publish.json`

**Purpose:** End-to-end workflow for publishing Python packages to PyPI with comprehensive quality checks.

**Configuration:**
- **Questions:** 8
- **Agents:** 8
- **Cost Range:** $0.05-$0.30
- **Duration:** ~8 minutes

**Questions:**
1. Has tests? (boolean)
2. Test coverage required (60%, 70%, 80%, 90%, 95%+)
3. Quality checks (Linting, Type checking, Security scan, Docs check)
4. Version bump (patch, minor, major)
5. Publish to PyPI? (boolean)
6. PyPI environment (TestPyPI, Production PyPI)
7. Run build verification? (boolean)
8. Notification preferences (Email, Slack, None)

**Agent Team:**
- `test_runner` - Executes test suite
- `coverage_checker` - Validates coverage thresholds
- `quality_validator` - Runs linters and type checkers
- `version_bumper` - Updates version numbers
- `changelog_updater` - Updates CHANGELOG.md
- `build_creator` - Creates distribution packages
- `pypi_publisher` - Publishes to PyPI
- `notification_sender` - Sends completion notifications

**Use Cases:**
- Publishing Python libraries to PyPI
- Automated release workflows
- CI/CD integration for package releases
- Quality-gated publishing

---

### 2. Code Refactoring Workflow

**ID:** `code_refactoring_workflow`
**File:** `.empathy/meta_workflows/templates/code_refactoring_workflow.json`

**Purpose:** Safe code refactoring with validation, testing, and human review before applying changes.

**Configuration:**
- **Questions:** 8
- **Agents:** 8
- **Cost Range:** $0.15-$2.50
- **Duration:** ~5 minutes

**Questions:**
1. Refactoring scope (Single function, Single class, Multiple classes, Entire module/package)
2. Refactoring type (Extract method, Rename variables, Simplify logic, Remove duplication, Optimize performance, Update dependencies, Modernize syntax)
3. Preserve existing tests? (boolean)
4. Test coverage required (60%, 70%, 80%, 90%, 95%+)
5. Style guide (PEP 8, Google, Custom, None)
6. Safety level (Conservative, Moderate, Aggressive)
7. Create backup? (boolean)
8. Require human review? (boolean)

**Agent Team:**
- `code_analyzer` - Analyzes code structure and identifies refactoring opportunities
- `test_runner_before` - Runs tests before refactoring
- `refactoring_planner` - Creates refactoring plan with steps
- `code_refactorer` - Applies refactoring changes
- `style_enforcer` - Applies style guide rules
- `test_runner_after` - Validates tests pass after changes
- `diff_reviewer` - Reviews changes and highlights risks
- `validation_reporter` - Creates validation report

**Use Cases:**
- Legacy code modernization
- Performance optimization
- Code quality improvement
- Technical debt reduction
- Dependency updates

**Safety Features:**
- Conservative/Moderate/Aggressive refactoring levels
- Automatic backup creation
- Test preservation validation
- Human review checkpoints
- Rollback capability

---

### 3. Security Audit Workflow

**ID:** `security_audit_workflow`
**File:** `.empathy/meta_workflows/templates/security_audit_workflow.json`

**Purpose:** Comprehensive security audit with vulnerability scanning, dependency checking, and compliance validation.

**Configuration:**
- **Questions:** 9
- **Agents:** 8
- **Cost Range:** $0.25-$3.00
- **Duration:** ~5 minutes

**Questions:**
1. Audit scope (Single module, Entire codebase, Dependencies only, Infrastructure configs)
2. Compliance frameworks (OWASP Top 10, CWE Top 25, PCI DSS, HIPAA, SOC 2, None)
3. Severity threshold (Critical only, High+, Medium+, All)
4. Check dependencies? (boolean)
5. Scan types (Static analysis, Secret detection, Dependency scan, Config audit, Container scan)
6. Audit infrastructure configs? (boolean)
7. Report formats (Markdown, JSON, HTML, SARIF, PDF)
8. Auto-create GitHub issues? (boolean)

**Agent Team:**
- `vulnerability_scanner` - Scans for security vulnerabilities (Bandit, Semgrep)
- `dependency_checker` - Checks for vulnerable dependencies (Safety, Snyk)
- `secret_detector` - Detects exposed secrets (detect-secrets, truffleHog)
- `owasp_validator` - Validates against OWASP Top 10
- `config_auditor` - Audits infrastructure and app configs
- `compliance_validator` - Checks compliance framework requirements
- `report_generator` - Generates comprehensive security reports
- `issue_creator` - Creates GitHub issues for findings

**Use Cases:**
- Pre-deployment security audits
- Compliance validation (OWASP, CWE, PCI DSS, HIPAA)
- Vulnerability assessments
- Security regression testing
- Third-party dependency audits

**Security Standards:**
- OWASP Top 10 (2021)
- CWE Top 25
- PCI DSS requirements
- HIPAA security rules
- SOC 2 compliance

---

### 4. Documentation Generation Workflow

**ID:** `documentation_generation_workflow`
**File:** `.empathy/meta_workflows/templates/documentation_generation_workflow.json`

**Purpose:** Automated documentation generation from code with examples, API references, and user guides.

**Configuration:**
- **Questions:** 10
- **Agents:** 9
- **Cost Range:** $0.20-$2.80
- **Duration:** ~5 minutes

**Questions:**
1. Documentation types (API docs, User guides, Tutorials, Architecture docs, Code comments, README)
2. Target audience (Developers, End users, DevOps/SRE, Architects, Contributors)
3. Include code examples? (boolean)
4. Documentation format (Markdown, reStructuredText, HTML, PDF, Confluence)
5. Style guide (Google, Microsoft, Custom, None)
6. Generate diagrams? (boolean)
7. Diagram types (Architecture, Sequence, Class, ER, Deployment)
8. Update README? (boolean)
9. Validate links? (boolean)

**Agent Team:**
- `code_analyzer` - Analyzes code structure and APIs
- `api_doc_generator` - Generates API reference documentation
- `example_generator` - Creates code examples and tutorials
- `user_guide_writer` - Writes user-facing documentation
- `diagram_generator` - Creates architecture and design diagrams
- `readme_updater` - Updates README.md with latest info
- `link_validator` - Validates all documentation links
- `documentation_formatter` - Applies consistent formatting
- `quality_reviewer` - Reviews documentation quality

**Use Cases:**
- API documentation generation
- User guide creation
- Architecture documentation
- Tutorial and example creation
- README maintenance
- Developer onboarding docs

**Documentation Types:**
- **API Docs:** Auto-generated from docstrings/comments
- **User Guides:** Step-by-step usage instructions
- **Tutorials:** Hands-on learning materials
- **Architecture:** System design and component diagrams
- **Code Comments:** Inline code documentation
- **README:** Project overview and quick start

**Diagram Generation:**
- Architecture diagrams (system components)
- Sequence diagrams (interaction flows)
- Class diagrams (OOP structure)
- ER diagrams (database schema)
- Deployment diagrams (infrastructure)

---

### 5. Test Creation and Management Workflow

**ID:** `test_creation_management_workflow`
**File:** `.empathy/meta_workflows/templates/test_creation_management_workflow.json`

**Purpose:** Enterprise-level test creation, inspection, updating, and management with comprehensive coverage.

**Configuration:**
- **Questions:** 12
- **Agents:** 11
- **Cost Range:** $0.30-$3.50
- **Duration:** ~5 minutes

**Questions:**
1. Testing scope (Single function/class, Single module/package, Multiple modules, Entire project)
2. Test types (Unit tests, Integration tests, E2E tests, Performance tests, Security tests, Contract tests, Regression tests)
3. Testing framework (pytest, unittest, Jest, JUnit, RSpec, Auto-detect)
4. Coverage target (60%, 70%, 80%, 90%, 95%+)
5. Quality checks (Assertion depth, Edge cases, Error handling, Mock quality, Test isolation, Performance, Flaky detection)
6. Inspection mode (Analyze existing only, Create new only, Both)
7. Update outdated tests? (boolean)
8. Test data strategy (Minimal fixtures, Realistic fixtures, Property-based, Snapshot, Mixed)
9. Enable parallel execution? (boolean)
10. Report types (Coverage HTML, JUnit XML, Performance metrics, Flaky tests, Missing coverage)
11. Generate CI/CD config? (boolean)
12. Generate test documentation? (boolean)

**Agent Team:**
- `test_analyzer` - Analyzes existing tests and identifies gaps
- `unit_test_generator` - Creates unit tests for functions and classes
- `integration_test_creator` - Creates integration tests for module interactions
- `e2e_test_designer` - Designs end-to-end workflow tests
- `test_quality_validator` - Validates test quality (assertion depth, edge cases)
- `test_updater` - Updates broken or outdated tests
- `fixture_manager` - Creates and manages test fixtures and factories
- `performance_test_creator` - Creates performance and load tests
- `test_report_generator` - Generates comprehensive test reports
- `ci_integration_specialist` - Creates CI/CD configuration for automated testing
- `test_documentation_writer` - Writes test plans and documentation

**Use Cases:**
- Comprehensive test suite creation
- Test quality improvement
- Legacy code test coverage
- CI/CD pipeline integration
- Test maintenance and updates
- Enterprise testing standards

**Testing Capabilities:**

**Multi-Level Testing:**
- **Unit Tests:** Function and class-level tests with high coverage
- **Integration Tests:** Module interaction and API contract tests
- **E2E Tests:** Full workflow and user journey tests
- **Performance Tests:** Load testing, stress testing, benchmarking
- **Security Tests:** Penetration testing, fuzzing, input validation
- **Contract Tests:** API contract validation
- **Regression Tests:** Bug prevention and backward compatibility

**Framework Support:**
- **Python:** pytest, unittest, Hypothesis (property-based)
- **JavaScript:** Jest, Mocha, Cypress
- **Java:** JUnit, TestNG
- **Ruby:** RSpec, Minitest

**Test Quality Validation:**
- **Assertion Depth:** Ensures tests have meaningful assertions (min 2+)
- **Edge Case Coverage:** Validates boundary conditions tested
- **Error Handling:** Ensures exception paths covered
- **Mock Quality:** Validates proper mocking and isolation
- **Test Isolation:** Verifies tests don't depend on each other
- **Performance:** Identifies slow tests (>1s)
- **Flaky Detection:** Identifies non-deterministic tests

**Test Data Strategies:**
- **Minimal Fixtures:** Simple, hardcoded test data
- **Realistic Fixtures:** Production-like data with Faker
- **Property-Based:** Hypothesis/QuickCheck for edge cases
- **Snapshot Testing:** Freeze outputs for regression detection
- **Mixed Strategy:** Combination of approaches

**CI/CD Integration:**
- **GitHub Actions** configuration generation
- **Parallel execution** for faster builds
- **Coverage upload** to Codecov/Coveralls
- **Slack notifications** for test results
- **PR comment integration** for coverage reports

**Test Reporting:**
- **Coverage Report:** HTML + terminal display
- **JUnit XML:** CI/CD integration format
- **Performance Metrics:** Test execution duration
- **Flaky Test Report:** Non-deterministic test detection
- **Missing Coverage:** Uncovered lines and functions

**Enterprise Features:**
- Mutation testing with `mutmut` for test effectiveness
- Test containerization with Docker/testcontainers
- E2E testing with Playwright/Selenium/Cypress
- API testing with REST-assured/Postman
- Database testing with fixtures and migrations
- Test data factories with factory_boy/Faker

---

## Comparison Matrix

| Template | Questions | Agents | Cost Range | Best For |
|----------|-----------|--------|------------|----------|
| Python Package Publishing | 8 | 8 | $0.05-$0.30 | PyPI releases, CI/CD |
| Code Refactoring | 8 | 8 | $0.15-$2.50 | Legacy modernization, tech debt |
| Security Audit | 9 | 8 | $0.25-$3.00 | Compliance, vulnerability scanning |
| Documentation Generation | 10 | 9 | $0.20-$2.80 | API docs, user guides |
| Test Creation & Management | 12 | 11 | $0.30-$3.50 | Comprehensive testing, CI/CD |

---

## Usage Examples

### Running a Workflow

```bash
# List available templates
attune meta-workflow list-templates

# Inspect a template
attune meta-workflow inspect test_creation_management_workflow

# Run a workflow (interactive)
attune meta-workflow run test_creation_management_workflow
```

### Programmatic Usage

```python
from attune.meta_workflows import TemplateRegistry, MetaWorkflow, FormResponse

# Load template
registry = TemplateRegistry()
template = registry.load_template("test_creation_management_workflow")

# Create workflow
workflow = MetaWorkflow(template=template)

# Execute with pre-filled responses
response = FormResponse(
    template_id="test_creation_management_workflow",
    responses={
        "test_scope": "Entire project (full suite)",
        "test_types": ["Unit tests (functions, classes)", "Integration tests (module interactions)"],
        "testing_framework": "pytest (Python)",
        "coverage_target": "80% (good coverage)",
        "test_quality_checks": ["Assertion depth (avoid shallow tests)", "Edge case coverage (boundary conditions)"],
        "test_inspection_mode": "Both (analyze + create new)",
        "update_outdated_tests": True,
        "test_data_strategy": "Realistic fixtures (production-like data)",
        "parallel_execution": True,
        "generate_test_reports": ["Coverage report (HTML + terminal)", "JUnit XML"],
        "ci_integration": True,
        "test_documentation": True,
    },
)

result = workflow.execute(form_response=response)
print(f"Created {len(result.agents_created)} agents")
print(f"Total cost: ${result.total_cost:.2f}")
```

---

## Template Development Guide

### Creating Custom Templates

Templates are JSON files with the following structure:

```json
{
  "template_id": "your_workflow_id",
  "name": "Your Workflow Name",
  "description": "Brief description",
  "version": "1.0.0",
  "author": "Your Name",
  "created_at": "2026-01-17T10:00:00Z",
  "estimated_cost_range": [0.10, 1.50],
  "form_schema": {
    "title": "Configuration Title",
    "description": "Configuration description",
    "questions": [...]
  },
  "agent_composition_rules": [...]
}
```

### Validation

```bash
# Validate your template
attune meta-workflow validate-template my_template.json
```

### Best Practices

1. **Question Design:**
   - Keep questions focused and actionable
   - Provide clear help text
   - Use appropriate question types (single_select, multi_select, boolean, text_input)
   - Set sensible defaults

2. **Agent Design:**
   - Create specialized agents with clear responsibilities
   - Use appropriate tier strategies (cheap_only, progressive, capable_first)
   - Define clear success criteria
   - Specify required tools

3. **Cost Optimization:**
   - Use `cheap_only` for simple tasks (formatting, file operations)
   - Use `progressive` for tasks that may need escalation
   - Use `capable_first` for complex reasoning tasks

4. **Testing:**
   - Test with mock execution first
   - Validate all question combinations
   - Verify agent creation logic
   - Test success criteria

---

## Migration from Existing Workflows

### Converting a Manual Workflow

1. **Identify workflow steps** - Break down your process into discrete steps
2. **Design questions** - Determine what configuration is needed
3. **Map to agents** - Create agent specs for each step
4. **Define tier strategy** - Choose appropriate escalation strategy
5. **Test thoroughly** - Validate with mock execution

### Example Migration

**Before (Manual):**
```bash
pytest --cov=src --cov-report=html
ruff check src/
mypy src/
python -m build
twine upload dist/*
```

**After (Template):**
Use `python_package_publish` template with automated quality checks, version bumping, and publishing.

---

## FAQ

**Q: Can I customize existing templates?**
A: Yes! Export a template with `attune meta-workflow export-template <id>`, modify the JSON, and load it as a custom template.

**Q: How do I add my own template?**
A: Create a JSON file in `.empathy/meta_workflows/templates/` following the template schema, then validate with `attune meta-workflow validate-template`.

**Q: What happens if an agent fails?**
A: The workflow continues with other agents. Failed agents are reported in the execution summary.

**Q: Can I run templates without interactive prompts?**
A: Yes! Provide a `FormResponse` object programmatically with pre-filled answers.

**Q: How does tier escalation work?**
A: Each agent has a tier strategy (cheap_only, progressive, capable_first) that determines when to use more expensive models based on quality metrics.

---

## Support

- **Documentation:** [docs/META_WORKFLOWS.md](META_WORKFLOWS.md)
- **GitHub Issues:** [Report bugs or request features](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Discussions:** [Ask questions](https://github.com/Smart-AI-Memory/attune-ai/discussions)

---

**Version:** 4.2.0
**Last Updated:** 2026-01-17
**Maintained By:** Attune AI Team
