"""diagramkit Phase-0 probe P2: pure-Python layered layout + SVG render.

The layout section below (between LAYOUT-BEGIN and LAYOUT-END) is the
measured artifact: a longest-path layering + barycenter ordering +
coordinate assignment in plain stdlib Python. The SVG emitter is probe
scaffolding (the real kernel would draw; this exists to judge
readability).
"""

import json
import sys
from pathlib import Path

# LAYOUT-BEGIN


def layered_layout(nodes, edges, dx=200, dy=64):
    """Position a DAG left-to-right: {id: (x, y)}.

    Longest-path layering, then 4 barycenter sweeps to reduce edge
    crossings, then simple per-layer vertical spread.
    """
    succ = {n: [] for n in nodes}
    pred = {n: [] for n in nodes}
    for a, b in edges:
        succ[a].append(b)
        pred[b].append(a)

    layer = {}

    def depth(n, seen=()):
        if n in layer:
            return layer[n]
        if n in seen:
            raise ValueError(f"cycle through {n!r}")
        d = 1 + max((depth(p, seen + (n,)) for p in pred[n]), default=-1)
        layer[n] = d
        return d

    for n in nodes:
        depth(n)

    layers = {}
    for n, d in layer.items():
        layers.setdefault(d, []).append(n)
    for d in layers:
        layers[d].sort()

    for sweep in range(4):
        forward = sweep % 2 == 0
        for d in sorted(layers, reverse=not forward):
            ref = pred if forward else succ
            rank = {n: i for ns in layers.values() for i, n in enumerate(ns)}

            def bary(n, ref=ref, rank=rank):
                nbrs = ref[n]
                if not nbrs:
                    return float(rank[n])
                return sum(rank[m] for m in nbrs) / len(nbrs)

            layers[d].sort(key=bary)

    pos = {}
    tallest = max(len(ns) for ns in layers.values())
    for d, ns in layers.items():
        offset = (tallest - len(ns)) / 2
        for i, n in enumerate(ns):
            pos[n] = (d * dx + 20, (i + offset) * dy + 20)
    return pos


# LAYOUT-END

STATUS_FILL = {
    "done": "#4fa66e",
    "in_flight": "#e0a53a",
    "blocked": "#e05c4a",
}
DEFAULT_FILL = "#8a94a6"
NODE_W, NODE_H = 168, 40


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(spec, pos):
    parts = []
    for a, b in spec["edges"]:
        x1, y1 = pos[a][0] + NODE_W, pos[a][1] + NODE_H / 2
        x2, y2 = pos[b][0], pos[b][1] + NODE_H / 2
        if x2 - x1 > 220:
            yb = max(y1, y2) + 35
            d = (
                f"M{x1:.0f},{y1:.0f} C{x1 + 80:.0f},{yb:.0f} "
                f"{x2 - 80:.0f},{yb:.0f} {x2:.0f},{y2:.0f}"
            )
        else:
            mx = (x1 + x2) / 2
            d = f"M{x1:.0f},{y1:.0f} C{mx:.0f},{y1:.0f} " f"{mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"
        parts.append(
            f'<path d="{d}" fill="none" stroke="#99a" stroke-width="1.5" '
            'marker-end="url(#arr)"/>'
        )
    for nid, meta in spec["nodes"].items():
        x, y = pos[nid]
        fill = STATUS_FILL.get(meta.get("status", ""), DEFAULT_FILL)
        label = esc(meta.get("label", nid))
        parts.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{NODE_W}" height="{NODE_H}" '
            f'rx="8" fill="{fill}"/>'
            f'<text x="{x + NODE_W / 2:.0f}" y="{y + NODE_H / 2 + 4:.0f}" '
            f'text-anchor="middle" font-size="12" font-family="sans-serif" '
            f'fill="#fff">{label}</text>'
        )
    w = max(x for x, _ in pos.values()) + NODE_W + 20
    h = max(y for _, y in pos.values()) + NODE_H + 20
    title = esc(spec.get("options", {}).get("title", ""))
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h + 30:.0f}" '
        f'width="100%"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#99a"/></marker></defs>'
        f'<text x="20" y="{h + 18:.0f}" font-size="13" font-weight="500" '
        f'font-family="sans-serif" fill="#222">{title}</text>'
    )
    return head + "".join(parts) + "</svg>"


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    specs = json.loads(Path(sys.argv[2]).read_text())
    src = Path(__file__).read_text()
    layout_code = src.split("# LAYOUT-BEGIN")[1].split("# LAYOUT-END")[0]
    print(f"layout code: {len(layout_code.encode())} bytes, {len(layout_code.splitlines())} lines")
    for name, spec in specs.items():
        pos = layered_layout(list(spec["nodes"]), spec["edges"])
        svg = to_svg(spec, pos)
        (out / f"{name}.svg").write_text(svg)
        print(f"  {name}: {len(spec['nodes'])} nodes -> {len(svg.encode())}B svg")


if __name__ == "__main__":
    main()
