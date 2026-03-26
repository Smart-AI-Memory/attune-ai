#!/usr/bin/python3
"""Fuzz target for configuration parsing."""
import sys

import atheris


def test_one_input(data: bytes) -> None:
    """Fuzz YAML/JSON config parsing with arbitrary input."""
    fdp = atheris.FuzzedDataProvider(data)
    raw = fdp.ConsumeUnicodeNoSurrogates(4096)

    if not raw:
        return

    # Fuzz JSON parsing
    import json

    try:
        json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fuzz YAML parsing
    try:
        import yaml

        yaml.safe_load(raw)
    except (yaml.YAMLError, ValueError, TypeError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
