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

### Build the documentation

The core package and normal website documentation support Python 3.10 or later.
From the repository root, install the documentation tools and build the website:

```bash
python -m pip install -e '.[docs]'
python scripts/build_docs.py website
```

PDF export requires Python 3.11 or later because the patched Pillow dependency no longer
supports Python 3.10. Use a fresh Python 3.11 or later virtual environment, install `.[docs]`,
and run:

```bash
python scripts/build_docs.py ebook
```

The `docs` and `all` extras omit the PDF toolchain on Python 3.10. The `ebook`
target refuses Python 3.10 before creating output or starting a build. Install
the native libraries required by [WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
for your operating system before exporting a PDF. Use a fresh virtual environment
when changing Python versions: upgrading an existing environment does not remove
previously installed PDF dependencies. If a Python 3.10 environment previously
installed `.[docs]` or `.[all]`, create a fresh environment instead of upgrading in place;
older PDF dependencies can otherwise remain installed.

On Python 3.10, the default `all` target builds the PyPI and website outputs, then
reports that PDF export is unavailable and exits with status 1. Use the `website`
target to build normal documentation on Python 3.10.

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

Open an issue or ask in [Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)!
