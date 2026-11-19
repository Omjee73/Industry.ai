"""Hand-placed architecture diagram generator.

Renders a self-contained, offline architecture HTML from an Archify
architecture candidate JSON (``backend/scripts/generate_architecture_html.py``).

Note: this is the hand-placed fallback path documented in Archify's skill.
Archify's own ``finalize`` CLI was attempted and aborted with
``finalize/receipt-publication`` (``finalize-receipt-changed-during-inspection``),
so the diagram is rendered here from the verified candidate instead.

Usage:
    python backend/scripts/generate_architecture_html.py [--candidate PATH] [--out PATH]

By default it picks the newest candidate under ``.archify/`` and writes to
``docs/architecture_diagram.html``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "docs" / "architecture_diagram.html"

TYPE_COLORS = {
    "external": "#475569",   # slate
    "frontend": "#3b82f6",   # blue
    "backend": "#f97316",    # amber (orange)
    "database": "#0891b2",   # teal
    "security": "#dc2626",   # red
    "messagebus": "#7c3aed", # violet
    "cloud": "#0ea5e9",      # sky
}


def _hex(color: str) -> str:
    """Expand a #rgb to #rrggbb and provide light/dark shades."""
    c = color.strip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    dark_bg = f"#{c}1a"  # 6-digit with low alpha-ish tint (hex fudge)
    return color, dark_bg


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _render_node(node: dict, x: float, y: float, w: float, h: float) -> str:
    color = TYPE_COLORS.get(node.get("type", "external"), "#475569")
    fill, _ = _hex(color)
    tag = node.get("tag")
    title = node["label"]
    sublabel = node.get("sublabel", "")
    label_html = f"<div class='label' style='color:{fill}'>{_esc(title)}</div>"
    if sublabel:
        label_html += f"<div class='sublabel'>{_esc(sublabel)}</div>"
    if tag:
        label_html += f"<div class='tag'>{_esc(tag)}</div>"
    return (
        f"<g class='node' transform='translate({x},{y})'>\n"
        f"  <rect x='0' y='0' width='{w}' height='{h}' rx='10' fill='#FFFFFF' "
        f"stroke='{fill}' stroke-width='2.5'/>\n"
        f"  <foreignObject x='0' y='0' width='{w}' height='{h}' "
        f"pointer-events='none'><div class='node-body'>{label_html}</div></foreignObject>\n"
        f"</g>"
    )


def _render_edge(conn: dict, n1: dict, n2: dict, W: float, H: float) -> tuple[str, str]:
    """Return (svg_edge, label_html) for one connection."""
    x1, y1 = n1["pos"]
    w1, h1 = n1["size"]
    x2, y2 = n2["pos"]
    w2, h2 = n2["size"]

    def center(n):
        return (n["pos"][0] + n["size"][0] / 2, n["pos"][1] + n["size"][1] / 2)

    def edge_point(n, other):
        cx, cy = center(n)
        ox, oy = center(other)
        dx, dy = (ox - cx, oy - cy)
        if abs(dx) > abs(dy):
            half = n["size"][0] / 2 + 2
            return (cx + (dx / abs(dx)) * half, cy)
        half = n["size"][1] / 2 + 2
        return (cx, cy + (dy / abs(dy)) * half)

    p1 = edge_point(n1, n2)
    p2 = edge_point(n2, n1)
    style_bits = []
    variant = conn.get("variant", "")
    if variant == "dashed":
        style_bits.append("stroke-dasharray='7 6'")
    if variant == "emphasis":
        style_bits.append("stroke-width='2.4'")
    else:
        style_bits.append("stroke-width='1.6'")
    line = (
        f"<line x1='{p1[0]}' y1='{p1[1]}' x2='{p2[0]}' y2='{p2[1]}' "
        f"stroke='var(--edge)' {' '.join(style_bits)}/>"
        f"<defs><marker id='arrow-{abs(hash(p1[0] * p2[1] - p1[1] * p2[0])) % 100000}' "
        f"markerWidth='9' markerHeight='7' refX='8' refY='3.5' orient='auto' "
        f"marker-end='true'><polygon points='0 0, 9 3.5, 0 7' fill='var(--edge)'/></marker></defs>\n"
        f"<line x1='{p1[0]}' y1='{p1[1]}' x2='{p2[0]}' y2='{p2[1]}' stroke='var(--edge)' "
        f"{' '.join(style_bits)} marker-end='url(#arrow-{abs(hash(p1[0] * p2[1] - p1[1] * p2[0])) % 100000})'/>"
    )
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    label = conn.get("label")
    label_html = ""
    if label:
        label_html = (
            f"<div class='edge-label' style='left:{mid[0] - 60}px;top:{mid[1] - 22}px;'>"
            f"{_esc(label)}</div>"
        )
    return line, label_html


