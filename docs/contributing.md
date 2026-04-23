---
description: Development guidelines for Contributing to Attune AI. Level 3 anticipatory design principles, coding standards, and best practices for contributors.
---

# Contributing to Attune AI

Thank you for your interest in contributing to the Attune AI!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/attune-ai.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest`
6. Commit: `git commit -m "feat: your feature description"`
7. Push: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Clone repository
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run linters
black .
ruff check .
```

## Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **Google-style** docstrings

## Testing

All new features should include tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=attune

# Run specific test
pytest tests/test_core.py::test_specific_function
```

## Documentation

Update documentation for any user-facing changes:
- Add examples to `docs/examples/`
- Update API docs if needed
- Update CHANGELOG.md

## Pull Request Guidelines

- Keep PRs focused (one feature/fix per PR)
- Include tests
- Update documentation
- Follow commit message conventions:
  - `feat:` new feature
  - `fix:` bug fix
  - `docs:` documentation
  - `test:` tests
  - `refactor:` refactoring

## Questions?

Open an issue or ask in [Discussions](https://github.com/Smart-AI-Memory/empathy/discussions)!
