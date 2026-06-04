"""Phase-0 recall benchmark: int8 vs float32 vector recall.

Measures whether int8-quantized embeddings preserve retrieval
quality vs the float32 baseline, on attune-ai's own .help corpus,
using the RedisVL path that agent-memory-server uses under the
hood. This is the gating measurement for the ams-int8-quantization
spec — it does NOT modify agent-memory-server.

Run with the AMS tool venv (has redisvl + numpy + redis + yaml):

    /Users/patrickroebuck/.local/share/uv/tools/agent-memory-server/bin/python \
        docs/specs/ams-int8-quantization/phase0_benchmark.py

Requires: Redis Stack on localhost:6379, Ollama on :11434 with
nomic-embed-text. Uses isolated bench_* indexes and drops them on
exit; does not touch the memory_records / working_memory indexes.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
import yaml
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"
DIMS = 768
TOPK = 5

# Repo root derived from this file: docs/specs/ams-int8-quantization/<file>
REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / ".help" / "templates"
# External labeled query set (attune-rag); override with QUERIES_PATH.
QUERIES = Path(
    os.environ.get(
        "QUERIES_PATH",
        "/Users/patrickroebuck/attune-rag/tests/golden/queries.yaml",
    )
)

# Go/no-go gate (pre-committed in decisions.md)
P1_TOLERANCE = 0.02  # int8 P@1 within 2 pts of float32
R5_TOLERANCE = 0.03  # int8 recall@5 within 3 pts of float32

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


EMBED_CHAR_CAP = 3000  # ~750 tokens; keeps input under nomic's context window


def embed(text: str) -> list[float]:
    """Embed text via Ollama nomic-embed-text (length-capped, 1 retry)."""
    payload = (text or " ")[:EMBED_CHAR_CAP]
    body = json.dumps({"model": MODEL, "prompt": payload}).encode()
    last = None
    for _ in range(2):
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["embedding"]
        except urllib.error.HTTPError as e:  # noqa: PERF203
            last = e
    raise last


def quantize_int8(vec: list[float]) -> list[int]:
    """Per-vector max-abs scale to int8 [-127, 127].

    nomic-embed-text is not unit-normalized (components exceed 1),
    so a per-vector scale uses the full int8 range. COSINE distance
    is invariant to positive per-vector scaling, so this is safe.
    """
    a = np.asarray(vec, dtype=np.float32)
    peak = float(np.max(np.abs(a))) or 1.0
    q = np.clip(np.round(a * (127.0 / peak)), -127, 127)
    return q.astype(np.int8).tolist()


def load_corpus() -> list[dict]:
    """Load .help templates as {id, feature, text}."""
    docs = []
    for md in sorted(CORPUS_DIR.rglob("*.md")):
        rel = md.relative_to(CORPUS_DIR).as_posix()
        feature = rel.split("/", 1)[0]
        raw = md.read_text(encoding="utf-8")
        text = _FRONTMATTER.sub("", raw).strip()
        if text:
            docs.append({"id": rel, "feature": feature, "text": text})
    return docs


def load_queries() -> list[dict]:
    """Load golden queries (all of them; label use is filtered later)."""
    return yaml.safe_load(QUERIES.read_text(encoding="utf-8"))["queries"]


def build_schema(name: str, datatype: str) -> dict:
    """RedisVL schema mirroring AMS's, with a chosen vector datatype."""
    return {
        "index": {"name": name, "prefix": f"{name}:", "storage_type": "hash"},
        "fields": [
            {"name": "id_", "type": "tag"},
            {"name": "feature", "type": "tag"},
            {
                "name": "vector",
                "type": "vector",
                "attrs": {
                    "dims": DIMS,
                    "distance_metric": "cosine",
                    "algorithm": "hnsw",
                    "datatype": datatype,
                },
            },
        ],
    }


def make_index(name: str, datatype: str, docs, doc_vecs) -> SearchIndex:
    """Create and load an index with the given datatype."""
    idx = SearchIndex.from_dict(build_schema(name, datatype), redis_url=REDIS_URL)
    idx.create(overwrite=True, drop=True)
    records = []
    for d, v in zip(docs, doc_vecs, strict=True):
        if datatype == "int8":
            blob = np.array(quantize_int8(v), dtype=np.int8).tobytes()
        else:
            blob = np.array(v, dtype=np.float32).tobytes()
        records.append({"id_": d["id"], "feature": d["feature"], "vector": blob})
    idx.load(records, id_field="id_")
    return idx


