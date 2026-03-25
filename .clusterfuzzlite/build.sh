#!/bin/bash -eu

pip3 install atheris

# Copy fuzz targets to $OUT
for fuzzer in $SRC/fuzz_*.py; do
  target=$(basename "$fuzzer" .py)
  cp "$fuzzer" "$OUT/$target"
  chmod +x "$OUT/$target"
done
