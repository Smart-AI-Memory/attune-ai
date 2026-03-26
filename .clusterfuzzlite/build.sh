#!/bin/bash -eu

pip3 install atheris
pip3 install $SRC/attune-ai

# Compile fuzz targets using the standard OSS-Fuzz helper.
# PyInstaller can't auto-detect attune imports, so pass
# --hidden-import for the modules used by fuzz targets.
compile_python_fuzzer "$SRC/fuzz_config_parsing.py"
compile_python_fuzzer "$SRC/fuzz_path_validation.py" \
  --hidden-import=attune \
  --hidden-import=attune.security \
  --hidden-import=attune.security.path_validation
