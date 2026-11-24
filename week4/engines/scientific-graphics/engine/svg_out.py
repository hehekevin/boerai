"""SVG writer: layered, text-editable, provenance-annotated."""
from __future__ import annotations

import hashlib
import json
import os
from xml.sax.saxutils import escape

from . import geom
from .draw import LAYER_ORDER, Drawing


def _f(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _dash(on: float, off: float) -> str:
    return f'stroke-dasharray="{_f(on)} {_f(off)}"'


def write_svg(drawing: Drawing, path: str, spec) -> dict:
    W, H = spec.width_mm, spec.height_mm
    scale = geom.MM2PT
    family = ", ".join(_quote_family(f) for f in spec.font_stack)
    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{_f(W)}mm" height="{_f(H)}mm" viewBox="0 0 {_f(W * scale)} {_f(H * scale)}" '
        f'version="1.1">')
    meta = {
        "generator": "FigForge",
        "case_id": spec.case_id,
        "figure_id": spec.figure_id,
        "figure_kind": spec.figure_kind,
        "units": "mm",
        "canvas_mm": [W, H],
        "font_family": spec.font_stack,
        "line_pt": spec.line_pt,
        "sources": spec.sources,
        "evidence": spec.evidence,
    }
    parts.append("<metadata>" + escape(json.dumps(meta, ensure_ascii=False)) + "</metadata>")
    parts.append(f"<title>{escape(spec.title or spec.figure_id)}</title>")
    parts.append(f"<desc>{escape(spec.caption[:400])}</desc>")
    parts.append(f'<g transform="scale({_f(scale)})" font-family="{family}" '
                 f'stroke-linecap="round" stroke-linejoin="round">')

    by_layer: dict[str, list[dict]] = {}
    for p in drawing.prims:
        by_layer.setdefault(p["layer"] or "canvas", []).append(p)

    order = LAYER_ORDER + [l for l in by_layer if l not in LAYER_ORDER]
    for layer in order:
        plist = by_layer.get(layer)
        if not plist:
            continue
        parts.append(f'<g id="layer-{layer}" inkscape:groupmode="layer" inkscape:label="{layer}">')
        for p in plist:
            parts.append(_prim(p))
        parts.append("</g>")
    parts.append("</g></svg>")
    data = "\n".join(parts) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data)
    return {"path": path, "bytes": len(data.encode("utf-8")),
            "sha256": hashlib.sha256(data.encode("utf-8")).hexdigest(),
            "layers": [l for l in order if l in by_layer],
            "text_elements": sum(1 for p in drawing.prims if p["kind"] == "text")}


def _quote_family(name: str) -> str:
    return "'" + name.replace("'", "") + "'"


def _prim(p: dict) -> str:
    kind = p["kind"]
    tag = escape(p.get("tag", "") or "")
    src = escape(str(p.get("src", "") or ""))
    extra = ""
    if tag:
        extra += f' data-tag="{tag}"'
    if src:
        extra += f' data-src="{src}"'
    if kind == "rect":
        rx = f' rx="{_f(p["rx"])}" ry="{_f(p["rx"])}"' if p.get("rx") else ""
        dash = " " + _dash(1.2, 0.9) if p.get("dash") else ""
        return (f'<rect x="{_f(p["x"])}" y="{_f(p["y"])}" width="{_f(p["w"])}" height="{_f(p["h"])}"'
                f'{rx} fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="{_f(p["sw"])}"'
                f' opacity="{_f(p["opacity"])}"{dash}{extra}/>')
    if kind == "line":
        dash = " " + _dash(1.2, 0.9) if p.get("dash") else ""
        return (f'<line x1="{_f(p["x1"])}" y1="{_f(p["y1"])}" x2="{_f(p["x2"])}" y2="{_f(p["y2"])}"'
                f' stroke="{p["stroke"]}" stroke-width="{_f(p["sw"])}" opacity="{_f(p["opacity"])}"'
                f'{dash}{extra}/>')
    if kind == "poly":
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in p["pts"])
        dash = " " + _dash(1.2, 0.9) if p.get("dash") else ""
        shape = "polygon" if p["closed"] else "polyline"
        fill = p["fill"] if p["closed"] else "none"
        return (f'<{shape} points="{pts}" fill="{fill}" stroke="{p["stroke"]}"'
                f' stroke-width="{_f(p["sw"])}" opacity="{_f(p["opacity"])}"{dash}{extra}/>')
    if kind == "circle":
        return (f'<circle cx="{_f(p["cx"])}" cy="{_f(p["cy"])}" r="{_f(p["r"])}" fill="{p["fill"]}"'
                f' stroke="{p["stroke"]}" stroke-width="{_f(p["sw"])}" opacity="{_f(p["opacity"])}"{extra}/>')
    if kind == "ellipse":
        return (f'<ellipse cx="{_f(p["cx"])}" cy="{_f(p["cy"])}" rx="{_f(p["rx"])}" ry="{_f(p["ry"])}"'
                f' fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="{_f(p["sw"])}"'
                f' opacity="{_f(p["opacity"])}"{extra}/>')
    if kind == "text":
        return _text(p, extra)
    return ""


def _text(p: dict, extra: str) -> str:
    size = p["size"] * geom.PT2MM
    anchor = {"middle": "middle", "end": "end", "start": "start"}.get(p["anchor"], "start")
    baseline = {"middle": "central", "top": "text-before-edge", "bottom": "text-after-edge"}.get(
        p["baseline"], "alphabetic")
    style = []
    style.append(f'font-size="{_f(size)}"')
    style.append(f'fill="{p["fill"]}"')
    style.append(f'text-anchor="{anchor}"')
    style.append(f'dominant-baseline="{baseline}"')
    if p.get("weight") == "bold":
        style.append('font-weight="bold"')
    if p.get("style") == "italic":
        style.append('font-style="italic"')
    if p.get("rotate"):
        style.append(f'transform="rotate({_f(p["rotate"])} {_f(p["x"])} {_f(p["y"])})"')
    body = escape(p["text"])
    out = ""
    if p.get("bg"):
        w = geom.text_width_mm(p["text"], p["size"]) + 1.2
        h = p["size"] * geom.PT2MM * 1.3
        x = p["x"] - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
        out += (f'<rect x="{_f(x)}" y="{_f(p["y"] - h / 2)}" width="{_f(w)}" height="{_f(h)}" '
                f'fill="#FFFFFF" opacity="0.88" stroke="none"/>')
    out += f'<text x="{_f(p["x"])}" y="{_f(p["y"])}" {" ".join(style)}{extra}>{body}</text>'
    return out
