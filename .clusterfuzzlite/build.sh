#!/bin/bash -eu

# Hash-pinned fuzz deps via requirements.txt + --require-hashes.
# The bare `pip install --hash=...` form fails on the clusterfuzz
# container's pip ("no such option: --hash"); the requirements-file
# form is universally supported and is what Scorecard's
# PinnedDependenciesID check recognizes.
pip3 install --require-hashes -r "$(dirname "$0")/requirements.txt"
pip3 install --no-deps "$SRC/attune-ai"

# Compile fuzz targets using the standard OSS-Fuzz helper.
# PyInstaller can't auto-detect attune imports, so pass
# --hidden-import for the modules used by fuzz targets.
compile_python_fuzzer "$SRC/fuzz_config_parsing.py"
compile_python_fuzzer "$SRC/fuzz_path_validation.py" \
  --hidden-import=attune \
  --hidden-import=attune.security \
  --hidden-import=attune.security.path_validation