def query_index(idx: SearchIndex, qvec: list[float], datatype: str) -> list[dict]:
    """Top-K from an index; encode query to match the field datatype."""
    if datatype == "int8":
        vec = quantize_int8(qvec)
        dt = "int8"
    else:
        vec = qvec
        dt = "float32"
    vq = VectorQuery(
        vector=vec,
        vector_field_name="vector",
        num_results=TOPK,
        return_fields=["id_", "feature"],
        dtype=dt,
    )
    return idx.query(vq)


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def main() -> int:
    docs = load_corpus()
    queries = load_queries()
    help_features = {p.name for p in CORPUS_DIR.iterdir() if p.is_dir()}
    labeled = [q for q in queries if q.get("expected_feature") in help_features]
    print(
        f"corpus={len(docs)} docs | queries={len(queries)} "
        f"({len(labeled)} with .help-matching labels)"
    )

    print("embedding corpus...", flush=True)
    doc_vecs = [embed(d["text"]) for d in docs]
    print("embedding queries...", flush=True)
    q_vecs = {q["id"]: embed(q["query"]) for q in queries}

    from redisvl.exceptions import RedisSearchError

    fp32 = make_index("bench_fp32", "float32", docs, doc_vecs)
    int8 = None
    int8_error = None
    try:
        int8 = make_index("bench_int8", "int8", docs, doc_vecs)
    except RedisSearchError as e:
        int8_error = str(e)
        print(f"int8 arm UNAVAILABLE on this Redis: {e}", file=sys.stderr)

    try:
        top1_match = 0
        overlaps = []
        p1 = {"float32": 0, "int8": 0}
        r5 = {"float32": 0, "int8": 0}

        for q in queries:
            qv = q_vecs[q["id"]]
            f_hits = query_index(fp32, qv, "float32")
            f_ids = [h["id_"] for h in f_hits]
            i_hits = query_index(int8, qv, "int8") if int8 else []
            i_ids = [h["id_"] for h in i_hits]
            if int8 and f_ids and i_ids and f_ids[0] == i_ids[0]:
                top1_match += 1
            if int8:
                overlaps.append(jaccard(set(f_ids), set(i_ids)))

            if q.get("expected_feature") in help_features:
                exp = q["expected_feature"]
                arms = [("float32", f_hits)] + ([("int8", i_hits)] if int8 else [])
                for arm, hits in arms:
                    feats = [h["feature"] for h in hits]
                    if feats and feats[0] == exp:
                        p1[arm] += 1
                    if exp in feats:
                        r5[arm] += 1

        n, nl = len(queries), len(labeled)
        res = {
            "corpus_docs": len(docs),
            "queries_total": n,
            "queries_labeled": nl,
            "p_at_1_float32": round(p1["float32"] / nl, 4),
            "recall_at_5_float32": round(r5["float32"] / nl, 4),
            "int8_available": int8 is not None,
        }
        if int8:
            res["agreement_top1"] = round(top1_match / n, 4)
            res["agreement_top5_jaccard_mean"] = round(sum(overlaps) / n, 4)
            res["p_at_1_int8"] = round(p1["int8"] / nl, 4)
            res["recall_at_5_int8"] = round(r5["int8"] / nl, 4)
            res["p_at_1_delta"] = round(res["p_at_1_float32"] - res["p_at_1_int8"], 4)
            res["recall_at_5_delta"] = round(
                res["recall_at_5_float32"] - res["recall_at_5_int8"], 4
            )
            res["gate_p_at_1_pass"] = res["p_at_1_delta"] <= P1_TOLERANCE
            res["gate_recall_at_5_pass"] = res["recall_at_5_delta"] <= R5_TOLERANCE
            res["GO"] = res["gate_p_at_1_pass"] and res["gate_recall_at_5_pass"]
        else:
            res["int8_blocked_reason"] = int8_error

        print(json.dumps(res, indent=2))
        return 0
    finally:
        fp32.delete(drop=True)
        if int8:
            int8.delete(drop=True)


if __name__ == "__main__":
    sys.exit(main())
