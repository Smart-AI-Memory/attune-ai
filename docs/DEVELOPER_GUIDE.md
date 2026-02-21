---
description: Developer Guide - Attune AI: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Developer Guide - Attune AI

**Version:** 4.0.0
**Last Updated:** January 16, 2026
**Audience:** Contributors, Plugin Developers, Framework Maintainers

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Building Custom Plugins](#building-custom-plugins)
7. [Contributing Workflow](#contributing-workflow)
8. [Release Process](#release-process)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- **Python 3.10+** (Framework supports 3.10-3.13)
- **Git** for version control
- **pip** for package management
- **Redis** (optional, for memory features)
- At least one LLM API key (Anthropic, OpenAI, or Google)

### Quick Development Setup

```bash
# Clone the repository
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e .[dev,test,full]

# Verify installation
pytest tests/unit --maxfail=1

# Set up environment variables
cp .env.example .env  # Edit with your API keys
```

---

## Development Environment Setup

### Recommended Tools

- **IDE**: VSCode with Python extension (or PyCharm)
- **Linters**: Black (formatting), Ruff (linting), MyPy (type checking)
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Pre-commit**: Automated code quality checks

### Installing Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**Configured hooks** (from [`.pre-commit-config.yaml`](../.pre-commit-config.yaml)):
- Black - Code formatter (100-char line length)
- Ruff - Fast Python linter
- Bandit - Security vulnerability scanner
- detect-secrets - Credential leak prevention
- MyPy - Static type checker (when re-enabled)

---

## Project Structure

```
attune-ai/
├── src/attune/              # Core framework
│   ├── workflows/               # Built-in workflows
│   ├── orchestration/           # Meta-orchestration system (v4.0)
│   ├── models/                  # Multi-provider LLM interface
│   ├── memory/                  # Memory graph and persistence
│   ├── telemetry/               # Usage tracking and analytics
│   ├── cache/                   # Response caching
│   └── config/                  # Configuration management
│
├── attune_llm/         # Legacy wizard system
│   └── wizards/                 # Base wizard classes + examples
│
├── empathy_software_plugin/     # Software development wizards
│   └── wizards/                 # 20+ specialized software wizards
│
├── tests/                       # Test suite (6,000+ tests)
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── validation/              # End-to-end validation
│
├── docs/                        # Documentation
│   ├── architecture/            # System design docs
│   ├── api-reference/           # API documentation
│   ├── guides/                  # User guides
│   └── blog/                    # Blog posts and articles
│
├── examples/                    # Usage examples
│   ├── orchestration/           # Meta-orchestration examples (v4.0)
│   ├── ai_wizards/              # Software development examples
│   └── domain_wizards/          # Domain-specific examples
│
├── website/                     # Next.js marketing site
├── benchmarks/                  # Performance benchmarks
└── .claude/                     # Claude Code project instructions
    └── rules/attune/           # Coding standards and patterns
```

### Key Directories Explained

- **`src/attune/`**: Core framework logic - most development happens here
- **`empathy_software_plugin/`**: Software development wizards (advanced debugging, testing, security)
- **`tests/`**: Comprehensive test suite with 68% coverage (target: 80%+)
- **`.claude/`**: Project-specific coding standards and patterns for AI assistants
- **`docs/architecture/`**: System design, integration plans, and technical specs

---

## Coding Standards

**Full Reference:** [`.claude/rules/attune/coding-standards-index.md`](../.claude/rules/attune/coding-standards-index.md)

### Critical Rules (MUST FOLLOW)

#### 1. Security

**NEVER use `eval()` or `exec()`** - Code injection vulnerability (CWE-95)

```python
# ❌ PROHIBITED
result = eval(user_input)

# ✅ REQUIRED
import ast
result = ast.literal_eval(user_input)  # Safe for literals only
```

**ALWAYS validate file paths** - Prevents path traversal (CWE-22)

```python
from attune.security.path_validation import _validate_file_path

# ✅ REQUIRED
validated_path = _validate_file_path(user_provided_path)
with validated_path.open('w') as f:
    f.write(data)
```

#### 2. Exception Handling

**NEVER use bare `except:`** - Catches KeyboardInterrupt, SystemExit

```python
# ❌ PROHIBITED
try:
    risky_operation()
except:  # Masks all errors!
    pass

# ✅ REQUIRED
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except FileNotFoundError as e:
    logger.warning(f"File not found: {e}")
    return default_value
```

**Acceptable broad catches** (with justification):

```python
# ✅ ALLOWED - Version detection with fallback
try:
    from importlib.metadata import version
    return version("attune-ai")
except Exception:  # noqa: BLE001
    # INTENTIONAL: Fallback for dev installs without metadata
    return "dev"
```

#### 3. Code Quality

- **Type hints required** on all public functions
- **Google-style docstrings** with Args, Returns, Raises
- **Line length**: 100 characters (enforced by Black)
- **Test coverage**: Minimum 80% (current: 68%, improving)

```python
def process_data(
    input_path: str,
    output_format: str = "json",
) -> dict[str, Any]:
    """Process data from file and return structured output.

    Args:
        input_path: Path to input file (user-controlled, will be validated)
        output_format: Desired output format ("json" or "yaml")

    Returns:
        Dictionary containing processed data with keys:
        - "status": Processing status
        - "data": Transformed data
        - "metadata": Processing metadata

    Raises:
        ValueError: If input_path is invalid or output_format unsupported
        FileNotFoundError: If input file doesn't exist
        PermissionError: If insufficient permissions

    Example:
        >>> result = process_data("data.csv", output_format="json")
        >>> print(result["status"])
        'success'
    """
    validated_path = _validate_file_path(input_path)
    # Implementation...
```

---

## Testing Guidelines

### Test Organization

- **Unit tests**: `tests/unit/` - Test individual functions/classes
- **Integration tests**: `tests/integration/` - Test component interactions
- **Validation tests**: `tests/validation/` - End-to-end workflows

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run tests matching pattern
pytest -k "test_security"

# Stop on first failure (fast feedback)
pytest -x

# Verbose output
pytest -v

# Run tests in parallel (faster)
pytest -n auto
```

### Writing Tests

**Required test coverage for new features:**
- Security-sensitive code: 100% coverage + security tests
- File operations: Path traversal tests, null byte injection tests
- Public APIs: Happy path + error cases + edge cases

**Test naming convention:**

```python
def test_{function_name}_{scenario}_{expected_outcome}():
    """Test description."""
    # Given
    config = EmpathyConfig(user_id="test")

    # When
    result = config.to_yaml(valid_path)

    # Then
    assert result.exists()
```

**Security test template:**

```python
import pytest
from pathlib import Path

def test_blocks_path_traversal():
    """Test that save blocks path traversal attacks."""
    config = EmpathyConfig(user_id="test")

    dangerous_paths = [
        "/etc/passwd",
        "../../etc/passwd",
        "../../../etc/passwd",
    ]

    for path in dangerous_paths:
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            config.to_yaml(path)

def test_blocks_null_byte_injection():
    """Test that save blocks null byte injection."""
    config = EmpathyConfig(user_id="test")

    with pytest.raises(ValueError, match="contains null bytes"):
        config.to_yaml("config\x00.json")

def test_allows_valid_paths(tmp_path):
    """Test that save allows valid paths."""
    config = EmpathyConfig(user_id="test")
    output_file = tmp_path / "config.yaml"

    result = config.to_yaml(str(output_file))

    assert output_file.exists()
    assert result == output_file
```

---

## Building Custom Plugins

### Creating a Custom Wizard

```python
from attune_llm.wizards import BaseWizard, WizardConfig
from attune_llm import EmpathyLLM

class MyCustomWizard(BaseWizard):
    """Custom wizard for specific domain."""

    def __init__(self, llm: EmpathyLLM | None = None):
        config = WizardConfig(
            name="my-custom-wizard",
            description="Specialized wizard for my use case",
            classification="INTERNAL",  # or SENSITIVE, PUBLIC
            audit_enabled=True,
        )
        super().__init__(config=config, llm=llm)

    async def analyze(self, context: dict) -> dict:
        """Analyze context and provide recommendations.

        Args:
            context: Dictionary with:
                - "input": User input data
                - "metadata": Optional metadata

        Returns:
            Dictionary with analysis results
        """
        prompt = self._build_prompt(context)
        response = await self.llm.interact(
            user_id=self.config.name,
            user_input=prompt,
            task_type="analyze",
        )

        return {
            "analysis": response.get("content"),
            "metadata": {"wizard": self.config.name},
        }

    def _build_prompt(self, context: dict) -> str:
        """Build prompt from context."""
        return f"Analyze this: {context.get('input')}"
```

### Creating a Custom Workflow

```python
from attune.workflows.base import BaseWorkflow, WorkflowConfig
from dataclasses import dataclass

@dataclass
class MyWorkflowResult:
    """Result from my custom workflow."""
    status: str
    findings: list[dict]
    recommendations: list[str]

class MyCustomWorkflow(BaseWorkflow):
    """Custom workflow for specific task."""

    def __init__(self, **kwargs):
        config = WorkflowConfig(
            name="my-workflow",
            description="Custom workflow for...",
            tier="CAPABLE",  # or CHEAP, PREMIUM
        )
        super().__init__(config=config, **kwargs)

    async def execute(self, **kwargs) -> MyWorkflowResult:
        """Execute custom workflow.

        Args:
            **kwargs: Workflow-specific parameters

        Returns:
            MyWorkflowResult with findings and recommendations
        """
        # Workflow implementation
        findings = await self._analyze(**kwargs)
        recommendations = self._generate_recommendations(findings)

        return MyWorkflowResult(
            status="completed",
            findings=findings,
            recommendations=recommendations,
        )
```

---

## Contributing Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following coding standards
- Add/update tests (maintain >80% coverage)
- Add/update documentation
- Run pre-commit hooks

### 3. Test Your Changes

```bash
# Run tests
pytest --cov=src

# Run linters
black .
ruff check . --fix

# Run security checks
bandit -r src/ --severity-level medium
```

### 4. Commit Changes

**Commit message format:**

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding/updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `ci:` CI/CD changes
- `chore:` Maintenance tasks

**Examples:**

```bash
# Feature
git commit -m "feat: Add meta-orchestration system for dynamic agent composition"

# Bug fix
git commit -m "fix: Resolve path traversal vulnerability in config export"

# Documentation
git commit -m "docs: Add developer guide and architecture overview"
```

### 5. Create Pull Request

**PR Template:**

```markdown
## Description
[Brief description of changes]

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows project coding standards
- [ ] Self-reviewed code
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests proving fix/feature works
- [ ] New/existing tests pass locally
```

---

## Release Process

### Version Numbering

We follow **Semantic Versioning** (semver):
- **Major** (X.0.0): Breaking changes
- **Minor** (x.X.0): New features (backward compatible)
- **Patch** (x.x.X): Bug fixes (backward compatible)

### Creating a Release

1. **Update version numbers:**
   - `pyproject.toml`
   - `src/attune/__init__.py`
   - `README.md` version badge

2. **Update CHANGELOG.md:**
   ```markdown
   ## [4.0.0] - 2026-01-16

   ### Added
   - Meta-orchestration system for dynamic agent composition

   ### Changed
   - Updated tier routing algorithm for better cost optimization

   ### Deprecated
   - HealthcareWizard and TechnologyWizard (use specialized plugins)

   ### Fixed
   - Path traversal vulnerability in file export
   ```

3. **Create release commit:**
   ```bash
   git commit -am "chore: Release v4.0.0"
   git tag -a v4.0.0 -m "Release v4.0.0 - Meta-Orchestration Era"
   git push origin main --tags
   ```

4. **Publish to PyPI:**
   ```bash
   python -m build
   twine upload dist/*
   ```

---

## Troubleshooting

### Common Issues

**Import Errors**

```python
# Problem: ModuleNotFoundError: No module named 'attune'
# Solution: Install in development mode
pip install -e .[dev]
```

**Test Failures**

```bash
# Problem: Tests failing due to missing Redis
# Solution: Install and start Redis, or skip memory tests
pytest -m "not redis"
```

**Pre-commit Hook Failures**

```bash
# Problem: Black formatting failures
# Solution: Let Black auto-format
black .

# Problem: Ruff linting failures
# Solution: Auto-fix what's possible
ruff check . --fix
```

**API Key Issues**

```bash
# Problem: AuthenticationError from LLM provider
# Solution: Check environment variables
python -m attune.models.cli provider --check

# Solution: Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Additional Resources

- **[Coding Standards](../.claude/rules/attune/coding-standards-index.md)** - Complete coding standards reference
- **[Exception Handling Guide](./EXCEPTION_HANDLING_GUIDE.md)** - Pattern examples
- **[Testing Patterns](./TESTING_PATTERNS.md)** - Test examples and best practices
- **[Architecture Overview](./ARCHITECTURE.md)** - System design and components
- **[API Reference](./api-reference/)** - Complete API documentation

---

## Questions?

- **Issues**: [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)
- **Security**: security@smartaimemory.com

---

**Last Updated:** January 16, 2026
**Maintained By:** Engineering Team
**License:** Apache License 2.0
