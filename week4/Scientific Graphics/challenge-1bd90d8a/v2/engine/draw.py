"""Build the display list (vector primitives, mm) for a laid-out spec."""
from __future__ import annotations

import math

from . import geom, prims, style
from .geom import Rect
from .ir import RELATION_TYPES, Spec
from .layout import Layout

LAYER_ORDER = ["canvas", "lanes", "containers", "edges", "nodes", "charts", "annotations",
               "legend", "title", "caption", "framing"]


class Drawing:
    def __init__(self, spec: Spec, layout: Layout):
        self.spec = spec
        self.layout = layout
        self.prims: list[dict] = []
        self.text_boxes: list[dict] = []   # for overflow / overlap checks
        self.shapes: list[dict] = []       # for overlap checks
        self.labels: list[dict] = []       # rendered text inventory
        self.marks: list[dict] = []        # data marks with values (bars, points, cells)
        self.substitutions: set[str] = set()
        self.build()

    # ------------------------------------------------------------------ API
    def add(self, p: dict) -> None:
        if p["kind"] == "text":
            cleaned, subs = geom.sanitize(p["text"])
            if subs:
                p = dict(p)
                p["text"] = cleaned
                for ch in subs:
                    self.substitutions.add(ch)
        self.prims.append(p)
        if p["kind"] == "text":
            w = geom.text_width_mm(p["text"], p["size"])
            h = p["size"] * geom.PT2MM * 1.15
            if abs(p.get("rotate", 0) or 0) in (90, -90, 270, -270):
                w, h = h, w
            anchor = p["anchor"]
            x = p["x"] - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
            self.text_boxes.append({"rect": Rect(x, p["y"] - h / 2, w, h), "text": p["text"],
                                    "tag": p["tag"], "layer": p["layer"], "size": p["size"]})
            self.labels.append({"text": p["text"], "tag": p["tag"], "src": p.get("src", ""),
                                "layer": p["layer"]})
        elif p["kind"] in {"rect", "ellipse", "circle", "poly"} and p["layer"] in {"nodes", "charts", "containers"}:
            self.shapes.append({"p": p, "tag": p.get("tag", "")})

    def build(self) -> None:
        spec, lay = self.spec, self.layout
        self.add(prims.rect(0, 0, spec.width_mm, spec.height_mm, fill=spec.background,
                            stroke="none", layer="canvas", tag="canvas"))
        self._draw_lanes()
        self._draw_panels()
        self._draw_containers()
        self._draw_edges()
        self._draw_nodes()
        self._draw_charts()
        self._draw_annotations()
        self._draw_legend()
        self._draw_title_caption()

    # --------------------------------------------------------------- layers
    def _draw_lanes(self) -> None:
        spec = self.spec
        for lid, r in self.layout.lanes.items():
            lane = spec.lane_by_id.get(lid, {})
            fill = lane.get("fill") or "#F7F9FB"
            if lane.get("fill") == "none":
                continue
            self.add(prims.rect(r.x, r.y, r.w, r.h, fill=fill, stroke="none", layer="lanes", tag=f"lane:{lid}"))
            self.add(prims.line(r.x, r.y, r.x1, r.y, stroke="#C9D2DA", sw=0.18, dash=True,
                                layer="lanes", tag=f"lane:{lid}"))
            self.add(prims.line(r.x, r.y1, r.x1, r.y1, stroke="#C9D2DA", sw=0.18, dash=True,
                                layer="lanes", tag=f"lane:{lid}"))
            if lane.get("label"):
                size = spec.font_pt * 0.82
                self.add(prims.text(r.x + 1.4, r.y + 2.2, lane["label"], size=size, anchor="start",
                                    fill="#5A6672", weight="bold", layer="lanes", tag=f"lane:{lid}"))

    def _draw_panels(self) -> None:
        spec = self.spec
        self.panel_letters = {}
        for p in spec.panels:
            r = self.layout.panels.get(p["id"])
            if not r:
                continue
            if p["title"] or p["id"]:
                size = spec.font_pt * 1.1
                x = r.x
                y = r.y - 1.8
                if y < 3.2:
                    y = r.y + 2.6
                label = p["id"]
                self.add(prims.text(x, y, label, size=size, anchor="start", weight="bold",
                                    fill="#111111", layer="framing", tag=f"panel:{p['id']}"))
                if p["title"]:
                    self.add(prims.text(x + geom.text_width_mm(label, size) + 1.4, y, p["title"],
                                        size=size * 0.92, anchor="start", fill="#333333",
                                        layer="framing", tag=f"panel:title:{p['id']}"))
                self.panel_letters[p["id"]] = (x, y)
        # panel separator rules for multi-panel figures
        if len(self.layout.panels) > 1:
            rects = list(self.layout.panels.values())
            for i in range(len(rects) - 1):
                a, b = rects[i], rects[i + 1]
                if abs(a.y - b.y) < 0.5 and abs(a.h - b.h) < 0.5:
                    xm = (a.x1 + b.x) / 2
                    self.add(prims.line(xm, a.y, xm, a.y1, stroke="#E2E2E2", sw=0.2,
                                        layer="framing", tag="panel-sep"))

    def _draw_containers(self) -> None:
        spec = self.spec
        for c in spec.containers:
            r = self.layout.containers.get(c["id"])
            if not r:
                continue
            fill = c["fill"] or "#FBFBFB"
            stroke = c["stroke"] or "#9AA5B1"
            dash = c["relation"] in {"part_of", "associate"}
            self.add(prims.rect(r.x, r.y, r.w, r.h, fill=fill, stroke=stroke, sw=0.22, rx=1.6,
                                dash=dash, opacity=0.95, layer="containers", tag=f"container:{c['id']}",
                                src=c.get("source", "")))
            if c["label"]:
                size = spec.font_pt * 0.82
                self.add(prims.text(r.x + 1.4, r.y + 1.7, c["label"], size=size, anchor="start",
                                    fill="#44505C", weight="bold", layer="containers",
                                    tag=f"container:label:{c['id']}", src=c.get("source", "")))

    def _draw_edges(self) -> None:
        spec = self.spec
        for e in spec.edges:
            routed = self.layout.edges.get(e["id"])
            if not routed:
                continue
            color = e["color"] or style.SEMANTIC.get(e["type"], "#333333")
            sw = geom.pt2mm(e["width_pt"] if e["width_pt"] else spec.line_pt)
            if e["type"] in {"contain", "part_of"}:
                sw *= 0.9
            pts = routed["poly"]
            end = style.END_STYLE.get(e["type"], "arrow")
            msize = max(1.5, 2.1 * sw / max(0.15, geom.pt2mm(0.6)))
            msize = min(msize, 2.6)
            self.add(prims.poly(pts, closed=False, stroke=color, sw=sw, dash=e["dash"],
                                layer="edges", tag=f"edge:{e['id']}", src=e.get("source", "")))
            self._arrowhead(pts[-2], pts[-1], end, color, sw, msize, f"edge:{e['id']}")
            if e["bidirectional"]:
                self._arrowhead(pts[1], pts[0], end, color, sw, msize, f"edge:{e['id']}")
            if e["label"]:
                size = spec.font_pt * 0.78
                mid = self.layout.edge_labels.get(e["id"]) or _label_anchor(pts)[0]
                self.add(prims.text(mid[0], mid[1], e["label"], size=size, anchor="middle",
                                    fill=color, bg=True, rotate=0, layer="edges",
                                    tag=f"edge:label:{e['id']}", src=e.get("source", "")))

    def _arrowhead(self, p0, p1, kind: str, color: str, sw: float, size: float, tag: str) -> None:
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        d = math.hypot(dx, dy)
        if d < 1e-6 or kind == "none":
            return
        ux, uy = dx / d, dy / d
        px, py = -uy, ux
        tip = p1
        L, W = size * 1.35, size * 0.62
        if kind == "arrow":
            base = (tip[0] - ux * L, tip[1] - uy * L)
            self.add(prims.poly([tip, (base[0] + px * W, base[1] + py * W),
                                 (base[0] - px * W, base[1] - py * W)], closed=True, fill=color,
                                stroke=color, sw=0.1, layer="edges", tag=tag + ":head"))
        elif kind == "bar":
            self.add(prims.line(tip[0] - px * size * 0.9, tip[1] - py * size * 0.9,
                                tip[0] + px * size * 0.9, tip[1] + py * size * 0.9,
                                stroke=color, sw=sw * 1.5, layer="edges", tag=tag + ":bar"))
        elif kind == "diamond":
            mid = (tip[0] - ux * size * 0.6, tip[1] - uy * size * 0.6)
            back = (tip[0] - ux * size * 1.2, tip[1] - uy * size * 1.2)
            self.add(prims.poly([tip, (mid[0] + px * size * 0.5, mid[1] + py * size * 0.5), back,
                                 (mid[0] - px * size * 0.5, mid[1] - py * size * 0.5)],
                                closed=True, fill="#FFFFFF", stroke=color, sw=sw * 0.9,
                                layer="edges", tag=tag + ":diamond"))
        elif kind == "dot":
            self.add(prims.circle(tip[0], tip[1], size * 0.35, fill=color, stroke="none",
                                  layer="edges", tag=tag + ":dot"))

    def _draw_nodes(self) -> None:
        spec = self.spec
        for n in spec.nodes:
            r = self.layout.nodes.get(n["id"])
            if not r:
                continue
            fill, stroke = style.class_colors(n["class"])
            fill = n["fill"] or fill
            stroke = n["stroke"] or stroke
            sw = geom.pt2mm(spec.line_pt) * (1.8 if n["emphasis"] == "key" else 1.0)
            shape = n["shape"]
            tag = f"node:{n['id']}"
            pad = 1.6
            if shape in {"roundrect", "rect", "instrument", "document", "cylinder"}:
                rx = 0.0 if shape in {"rect", "document"} else max(1.0, min(2.2, r.h * 0.18))
                self.add(prims.rect(r.x, r.y, r.w, r.h, fill=fill, stroke=stroke, sw=sw, rx=rx,
                                    layer="nodes", tag=tag, src=n.get("source", "")))
                if shape == "instrument":
                    self.add(prims.rect(r.x + pad * 0.5, r.y + pad * 0.5, r.w - pad, r.h - pad,
                                        fill="none", stroke=stroke, sw=sw * 0.5, rx=rx * 0.6,
                                        opacity=0.6, layer="nodes", tag=tag + ":inner"))
                if shape == "document":
                    fold = min(3.2, r.w * 0.18, r.h * 0.3)
                    self.add(prims.poly([(r.x1 - fold, r.y), (r.x1, r.y + fold), (r.x1 - fold, r.y + fold)],
                                        closed=True, fill="#FFFFFF", stroke=stroke, sw=sw * 0.7,
                                        layer="nodes", tag=tag + ":fold"))
                if shape == "cylinder":
                    self.add(prims.ellipse(r.cx, r.y + 0.7, r.w / 2, 0.9, fill="#FFFFFF", stroke=stroke,
                                           sw=sw * 0.8, opacity=0.9, layer="nodes", tag=tag + ":top"))
            elif shape in {"ellipse", "cell", "organelle", "nucleus", "vesicle"}:
                self.add(prims.ellipse(r.cx, r.cy, r.w / 2, r.h / 2, fill=fill, stroke=stroke, sw=sw,
                                       layer="nodes", tag=tag, src=n.get("source", "")))
                if shape == "nucleus":
                    self.add(prims.ellipse(r.cx, r.cy, r.w / 2 - 1.4, r.h / 2 - 1.4, fill="none",
                                           stroke=stroke, sw=sw * 0.6, opacity=0.6, layer="nodes",
                                           tag=tag + ":inner"))
            elif shape == "diamond":
                pts = [(r.cx, r.y), (r.x1, r.cy), (r.cx, r.y1), (r.x, r.cy)]
                self.add(prims.poly(pts, closed=True, fill=fill, stroke=stroke, sw=sw, layer="nodes",
                                    tag=tag, src=n.get("source", "")))
            elif shape == "hexagon":
                k = r.w * 0.18
                pts = [(r.x + k, r.y), (r.x1 - k, r.y), (r.x1, r.cy), (r.x1 - k, r.y1),
                       (r.x + k, r.y1), (r.x, r.cy)]
                self.add(prims.poly(pts, closed=True, fill=fill, stroke=stroke, sw=sw, layer="nodes",
                                    tag=tag, src=n.get("source", "")))
            elif shape == "membrane_receptor":
                self._receptor(r, fill, stroke, sw, tag, n)
            elif shape == "channel":
                pts = [(r.x, r.y), (r.x1 - r.w * 0.2, r.y), (r.x1, r.y1), (r.x + r.w * 0.2, r.y1)]
                self.add(prims.poly(pts, closed=True, fill=fill, stroke=stroke, sw=sw, layer="nodes",
                                    tag=tag, src=n.get("source", "")))
            else:
                self.add(prims.rect(r.x, r.y, r.w, r.h, fill=fill, stroke=stroke, sw=sw, rx=1.4,
                                    layer="nodes", tag=tag, src=n.get("source", "")))
                shape = "roundrect"
            self._node_text(n, r, fill, shape)

    def _receptor(self, r: Rect, fill: str, stroke: str, sw: float, tag: str, n: dict) -> None:
        # transmembrane receptor: box plus two bilayer lines crossing it
        self.add(prims.rect(r.x, r.y, r.w, r.h, fill=fill, stroke=stroke, sw=sw, rx=1.2,
                            layer="nodes", tag=tag, src=n.get("source", "")))
        y1 = r.y + r.h * 0.42
        y2 = r.y + r.h * 0.58
        for y in (y1, y2):
            self.add(prims.line(r.x + 0.4, y, r.x1 - 0.4, y, stroke="#8A949E", sw=0.22, dash=False,
                                layer="nodes", tag=tag + ":membrane"))
        # lipid head groups
        step = 1.5
        x = r.x + 0.7
        while x < r.x1 - 0.4:
            self.add(prims.circle(x, y1 - 0.55, 0.28, fill="#B8C2CC", stroke="none", layer="nodes", tag=tag + ":lipid"))
            self.add(prims.circle(x, y2 + 0.55, 0.28, fill="#B8C2CC", stroke="none", layer="nodes", tag=tag + ":lipid"))
            x += step

    def _node_text(self, n: dict, r: Rect, fill: str, shape: str) -> None:
        spec = self.spec
        size = spec.font_pt * (1.06 if n["emphasis"] == "key" else 1.0)
        ink = n["text_color"] or geom.readable_ink(fill)
        if n["emphasis"] == "muted":
            ink = geom.mix(ink, "#FFFFFF", 0.35)
        max_w = r.w - 2.4
        longest = max((geom.text_width_mm(w, size) for w in _words(n["label"])), default=0.0)
        if longest > max_w > 0:
            size = max(size * 0.72, size * max_w / longest)
            if n["emphasis"] == "key":
                size = min(size, spec.font_pt * 1.06)
        lines = geom.wrap_text(n["label"], max_w, size, max_lines=4)
        sub_lines = geom.wrap_text(n["sublabel"], max_w, size * 0.86, max_lines=3) if n["sublabel"] else []
        lh = size * geom.PT2MM * 1.18
        slh = size * 0.86 * geom.PT2MM * 1.12
        total = len(lines) * lh + len(sub_lines) * slh
        y = r.cy - total / 2 + lh / 2
        for i, line in enumerate(lines):
            self.add(prims.text(r.cx, y, line, size=size, anchor="middle", fill=ink,
                                weight="bold" if n["emphasis"] == "key" else "normal",
                                style="italic" if n.get("italic") else "normal",
                                layer="nodes", tag=f"node:label:{n['id']}", src=n.get("source", "")))
            y += lh
        for line in sub_lines:
            self.add(prims.text(r.cx, y + (slh - lh) / 2, line, size=size * 0.86, anchor="middle",
                                fill=geom.mix(ink, "#FFFFFF", 0.15), layer="nodes",
                                tag=f"node:sub:{n['id']}", src=n.get("source", "")))
            y += slh

    def _draw_charts(self) -> None:
        from . import chart as chart_mod
        self.chart_meta = {}
        for c in self.spec.charts:
            rects = self.layout.charts.get(c["id"])
            if not rects:
                continue
            ps, meta = chart_mod.draw_chart(c, rects, self.spec, layer="charts")
            for p in ps:
                self.add(p)
            self.chart_meta[c["id"]] = meta
            for p in ps:
                if p["kind"] in {"rect", "circle"} and p.get("tag", "").startswith(("bar:", "pt:", "cell:", "box:")):
                    self.marks.append({"tag": p["tag"], "chart": c["id"]})

    def _draw_annotations(self) -> None:
        spec = self.spec
        for a in spec.annotations:
            info = self.layout.annotations.get(a["id"])
            if not info:
                continue
            ink = "#333333"
            size = info["size"]
            r = info["rect"]
            if a["kind"] == "callout" and info["target"] in self.layout.nodes:
                t = self.layout.nodes[info["target"]]
                self.add(prims.line(r.x + r.w / 2, r.y1, t.cx, t.y - 0.5, stroke=ink, sw=0.2,
                                    dash=True, layer="annotations", tag=f"ann:{a['id']}"))
            for i, line in enumerate(info["lines"]):
                self.add(prims.text(r.x, r.y + size * geom.PT2MM * (1.0 + i * 1.25), line, size=size,
                                    anchor="start", fill=ink, style="italic" if a["kind"] == "note" else "normal",
                                    layer="annotations", tag=f"ann:{a['id']}", src=a.get("source", "")))
        sb = self.layout.scalebar
        if sb:
            spec_um = sb.get("text") or ""
            r = self.layout.panels.get(sb.get("panel") or next(iter(self.layout.panels), ""))
            if r:
                w = 20.0
                x0, y0 = r.x + 2.0, r.y1 - 2.5
                self.add(prims.line(x0, y0, x0 + w, y0, stroke="#111111", sw=0.6, layer="annotations", tag="scalebar"))
                self.add(prims.line(x0, y0 - 1.0, x0, y0 + 0.6, stroke="#111111", sw=0.6, layer="annotations"))
                self.add(prims.line(x0 + w, y0 - 1.0, x0 + w, y0 + 0.6, stroke="#111111", sw=0.6, layer="annotations"))
                self.add(prims.text(x0 + w / 2, y0 - 1.8, spec_um, size=spec.font_pt * 0.8,
                                    fill="#111111", layer="annotations", tag="scalebar:text"))

    def _draw_legend(self) -> None:
        spec = self.spec
        lr = self.layout.legend_rect
        items = spec.legend["items"]
        if not lr or not items:
            return
        size = self.layout.legend_size
        lh = self.layout.legend_line_h
        if spec.legend["title"]:
            self.add(prims.text(lr.x, lr.y + size * geom.PT2MM * 0.8, spec.legend["title"], size=size,
                                anchor="start", weight="bold", fill="#111111", layer="legend", tag="legend:title"))
        x = lr.x
        y = lr.y + (size * geom.PT2MM * 1.3 if spec.legend["title"] else size * geom.PT2MM * 0.9)
        for row in getattr(self.layout, "legend_rows", []):
            x = lr.x
            for idx, w in row:
                it = items[idx]
                color = it["color"] or style.category_colors(max(1, len(items)))[idx % len(style.category_colors(max(1, len(items))))]
                swatch = it["swatch"]
                if swatch in {"line", "arrow", "dash"}:
                    self.add(prims.line(x, y, x + 4.4, y, stroke=color, sw=0.3 + (0.15 if swatch != "line" else 0),
                                        dash=it["dash"] or swatch == "dash", layer="legend",
                                        marker_end="arrow" if swatch == "arrow" else "",
                                        marker_size=1.5, tag=f"legend:{it['key']}"))
                elif swatch == "bar":
                    self.add(prims.rect(x, y - 1.0, 4.4, 2.0, fill=color, stroke=color, sw=0.1,
                                        layer="legend", tag=f"legend:{it['key']}"))
                elif swatch == "box":
                    self.add(prims.rect(x, y - 1.7, 4.4, 3.4, fill=color, stroke="#555555", sw=0.18,
                                        opacity=0.55, layer="legend", tag=f"legend:{it['key']}"))
                elif swatch == "tbar":
                    self.add(prims.line(x, y, x + 4.4, y, stroke=color, sw=0.3, layer="legend",
                                        marker_end="bar", marker_size=1.5, tag=f"legend:{it['key']}"))
                elif swatch == "gradient":
                    for k in range(6):
                        t = k / 5
                        self.add(prims.rect(x + k * 0.8, y - 1.1, 0.8, 2.2,
                                            fill=style.heat_color(t, 0, 1), stroke="none",
                                            layer="legend", tag=f"legend:{it['key']}"))
                else:
                    rx = 1.2 if it["swatch"] in {"color", "shape", "fill"} else 0.0
                    self.add(prims.rect(x, y - 1.1, 4.4, 2.2, fill=color, stroke="#555555", sw=0.18,
                                        rx=rx, layer="legend", tag=f"legend:{it['key']}"))
                self.add(prims.text(x + 5.8, y, it["label"], size=size, anchor="start", fill="#111111",
                                    layer="legend", tag=f"legend:text:{it['key']}", src=it.get("source", "")))
                x += 5.8 + geom.text_width_mm(it["label"], size) + 4.2
            y += lh

    def _draw_title_caption(self) -> None:
        spec = self.spec
        if self.layout.title_rect:
            tr = self.layout.title_rect
            n = len(self.layout.title_lines)
            size = self.layout.title_size
            lh = size * geom.PT2MM * 1.25
            y = tr.y + lh / 2
            if n == 1:
                y = tr.cy
            for line in self.layout.title_lines:
                self.add(prims.text(spec.width_mm / 2, y, line, size=size, anchor="middle",
                                    weight="bold", fill="#111111", layer="title", tag="title"))
                y += lh
        if self.layout.caption_rect:
            cr = self.layout.caption_rect
            size = self.layout.caption_size
            lh = size * geom.PT2MM * 1.28
            y = cr.y + lh * 0.8
            for line in self.layout.caption_lines:
                self.add(prims.text(cr.x, y, line, size=size, anchor="start", fill="#222222",
                                    layer="caption", tag="caption"))
                y += lh


def _words(text: str) -> list[str]:
    """Wrapping units: words for spaced text, single characters for CJK runs."""
    out, buf = [], ""
    for ch in str(text):
        if ch == " ":
            if buf:
                out.append(buf)
                buf = ""
        elif geom._char_em(ch) >= 0.99:
            if buf:
                out.append(buf)
                buf = ""
            out.append(ch)
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out


def _label_anchor(pts: list[tuple[float, float]]) -> tuple[tuple[float, float], float]:
    # point at the middle of the polyline, by arc length
    segs = []
    total = 0.0
    for i in range(len(pts) - 1):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append(d)
        total += d
    if total == 0:
        return pts[0], 0.0
    half = total / 2
    acc = 0.0
    for i, d in enumerate(segs):
        if acc + d >= half:
            t = (half - acc) / (d or 1)
            x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t
            y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
            return (x, y), 0.0
        acc += d
    return pts[-1], 0.0
