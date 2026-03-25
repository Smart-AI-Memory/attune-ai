#!/bin/bash -eu

pip3 install atheris
pip3 install -e $SRC/attune-ai

# Compile fuzz targets using the standard OSS-Fuzz helper
for fuzzer in $SRC/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer"
done
