#!/usr/bin/python3
"""Fuzz target for path validation security boundary."""
import sys

import atheris

from attune.security.path_validation import _validate_file_path


def test_one_input(data: bytes) -> None:
    """Fuzz _validate_file_path with arbitrary input."""
    fdp = atheris.FuzzedDataProvider(data)
    path_str = fdp.ConsumeUnicodeNoSurrogates(512)

    if not path_str:
        return

    try:
        _validate_file_path(path_str)
    except (ValueError, TypeError, OSError):
        # Expected rejections from the validator
        pass


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