def render_html(candidate: dict) -> str:
    nodes = candidate.get("components", [])
    connections = candidate.get("connections", [])
    boundaries = candidate.get("boundaries", [])
    cards = candidate.get("cards", [])
    meta = candidate.get("meta", {})

    margin = 20
    W = max((n["pos"][0] + n["size"][0] for n in nodes), default=600) + margin
    H = max((n["pos"][1] + n["size"][1] for n in nodes), default=400) + margin

    node_by_id = {n["id"]: n for n in nodes}
    svg_parts = [f"<svg viewBox='0 0 {W} {H}' width='100%' height='{H}px' preserveAspectRatio='xMidYMid'>"]
    svg_parts.append("<rect width='100%' height='100%' rx='12' fill='var(--surface)'/>")

    # boundaries (dashed wrappers around nodes)
    for b in boundaries:
        wrapped = [node_by_id[i] for i in b.get("wraps", []) if i in node_by_id]
        if not wrapped:
            continue
        pad = b.get("pad", 12)
        x0 = min(n["pos"][0] - pad for n in wrapped)
        y0 = min(n["pos"][1] - pad for n in wrapped)
        x1 = max(n["pos"][0] + n["size"][0] + pad for n in wrapped)
        y1 = max(n["pos"][1] + n["size"][1] + pad for n in wrapped)
        svg_parts.append(
            f"<rect x='{x0}' y='{y0}' width='{x1 - x0}' height='{y1 - y0}' rx='8' fill='none' "
            f"stroke='var(--edge)' stroke-width='1.2' stroke-dasharray='7 5'/>\n"
            f"<text x='{x0 + 4}' y='{y0 - 2}' font-size='12' fill='var(--fg)' font-weight='600' "
            f"opacity='0.85'>{_esc(b['label'])}</text>"
        )

    # edges first (behind nodes)
    for conn in connections:
        if conn.get("from") in node_by_id and conn.get("to") in node_by_id:
            line, label_html = _render_edge(conn, node_by_id[conn["from"]], node_by_id[conn["to"]], W, H)
            svg_parts.append(line)

    # nodes
    for n in nodes:
        svg_parts.append(_render_node(n, n["pos"][0], n["pos"][1], n["size"][0], n["size"][1]))

    # edge labels (top layer)
    for conn in connections:
        if conn.get("from") in node_by_id and conn.get("to") in node_by_id:
            _, label_html = _render_edge(conn, node_by_id[conn["from"]], node_by_id[conn["to"]], W, H)
            if label_html:
                svg_parts.append(label_html)
    svg_parts.append("</svg>")
    svg = "\n".join(svg_parts)

    # cards panel
    cards_html = ""
    for card in cards:
        dot = card.get("dot", "cyan")
        title = _esc(card["title"])
        items = "".join(f"<li>{_esc(item)}</li>" for item in card.get("items", []))
        cards_html += (
            f"<article class='card'>\n"
            f"  <div class='card-head'><span class='dot' style='background:var(--dot-{dot}, #06b6d4)'></span>"
            f"  <h3>{title}</h3></div>\n"
            f"  <ul class='card-items'>{items}</ul>\n</article>"
        )

    title = _esc(meta.get("title", "Architecture"))
    subtitle = meta.get("subtitle", "")

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} — Architecture</title>
<style>
:root {{
  --surface: #FAFBFC;
  --card: #FFFFFF;
  --elevated: #F8F9FC;
  --fg: #1F2937;
  --muted: #6B7280;
  --subtle: #CBD2D9;
  --edge: #9CA3AF;
  --text-on-node: #FFFFFF;
  --dot-cyan: #06b6d4;
  --dot-emerald: #10b981;
  --dot-rose: #F43F5E;
  --dot-violet: #7c3aed;
}}
.dark {{
  --surface: #0F1113;
  --card: #15181D;
  --elevated: #1B1F25;
  --fg: #E8EAF0;
  --muted: #9AA0A8;
  --subtle: #5B5F66;
  --edge: #474C57;
  --text-on-node: #FFFFFF;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--surface); color: var(--fg); font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }}
.wrap {{ display: flex; align-items: flex-start; gap: 24px; padding: 28px; max-width: 1620px; margin: 0 auto; }}
.canvas-wrap {{ flex: 1 1 auto; min-width: 0; display: block; }}
.canvas-wrap svg {{ width: 100%; height: auto; display: block; border-radius: 14px; background: var(--card); box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06); }}
.cards-panel {{ flex: 0 0 290px; display: flex; flex-direction: column; gap: 12px; }}
.card {{ background: var(--card); border: 2px solid var(--subtle); border-radius: 14px; padding: 16px 18px; }}
.card .card-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.card .card-head .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
.card .card-head h3 {{ font-size: 14px; font-weight: 700; margin: 0; }}
.card-items {{ list-style: none; padding: 0; margin: 0; font-size: 12.5px; line-height: 1.55; color: var(--muted); }}
.card-items li {{ display: flex; gap: 8px; align-items: flex-start; }}
.card-items li::before {{ content: '•'; color: var(--dot-cyan); flex: none; }}
.node .node-body {{ font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }}
.node .label {{ font-size: 14px; font-weight: 700; color: var(--text-on-node); text-align: center; }}
.node .sublabel {{ font-size: 11px; color: #FFFFFF; opacity: 0.85; text-align: center; margin-top: 2px; }}
.node .tag {{ font-size: 10px; color: #FFFFFF; opacity: 0.9; text-align: center; margin-top: 3px; font-family: ui-monospace, monospace; }}
.edge-label {{ position: absolute; background: var(--surface); color: var(--muted); font-size: 11px; border: 1px solid var(--subtle); border-radius: 6px; padding: 1px 7px; white-space: nowrap; }}
.header {{ padding: 0 28px; border-bottom: 2px solid var(--subtle); }}
.header-row {{ display: flex; align-items: baseline; justify-content: space-between; }}
h1 {{ font-size: 22px; margin: 14px 0 2px; letter-spacing: -0.01em; }}
h1 small {{ display: block; font-size: 13px; color: var(--muted); font-weight: 400; margin-top: 2px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; color: var(--muted); margin-top: 10px; }}
.legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
.legend i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
footer {{ font-size: 11.5px; color: var(--muted); text-align: center; padding: 18px 28px; border-top: 2px solid var(--subtle); }}
@media (max-width: 1180px) {{
  .wrap {{ flex-direction: column; align-items: stretch; }}
  .cards-panel {{ flex: 1 1 auto; }}
  .canvas-wrap {{ min-width: 0; overflow-x: auto; }}
}}
</style>
</head>
<body>
<header class="header">
  <div class="header-row">
    <div><h1>{title}<small>{subtitle}</small></h1></div>
  </div>
  <p style="font-size:13px;color:var(--muted);margin:4px 0 0;">Architecture of the PCB Missing Component Detection application (Task B). Fully offline, web-only.</p>
</header>
<main class="wrap">
  <div class="canvas-wrap">
    {svg}
    <div class="legend">
      <span><i style="background:#475569"></i> external · <i style="background:#3b82f6"></i> frontend ·
      <i style="background:#f97316"></i> backend · <i style="background:#0891b2"></i> database ·
      <i style="background:#dc2626"></i> security · <i style="background:#7c3aed"></i> messagebus ·
      <i style="background:#0ea5e9"></i> cloud</span>
    </div>
  </div>
  <aside class="cards-panel">{cards_html}</aside>
</main>
<footer>Generated by backend/scripts/generate_architecture_html.py from
<code>.archify/architecture-pcb-inspector-*/candidate.json</code>. Offline: everything shown runs on the local machine.</footer>
<script>
  // Theme toggle via prefers-color-scheme (reacts to system setting).
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {{
    document.documentElement.classList.add('dark');
  }}
  window.addEventListener('load', () => {{
    window.addEventListener('click', () => {{
      document.documentElement.classList.toggle('dark', window.matchMedia('(prefers-color-scheme: dark)').matches);
    }}, {{ passive: true }});
  }});
</script>
</body>
</html>
"""
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docs/architecture_diagram.html from an Archify candidate.")
    parser.add_argument("--candidate", default=None, help="Path to the candidate.json")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output path for the diagram HTML")
    args = parser.parse_args()

    candidates = sorted(REPO_ROOT.glob(".archify/architecture-*/candidate.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        print("ERROR: no candidates found under .archify/architecture-*/candidate.json")
        return 1
    candidate_path = Path(args.candidate) if args.candidate else candidates[-1]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(candidate), encoding="utf-8")
    print(f"Wrote architecture diagram to {out_path} (from {candidate_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
