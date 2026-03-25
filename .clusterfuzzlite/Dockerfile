FROM gcr.io/oss-fuzz-base/base-builder-python

COPY . $SRC/attune-ai
WORKDIR $SRC/attune-ai

COPY .clusterfuzzlite/build.sh $SRC/build.sh
COPY .clusterfuzzlite/fuzz_*.py $SRC/

RUN pip3 install -e .
