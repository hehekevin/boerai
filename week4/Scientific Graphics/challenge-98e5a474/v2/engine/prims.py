"""Primitive constructors shared by the layout renderers.

Every primitive is a plain dict in millimetre coordinates (origin top-left).
`tag` names the graphic object, `src` carries the evidence id, so both are
carried into the SVG as data-* attributes for round-trip inspection.
"""
from __future__ import annotations


def rect(x, y, w, h, fill="#FFFFFF", stroke="none", sw=0.2, rx=0.0, dash=False,
         opacity=1.0, layer="", tag="", src="", stroke_opacity=1.0):
    return {"kind": "rect", "x": x, "y": y, "w": w, "h": h, "rx": rx, "fill": fill,
            "stroke": stroke, "sw": sw, "dash": dash, "opacity": opacity, "layer": layer,
            "tag": tag, "src": src, "stroke_opacity": stroke_opacity}


def line(x1, y1, x2, y2, stroke="#333333", sw=0.25, dash=False, marker_end="", marker_start="",
         marker_size=1.6, opacity=1.0, layer="", tag="", src=""):
    return {"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "stroke": stroke,
            "sw": sw, "dash": dash, "marker_end": marker_end, "marker_start": marker_start,
            "marker_size": marker_size, "opacity": opacity, "layer": layer, "tag": tag, "src": src}


def poly(pts, closed=False, fill="none", stroke="#333333", sw=0.25, dash=False, opacity=1.0,
         layer="", tag="", src=""):
    return {"kind": "poly", "pts": [(float(a), float(b)) for a, b in pts], "closed": closed,
            "fill": fill, "stroke": stroke, "sw": sw, "dash": dash, "opacity": opacity,
            "layer": layer, "tag": tag, "src": src}


def text(x, y, s, size=6.0, anchor="middle", baseline="middle", fill="#111111", weight="normal",
         rotate=0.0, style="normal", layer="", tag="", src="", family="", bg=False):
    return {"kind": "text", "x": x, "y": y, "text": str(s), "size": size, "anchor": anchor,
            "baseline": baseline, "fill": fill, "weight": weight, "rotate": rotate,
            "style": style, "layer": layer, "tag": tag, "src": src, "family": family, "bg": bg}


def circle(cx, cy, r, fill="#FFFFFF", stroke="none", sw=0.2, opacity=1.0, layer="", tag="", src=""):
    return {"kind": "circle", "cx": cx, "cy": cy, "r": r, "fill": fill, "stroke": stroke,
            "sw": sw, "opacity": opacity, "layer": layer, "tag": tag, "src": src}


def ellipse(cx, cy, rx, ry, fill="#FFFFFF", stroke="none", sw=0.2, opacity=1.0, layer="", tag="", src=""):
    return {"kind": "ellipse", "cx": cx, "cy": cy, "rx": rx, "ry": ry, "fill": fill,
            "stroke": stroke, "sw": sw, "opacity": opacity, "layer": layer, "tag": tag, "src": src}
