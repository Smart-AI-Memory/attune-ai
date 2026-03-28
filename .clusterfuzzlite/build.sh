#!/bin/bash -eu

pip3 install 'atheris==3.0.0' \
  --hash=sha256:8a5c8a781467c187da40fd29139784193e2647058831f837f675d0bb8cbd8746 \
  --hash=sha256:510e502c57b6dc615fb174066407af620d4c7f73cf08a782c86e7761bf12c4eb \
  --hash=sha256:a402cdca8a650d1371050b1f9552eb4cdc488d2db64950d603c4560318365eac
pip3 install 'structlog==25.5.0' \
  --hash=sha256:a8453e9b9e636ec59bd9e79bbd4a72f025981b3ba0f5837aebf48f02f37a7f9f
pip3 install --no-deps $SRC/attune-ai

# Compile fuzz targets using the standard OSS-Fuzz helper.
# PyInstaller can't auto-detect attune imports, so pass
# --hidden-import for the modules used by fuzz targets.
compile_python_fuzzer "$SRC/fuzz_config_parsing.py"
compile_python_fuzzer "$SRC/fuzz_path_validation.py" \
  --hidden-import=attune \
  --hidden-import=attune.security \
  --hidden-import=attune.security.path_validation
