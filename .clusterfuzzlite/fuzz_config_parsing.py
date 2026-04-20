#!/usr/bin/python3
"""Fuzz target for configuration parsing."""

import json
import sys

import atheris

# Guard imports at module load time so the try/except inside
# the fuzz loop can reference their exception classes safely.
# The clusterfuzz build installs attune-ai with --no-deps, so
# pyyaml may not be present — degrade cleanly when it isn't
# rather than crashing with UnboundLocalError when the loop's
# `except (yaml.YAMLError, ...)` tries to dereference a never-
# bound `yaml` name (a previous crash signature in CI).
try:
    import yaml

    _YAML_AVAILABLE = True
    _YAML_ERROR: type[Exception] = yaml.YAMLError
except ImportError:
    _YAML_AVAILABLE = False
    _YAML_ERROR = ValueError  # placeholder; never raised


def test_one_input(data: bytes) -> None:
    """Fuzz YAML/JSON config parsing with arbitrary input."""
    fdp = atheris.FuzzedDataProvider(data)
    raw = fdp.ConsumeUnicodeNoSurrogates(4096)

    if not raw:
        return

    # Fuzz JSON parsing
    try:
        json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fuzz YAML parsing (only if pyyaml is installed).
    if _YAML_AVAILABLE:
        try:
            yaml.safe_load(raw)
        except (_YAML_ERROR, ValueError, TypeError):
            # Invalid YAML is expected under fuzzing; ignore parse/type errors.
            pass


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
