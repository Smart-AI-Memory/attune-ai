"""diagramkit Phase-0 probes P1 (capability) and P3 (patch value).

Authors three REAL session artifacts both as mermaid text and as the
candidate diagramkit spec (id-keyed node map + edge list), measures
both, then measures update-in-place both ways. merge_patch semantics
come from the shipped chartkit implementation.
"""

import json

from attune.widgets.chart_widget_tool import merge_patch


def B(s):
    return len(s.encode("utf-8"))


def CJ(o):
    return json.dumps(o, separators=(",", ":"))


def report(name, mermaid, spec):
    print(f"\n=== {name} ===")
    print(f"  nodes={len(spec['nodes'])} edges={len(spec['edges'])}")
    print(f"  mermaid: {B(mermaid)}B (~{B(mermaid)//4} tok)")
    c = CJ(spec)
    print(f"  spec:    {B(c)}B (~{B(c)//4} tok)")


# --- Artifact A: widget-kernel-family queue (real statuses, 2026-08-06)
A_MERMAID = """graph LR
  classDef done fill:#4fa66e,color:#fff
  classDef in_flight fill:#e0a53a,color:#fff
  classDef pending fill:#8a94a6,color:#fff
  bg[boundary gate]:::done --> fk[formkit kernel]:::in_flight
  fk --> ik[infokit tiles]:::pending
  lh[latency harness]:::pending --> dk[diagramkit build]:::pending
  ik --> dk
  p0[diagramkit phase-0]:::done --> dk
"""
A_SPEC = {
    "v": 1,
    "kind": "dag",
    "nodes": {
        "bg": {"label": "boundary gate", "status": "done"},
        "fk": {"label": "formkit kernel", "status": "in_flight"},
        "ik": {"label": "infokit tiles", "status": "pending"},
        "lh": {"label": "latency harness", "status": "pending"},
        "p0": {"label": "diagramkit phase-0", "status": "done"},
        "dk": {"label": "diagramkit build", "status": "pending"},
    },
    "edges": [["bg", "fk"], ["fk", "ik"], ["ik", "dk"], ["lh", "dk"], ["p0", "dk"]],
    "options": {"title": "widget-kernel-family queue"},
}

# --- Artifact B: PR #1963 pipeline, mid-run snapshot (real run shape)
B_MERMAID = """graph LR
  classDef done fill:#4fa66e,color:#fff
  classDef in_flight fill:#e0a53a,color:#fff
  classDef blocked fill:#e05c4a,color:#fff
  rb[rebase onto main]:::done --> li[lint + gates]:::done
  rb --> tm[test matrix 12 lanes]:::in_flight
  rb --> db[docs build]:::in_flight
  tm --> cov[codecov gates]:::in_flight
  li --> am[auto-merge]:::blocked
  cov --> am
  db --> am
"""
B_SPEC = {
    "v": 1,
    "kind": "dag",
    "nodes": {
        "rb": {"label": "rebase onto main", "status": "done"},
        "li": {"label": "lint + gates", "status": "done"},
        "tm": {"label": "test matrix 12 lanes", "status": "in_flight"},
        "db": {"label": "docs build", "status": "in_flight"},
        "cov": {"label": "codecov gates", "status": "in_flight"},
        "am": {"label": "auto-merge", "status": "blocked"},
    },
    "edges": [
        ["rb", "li"],
        ["rb", "tm"],
        ["rb", "db"],
        ["tm", "cov"],
        ["li", "am"],
        ["cov", "am"],
        ["db", "am"],
    ],
    "options": {"title": "PR 1963 pipeline"},
}

# --- Artifact C: attune.elicitation import graph (real, from grep)
C_EDGES = [
    ["init", "bridge"],
    ["init", "schema"],
    ["init", "reference"],
    ["init", "templates"],
    ["init", "widget"],
    ["bridge", "models"],
    ["bridge", "form_events"],
    ["schema", "models"],
    ["fix_intake", "intake"],
    ["fix_intake", "models"],
    ["intake", "bridge"],
    ["intake", "models"],
    ["intake", "workflows"],
    ["spec_intake", "intake"],
    ["spec_intake", "models"],
    ["templates", "bridge"],
    ["templates", "models"],
    ["widget", "bridge"],
    ["widget", "theme"],
    ["widget", "models"],
    ["wf_templates", "fix_intake"],
    ["wf_templates", "intake"],
]
C_NODE_IDS = sorted({n for e in C_EDGES for n in e})
C_SPEC = {
    "v": 1,
    "kind": "dag",
    "nodes": {n: {"label": n} for n in C_NODE_IDS},
    "edges": C_EDGES,
    "options": {"title": "attune.elicitation imports"},
}
C_MERMAID = "graph LR\n" + "".join(f"  {a} --> {b}\n" for a, b in C_EDGES)

report("A: family queue DAG", A_MERMAID, A_SPEC)
report("B: PR pipeline", B_MERMAID, B_SPEC)
report("C: import graph", C_MERMAID, C_SPEC)

# --- P3: update-in-place, both ways
print("\n=== P3: flip formkit -> done (artifact A) ===")
patch = {"nodes": {"fk": {"status": "done"}}}
print(f"  diagramkit patch: {B(CJ(patch))}B (~{max(1, B(CJ(patch))//4)} tok)")
merged = merge_patch(A_SPEC, patch)
assert merged["nodes"]["fk"] == {"label": "formkit kernel", "status": "done"}
assert merged["nodes"]["bg"] == A_SPEC["nodes"]["bg"]
print("  merge_patch semantics: label preserved, only status changed ✓")
remitted = A_MERMAID.replace("fk[formkit kernel]:::in_flight", "fk[formkit kernel]:::done")
print(f"  mermaid re-emission:  {B(remitted)}B (full text, no partial update exists)")

print("\n=== P3: topology change — add a node + edge (artifact A) ===")
topo_patch = {
    "nodes": {"rt": {"label": "roundtable ruling", "status": "pending"}},
    "edges": A_SPEC["edges"] + [["dk", "rt"]],
}
print(f"  diagramkit patch: {B(CJ(topo_patch))}B (edges array replaces wholesale)")
merged2 = merge_patch(A_SPEC, topo_patch)
assert len(merged2["edges"]) == 6 and len(merged2["nodes"]) == 7
print("  merge_patch semantics: node map merged, edge list replaced ✓")

print("\n=== P3 design finding ===")
bad_nodes_as_array = {"nodes": [dict(v, id=k) for k, v in A_SPEC["nodes"].items()]}
flip_via_array = {
    "nodes": [
        dict(v, id=k, status="done" if k == "fk" else v.get("status"))
        for k, v in A_SPEC["nodes"].items()
    ]
}
print(
    f"  if nodes were an ARRAY (chartkit-style), the same status flip "
    f"costs {B(CJ(flip_via_array))}B (whole array replaces) vs "
    f"{B(CJ(patch))}B with the id-keyed map"
)
