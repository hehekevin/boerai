"""Deterministic layout.

Produces absolute millimetre rectangles for panels, lanes, nodes, charts,
legend, title and caption, plus routed edge polylines.  Layout is computed
from the spec alone, so the same spec always yields the same geometry.
"""
from __future__ import annotations

import math
from typing import Any

from . import geom
from .geom import Rect
from .ir import Spec

MARGIN_MM = 5.0
GUTTER_MM = 5.0
NODE_PAD_X_MM = 2.6
NODE_PAD_Y_MM = 1.8
MIN_NODE_W = 17.0
MIN_NODE_H = 7.0


class Layout:
    def __init__(self, spec: Spec):
        self.spec = spec
        self.warnings: list[str] = []
        self.canvas = Rect(0, 0, spec.width_mm, spec.height_mm)
        self.title_rect: Rect | None = None
        self.caption_rect: Rect | None = None
        self.legend_rect: Rect | None = None
        self.panels: dict[str, Rect] = {}
        self.panel_titles: dict[str, Rect] = {}
        self.lanes: dict[str, Rect] = {}
        self.nodes: dict[str, Rect] = {}
        self.containers: dict[str, Rect] = {}
        self.charts: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.annotations: dict[str, dict] = {}
        self.scalebar: dict | None = None
        self.legend_items_layout: list[dict] = []
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        spec = self.spec
        self._place_title()
        self._place_caption()
        fig_area = self._figure_area()
        self._place_panels(fig_area)
        self._place_legend()
        self.node_areas: dict[str, Rect] = {}
        self.chart_areas: dict[str, Rect] = {}
        for pid, prect in self.panels.items():
            has_nodes = bool(self._panel_nodes(pid))
            charts = [c for c in self.spec.charts if (c["panel"] or "") == (pid or "")]
            if has_nodes and charts:
                ratio = 0.62 if len(charts) == 1 else 0.55
                if prect.w > prect.h * 1.35 and len(charts) == 1:
                    w = prect.w * 0.42
                    self.node_areas[pid] = Rect(prect.x, prect.y, prect.w - w - GUTTER_MM, prect.h)
                    self.chart_areas[pid] = Rect(prect.x1 - w, prect.y, w, prect.h)
                else:
                    h = prect.h * ratio
                    self.node_areas[pid] = Rect(prect.x, prect.y, prect.w, h)
                    self.chart_areas[pid] = Rect(prect.x, prect.y + h + 3.0, prect.w, prect.h - h - 3.0)
            else:
                self.node_areas[pid] = prect
                self.chart_areas[pid] = prect
        for pid in self.panels:
            self._layout_panel_nodes(pid, self.node_areas[pid])
            self._layout_panel_charts(pid, self.chart_areas[pid])
        self._layout_containers()
        self._route_edges()
        self._place_annotations()

    def _place_title(self) -> None:
        spec = self.spec
        if not spec.title:
            return
        size = spec.font_pt * 1.45
        lines = geom.wrap_text(spec.title, spec.width_mm - 2 * MARGIN_MM, size, max_lines=3)
        h = len(lines) * size * geom.PT2MM * 1.25 + 1.4
        self.title_rect = Rect(MARGIN_MM, MARGIN_MM, spec.width_mm - 2 * MARGIN_MM, h)
        self.title_lines = lines
        self.title_size = size

    def _place_caption(self) -> None:
        spec = self.spec
        if not spec.caption:
            self.caption_lines = []
            return
        size = max(5.0, spec.font_pt * 0.92)
        avail = spec.width_mm - 2 * MARGIN_MM
        lines = geom.wrap_text(spec.caption, avail, size, max_lines=14)
        h = len(lines) * size * geom.PT2MM * 1.28 + 2.0
        y = spec.height_mm - MARGIN_MM - h
        self.caption_rect = Rect(MARGIN_MM, y, avail, h)
        self.caption_lines = lines
        self.caption_size = size

    def _figure_area(self) -> Rect:
        spec = self.spec
        top = MARGIN_MM + (self.title_rect.h + 4.6 if self.title_rect else 0)
        bottom = spec.height_mm - MARGIN_MM - (self.caption_rect.h + 2.0 if self.caption_rect else 0)
        return Rect(MARGIN_MM, top, spec.width_mm - 2 * MARGIN_MM, max(10.0, bottom - top))

    def _place_panels(self, area: Rect) -> None:
        spec = self.spec
        panels = spec.panels
        if not panels:
            self.panels[""] = area
            self.panel_titles[""] = Rect(area.x, area.y - 4, area.w, 4)
            return
        explicit = all(p["x_mm"] is not None and p["y_mm"] is not None and p["w_mm"] and p["h_mm"]
                       for p in panels)
        if explicit:
            for p in panels:
                self.panels[p["id"]] = Rect(p["x_mm"], p["y_mm"], p["w_mm"], p["h_mm"])
            return
        n = len(panels)
        if all(p["w_mm"] and p["h_mm"] for p in panels):
            # widths/heights given: stack left-to-right, top aligned
            x = area.x
            for p in panels:
                w = min(p["w_mm"], area.x1 - x)
                h = min(p["h_mm"], area.h)
                self.panels[p["id"]] = Rect(x, area.y, max(8, w), max(8, h))
                x += w + GUTTER_MM
            return
        layout_hint = next((p["layout"] for p in panels if p["layout"]), "")
        if layout_hint in {"row", "horizontal"}:
            cols = n
        elif layout_hint in {"column", "vertical"}:
            cols = 1
        elif n == 1:
            cols = 1
        elif n == 2:
            cols = 2 if area.w / area.h > 1.15 else 1
        elif n == 3:
            cols = 3 if area.w / area.h > 1.5 else 2
        else:
            cols = 2 if area.w / area.h < 2.2 else n
        rows = int(math.ceil(n / cols))
        cw = (area.w - GUTTER_MM * (cols - 1)) / cols
        ch = (area.h - GUTTER_MM * (rows - 1)) / rows
        for i, p in enumerate(panels):
            r, c = divmod(i, cols)
            self.panels[p["id"]] = Rect(area.x + c * (cw + GUTTER_MM), area.y + r * (ch + GUTTER_MM), cw, ch)

    def _place_legend(self) -> None:
        spec = self.spec
        items = spec.legend["items"]
        if not items:
            return
        self.legend_size = max(5.2, spec.font_pt * 0.95)
        size = self.legend_size
        line_h = size * geom.PT2MM * 1.55
        swatch_w = 5.5
        gap = 4.0
        widths = [swatch_w + 1.6 + geom.text_width_mm(it["label"], size) for it in items]
        pos = spec.legend["position"]
        area_w = spec.width_mm - 2 * MARGIN_MM
        if pos == "right":
            col_w = max(widths) + 4
            h = len(items) * line_h + 3
            self.legend_rect = Rect(spec.width_mm - MARGIN_MM - col_w,
                                    self.canvas.h - MARGIN_MM - (self.caption_rect.h + 3 if self.caption_rect else 0) - h,
                                    col_w, h)
            rows = [[(i, widths[i])] for i in range(len(items))]
        else:
            rows: list[list[tuple[int, float]]] = [[]]
            used = 0.0
            for i, w in enumerate(widths):
                need = w + (gap if rows[-1] else 0)
                if used + need > area_w and rows[-1]:
                    rows.append([])
                    used = 0.0
                    need = w
                rows[-1].append((i, w))
                used += need
            h = len(rows) * line_h + 2.4
            y = (self.caption_rect.y - 2.0 - h) if self.caption_rect else (spec.height_mm - MARGIN_MM - h)
            self.legend_rect = Rect(MARGIN_MM, max(MARGIN_MM, y), area_w, h)
        for item in items:
            self.legend_items_layout.append({"key": item["key"], "label": item["label"]})
        self.legend_rows = rows
        self.legend_line_h = line_h
        self.legend_swatch_w = swatch_w
        # legend consumes the bottom strip: shrink figure area accordingly
        if self.legend_rect is not None and pos != "right":
            for pid in list(self.panels):
                r = self.panels[pid]
                if r.y1 > self.legend_rect.y - 1.0:
                    new_h = max(10.0, self.legend_rect.y - 1.0 - r.y)
                    self.panels[pid] = Rect(r.x, r.y, r.w, new_h)
        if pos == "right":
            for pid in list(self.panels):
                r = self.panels[pid]
                if r.x1 > self.legend_rect.x - 1.0:
                    self.panels[pid] = Rect(r.x, r.y, max(10.0, self.legend_rect.x - 1.0 - r.x), r.h)

    # ------------------------------------------------------------- nodes
    def _panel_nodes(self, pid: str) -> list[dict]:
        return [n for n in self.spec.nodes if (n["panel"] or "") == (pid or "")]

    def _panel_lanes(self, pid: str) -> list[dict]:
        lanes = [l for l in self.spec.lanes if (l["panel"] or "") == (pid or "")]
        if not lanes and self.spec.lanes and pid == "":
            lanes = list(self.spec.lanes)
        return sorted(lanes, key=lambda l: l["order"])

    def _layer_index(self, nodes: list[dict], edges: list[dict]) -> dict[str, int]:
        """Longest-path layering on the DAG obtained by dropping back edges.

        Feedback links (e.g. ERK -> SOS) are back edges: keeping them in the
        layering would push their target one column too far right and collide
        with its neighbours.  They are still drawn, just not layered.
        """
        ids = {n["id"] for n in nodes}
        succ: dict[str, list[str]] = {i: [] for i in ids}
        pairs = []
        for e in edges:
            if e["from"] in ids and e["to"] in ids and e["from"] != e["to"] \
                    and e["type"] not in {"contain", "part_of"}:
                if e["to"] not in succ[e["from"]]:
                    succ[e["from"]].append(e["to"])
                    pairs.append((e["from"], e["to"]))
        state: dict[str, int] = {}
        back: set[tuple[str, str]] = set()
        order: list[str] = []

        def dfs(u: str) -> None:
            state[u] = 1
            for v in succ[u]:
                if state.get(v, 0) == 1:
                    back.add((u, v))
                    continue
                if state.get(v, 0) == 0:
                    dfs(v)
            state[u] = 2
            order.append(u)

        for n in nodes:
            if state.get(n["id"], 0) == 0:
                dfs(n["id"])
        layer = {i: 0 for i in ids}
        for u in reversed(order):
            for v in succ[u]:
                if (u, v) in back:
                    continue
                if layer[v] < layer[u] + 1:
                    layer[v] = layer[u] + 1
        used = sorted(set(layer.values()))
        remap = {v: i for i, v in enumerate(used)}
        self.back_edges = {f"{a}->{b}" for a, b in back}
        return {k: remap[v] for k, v in layer.items()}

    def _node_size(self, node: dict, avail_w: float) -> tuple[float, float]:
        spec = self.spec
        size = spec.font_pt * (1.06 if node["emphasis"] == "key" else 1.0)
        max_text_w = max(6.5, min(avail_w * 0.88, 46.0))
        lines = geom.wrap_text(node["label"], max_text_w, size, max_lines=4) or [node["label"]]
        w_text = max([geom.text_width_mm(l, size) for l in lines] + [0])
        sub_lines = []
        if node["sublabel"]:
            sub_lines = geom.wrap_text(node["sublabel"], max_text_w, size * 0.86, max_lines=3)
            w_text = max(w_text, max([geom.text_width_mm(l, size * 0.86) for l in sub_lines] + [0]))
        w = max(min(MIN_NODE_W, avail_w * 0.80), w_text + 2 * NODE_PAD_X_MM)
        w = min(w, max(9.0, avail_w * 0.86))
        line_h = size * geom.PT2MM * 1.18
        h = len(lines) * line_h + len(sub_lines) * size * 0.86 * geom.PT2MM * 1.15 + 2 * NODE_PAD_Y_MM
        h = max(MIN_NODE_H, h)
        if node["shape"] in {"membrane_receptor"}:
            h = max(h, 11.0)
        if node["shape"] in {"cell", "nucleus", "organelle"}:
            w = max(w, 22.0)
            h = max(h, 12.0)
        if node["w_mm"]:
            w = node["w_mm"]
        if node["h_mm"]:
            h = node["h_mm"]
        return w, h

    def _layout_panel_nodes(self, pid: str, prect: Rect) -> None:
        spec = self.spec
        nodes = self._panel_nodes(pid)
        if not nodes:
            return
        lanes = self._panel_lanes(pid)
        pad = 2.4
        edges = [e for e in spec.edges if e["from"] in {n["id"] for n in nodes}
                 and e["to"] in {n["id"] for n in nodes}]
        layer = self._layer_index(nodes, edges)
        ncol = max(layer.values(), default=0) + 1
        lane_ids = [l["id"] for l in lanes]

        # grid: lanes fix one row per lane; without lanes a long chain wraps in
        # a serpentine so that a 8-column chain still fits a narrow panel
        if lanes:
            cols_grid, rows_grid = ncol, len(lanes)
        else:
            target = 27.0 if len(nodes) > 4 else 34.0
            vertical = (len(nodes) <= 2) or (
                ncol >= 4 and prect.h / max(1.0, prect.w) > 0.85 and len(nodes) <= 9)
            if vertical:
                cols_grid = 1
                rows_grid = max(ncol, len(nodes))
            else:
                cols_grid = max(2, min(ncol, int(max(1.0, prect.w) / target)))
                cols_grid = min(cols_grid, ncol)
                rows_grid = int(math.ceil(ncol / cols_grid))

        max_reserve = 0.0
        for l in lanes:
            if l["label"]:
                max_reserve = max(max_reserve, min(16.0, geom.text_width_mm(l["label"], spec.font_pt * 0.82) * 0.42))
        col_w = (prect.w - 2 * pad - max_reserve - 1.2) / max(1, cols_grid)
        sizes = {n["id"]: self._node_size(n, col_w) for n in nodes}

        def grid_of(nid: str) -> tuple[int, int]:
            lay = layer.get(nid, 0)
            r, c = divmod(lay, cols_grid)
            if r % 2 == 1:
                c = cols_grid - 1 - c
            return r, c

        by_lane: dict[str, list[dict]] = {}
        for n in nodes:
            lane_id = n["lane"] if n["lane"] in lane_ids else ("" if not lanes else lanes[0]["id"])
            n["_lane"] = lane_id
            by_lane.setdefault(lane_id, []).append(n)

        lane_rects: dict[str, Rect] = {}
        if lanes:
            need: dict[str, float] = {}
            for lid, lnodes in by_lane.items():
                counts: dict[int, int] = {}
                for n in lnodes:
                    counts[layer.get(n["id"], 0)] = counts.get(layer.get(n["id"], 0), 0) + 1
                rows = max(counts.values(), default=1)
                hmax = max(sizes[n["id"]][1] for n in lnodes)
                need[lid] = rows * (hmax + 1.8) + 3.0
            avail_h = prect.h - pad * 2
            explicit = sum((l["h_mm"] or 0) for l in lanes)
            if explicit > 0:
                weights = [((l["h_mm"] or 0) / explicit) * avail_h for l in lanes]
                scale = avail_h / sum(weights) if sum(weights) > 0 else 1.0
                heights = [w * scale for w in weights]
            else:
                base = avail_h / len(lanes)
                heights = [max(need.get(l["id"], 8.0), base) for l in lanes]
                tot = sum(heights)
                heights = [h * avail_h / tot for h in heights] if tot else heights
            y = prect.y + pad
            for l, hh in zip(lanes, heights):
                lane_rects[l["id"]] = Rect(prect.x + pad, y, prect.w - 2 * pad, hh)
                self.lanes[l["id"]] = Rect(prect.x + pad * 0.4, y, prect.w - pad * 0.8, hh)
                y += hh
        else:
            lane_rects[""] = Rect(prect.x + pad, prect.y + pad, prect.w - 2 * pad, prect.h - 2 * pad)

        for lane_id, lnodes in by_lane.items():
            band = lane_rects.get(lane_id) or prect
            label_reserve = 0.0
            if lane_id and spec.lane_by_id.get(lane_id, {}).get("label"):
                label_reserve = min(16.0, geom.text_width_mm(spec.lane_by_id[lane_id]["label"],
                                                             spec.font_pt * 0.82) * 0.42)
            inner = Rect(band.x + label_reserve, band.y + 1.2,
                         band.w - label_reserve - 1.2, max(4.0, band.h - 2.4))
            row_h = inner.h / max(1, rows_grid) if not lanes else inner.h
            groups: dict[tuple[int, int], list[dict]] = {}
            for n in lnodes:
                if lanes:
                    key = (0, layer.get(n["id"], 0))
                else:
                    key = grid_of(n["id"])
                groups.setdefault(key, []).append(n)
            for (gr, gc), gnodes in groups.items():
                gnodes.sort(key=lambda n: (n["order"] if n["order"] is not None else 0, n["label"]))
                csizes = [sizes[n["id"]] for n in gnodes]
                total_h = sum(s[1] for s in csizes) + 1.8 * (len(gnodes) - 1)
                if lanes:
                    band_top, band_h = inner.y, inner.h
                else:
                    band_top, band_h = inner.y + gr * row_h, row_h
                if total_h > band_h and len(gnodes) > 1:
                    gap = max(0.6, (band_h - sum(s[1] for s in csizes)) / (len(gnodes) - 1))
                    total_h = sum(s[1] for s in csizes) + gap * (len(gnodes) - 1)
                else:
                    gap = 1.8
                y = band_top + (band_h - total_h) / 2
                y = max(band_top, min(y, band_top + band_h - total_h))
                for n, (w, h) in zip(gnodes, csizes):
                    if n["x_mm"] is not None:
                        x = n["x_mm"]
                    else:
                        cx = inner.x + col_w * gc + col_w / 2
                        x = cx - w / 2
                        x = max(inner.x, min(x, inner.x1 - w))
                    yy = n["y_mm"] if n["y_mm"] is not None else y
                    self.nodes[n["id"]] = Rect(x, yy, w, h)
                    y += h + gap

        for lane_id, lnodes in by_lane.items():
            self._separate(lnodes, lane_rects.get(lane_id) or prect, prect)
        for nid, r in list(self.nodes.items()):
            if nid in {n["id"] for n in nodes}:
                dy = 0.0
                if r.y < prect.y + 0.8:
                    dy = prect.y + 0.8 - r.y
                elif r.y1 > prect.y1 - 0.4:
                    dy = prect.y1 - 0.4 - r.y1
                if dy:
                    self.nodes[nid] = Rect(r.x, r.y + dy, r.w, r.h)

    def _separate(self, lnodes: list[dict], band: Rect, prect: Rect) -> None:
        """Resolve the rare residual overlaps inside one grid cell.

        Column widths are capped at 86 % of the column pitch, so nodes in
        different columns cannot collide; only stacked or explicitly placed
        nodes can, and those are pushed apart vertically inside their band.
        """
        for _ in range(5):
            moved = False
            items = [self.nodes[n["id"]] for n in lnodes if n["id"] in self.nodes]
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    a, b = items[i], items[j]
                    if not a.intersects(b, tol=0.1):
                        continue
                    if abs(a.cx - b.cx) > 0.55 * max(a.w, b.w):
                        continue  # different columns: leave the grid alone
                    lower, upper = (a, b) if a.y <= b.y else (b, a)
                    need = lower.y1 + 0.8 - upper.y
                    if upper.y1 + need <= band.y1:
                        upper.y += need
                        moved = True
                    elif lower.y - need >= band.y:
                        lower.y -= need
                        moved = True
            if not moved:
                break
    def _layout_panel_charts(self, pid: str, prect: Rect) -> None:
        charts = [c for c in self.spec.charts if (c["panel"] or "") == (pid or "")]
        if not charts:
            return
        top = prect.y
        avail_h = max(12.0, prect.y1 - top - 1.0)
        n = len(charts)
        if n > 1:
            w = (prect.w - GUTTER_MM * (n - 1)) / n
            for i, c in enumerate(charts):
                rect = Rect(prect.x + i * (w + GUTTER_MM), top, w, avail_h)
                self.charts[c["id"]] = self._chart_rects(c, rect)
        else:
            c = charts[0]
            rect = Rect(prect.x, top, prect.w, avail_h)
            self.charts[c["id"]] = self._chart_rects(c, rect)

    def _chart_rects(self, c: dict, rect: Rect) -> dict:
        if c["x_mm"] is not None and c["y_mm"] is not None:
            rect = Rect(c["x_mm"], c["y_mm"], c["w_mm"] or rect.w, c["h_mm"] or rect.h)
        elif c["w_mm"] and c["h_mm"]:
            rect = Rect(rect.x, rect.y, c["w_mm"], c["h_mm"])
        size = self.spec.font_pt * 0.92
        title_h = (size * geom.PT2MM * 1.5) if c["title"] else 0.0
        legend_h = 0.0
        if c.get("legend"):
            legend_h = size * geom.PT2MM * 1.6
        left = 0.0 if c["type"] in {"heatmap"} else 13.0
        if c["type"] in {"heatmap"}:
            left = 15.0
        bottom = 9.0
        if c["type"] in {"bar"} and any_category_rotated(c):
            bottom = 13.0
        plot = Rect(rect.x + left, rect.y + title_h + 1.0,
                    max(6.0, rect.w - left - 3.0),
                    max(6.0, rect.h - title_h - bottom - legend_h - 1.0))
        return {"rect": rect, "plot": plot, "title_h": title_h, "legend_h": legend_h,
                "xlabel_h": bottom, "cbar": bool(c.get("colorbar"))}

    def _layout_containers(self) -> None:
        spec = self.spec
        for c in spec.containers:
            rects = [self.nodes[m] for m in c["members"] if m in self.nodes]
            if not rects:
                if c["label"]:
                    self.warnings.append(f"container {c['id']} has no laid-out members")
                continue
            r = rects[0]
            for other in rects[1:]:
                r = r.union(other)
            pad = 2.0 if c["relation"] == "contains" else 1.4
            top_extra = 4.0 if c["label"] else 0.0
            self.containers[c["id"]] = Rect(r.x - pad, r.y - pad - top_extra, r.w + 2 * pad, r.h + 2 * pad + top_extra)
        # a container must never swallow a non-member: nudge intruders out
        self.container_conflicts: list[str] = []
        for _ in range(4):
            changed = False
            for c in spec.containers:
                r = self.containers.get(c["id"])
                if not r:
                    continue
                members = set(c["members"])
                for nid, nr in list(self.nodes.items()):
                    if nid in members:
                        continue
                    if not r.intersects(nr, tol=0.2):
                        continue
                    top_bound = MARGIN_MM
                    for m in c["members"]:
                        mn = self.spec.node_by_id.get(m) or {}
                        pa = self.node_areas.get(mn.get("panel") or "")
                        if pa is not None:
                            top_bound = max(top_bound, pa.y + 0.6)
                    above = Rect(nr.x, r.y - nr.h - 1.4, nr.w, nr.h)
                    below = Rect(nr.x, r.y1 + 1.4, nr.w, nr.h)
                    if above.y >= top_bound and not any(
                            above.intersects(o, tol=0.2) for k, o in self.nodes.items() if k != nid):
                        self.nodes[nid] = above
                        changed = True
                    elif below.intersects(r) is False and not any(
                            below.intersects(o, tol=0.2) for k, o in self.nodes.items() if k != nid):
                        self.nodes[nid] = below
                        changed = True
                    else:
                        self.container_conflicts.append(f"{c['id']}~{nid}")
            if not changed:
                break
        for cid, r in self.containers.items():
            for nid, nr in self.nodes.items():
                if nid not in next(c2["members"] for c2 in spec.containers if c2["id"] == cid) \
                        and r.intersects(nr, tol=0.2):
                    if f"{cid}~{nid}" not in self.container_conflicts:
                        self.container_conflicts.append(f"{cid}~{nid}")

    # ------------------------------------------------------------- edges
    def _route_edges(self) -> None:
        spec = self.spec
        for e in spec.edges:
            a = self.nodes.get(e["from"])
            b = self.nodes.get(e["to"])
            if not a or not b:
                continue
            poly = self._route(a, b, e)
            self.edges[e["id"]] = {"poly": poly, "from": e["from"], "to": e["to"]}
        # record crossing count for the report
        self.edge_crossings = count_crossings(self.edges)
        self.edge_labels: dict[str, tuple[float, float]] = {}
        self._place_edge_labels()

    def _place_edge_labels(self) -> None:
        spec = self.spec
        occupied = [r for r in self.nodes.values()]
        for e in spec.edges:
            if not e["label"]:
                continue
            routed = self.edges.get(e["id"])
            if not routed:
                continue
            size = spec.font_pt * 0.78
            w = geom.text_width_mm(e["label"], size) + 1.4
            h = size * geom.PT2MM * 1.4
            base = label_anchor(routed["poly"])
            best = None
            for dx, dy in ((0, 0), (0, -h - 0.6), (0, h + 0.6), (w / 2 + 1.2, 0), (-w / 2 - 1.2, 0),
                           (0, -2 * h - 1.2), (0, 2 * h + 1.2)):
                cand = Rect(base[0] - w / 2 + dx, base[1] - h / 2 + dy, w, h)
                hits = sum(1 for r in occupied if r.intersects(cand, tol=0.2))
                if hits == 0:
                    best = cand
                    break
                if best is None or hits < best[0]:
                    best = (hits, cand)
            rect = best[1] if isinstance(best, tuple) and isinstance(best[0], int) else best
            if isinstance(rect, tuple):
                rect = rect[1]
            self.edge_labels[e["id"]] = (rect.cx, rect.cy)
            occupied.append(rect)

    def _route(self, a: Rect, b: Rect, e: dict) -> list[tuple[float, float]]:
        if e["waypoints"]:
            pts = [(a.cx, a.cy)]
            for wp in e["waypoints"]:
                if isinstance(wp, dict):
                    pts.append((float(wp.get("x_mm", a.cx)), float(wp.get("y_mm", a.cy))))
                elif isinstance(wp, (list, tuple)) and len(wp) >= 2:
                    pts.append((float(wp[0]), float(wp[1])))
            pts.append((b.cx, b.cy))
            pts[0] = geom.clip_to_rect(a, a.cx, a.cy, pts[1][0], pts[1][1], pad=0.6)
            pts[-1] = geom.clip_to_rect(b, b.cx, b.cy, pts[-2][0], pts[-2][1], pad=0.6, far=False)
            return pts
        if abs(a.cx - b.cx) < 1e-6 and abs(a.cy - b.cy) < 1e-6:
            return [(a.cx, a.cy), (b.cx, b.cy)]
        p0 = geom.clip_to_rect(a, a.cx, a.cy, b.cx, b.cy, pad=0.6)
        p1 = geom.clip_to_rect(b, b.cx, b.cy, a.cx, a.cy, pad=0.6, far=False)
        if e["route"] == "orthogonal":
            midx = (p0[0] + p1[0]) / 2
            return [p0, (midx, p0[1]), (midx, p1[1]), p1]
        # avoid passing through an unrelated node: detour around its side
        blockers = [r for nid, r in self.nodes.items() if nid not in (e["from"], e["to"])
                    and segment_hits(p0, p1, r)]
        if not blockers:
            return [p0, p1]
        br = blockers[0]
        for other in blockers[1:]:
            br = br.union(other)
        left_x = br.x - 2.6
        right_x = br.x1 + 2.6
        room_left = left_x - self.canvas.x
        room_right = self.canvas.x1 - right_x
        sx = left_x if room_left >= room_right else right_x
        sx = max(self.canvas.x + 1.5, min(sx, self.canvas.x1 - 1.5))
        out_y = p0[1]
        in_y = p1[1]
        return [p0, (sx, out_y), (sx, in_y), p1]

    def _place_annotations(self) -> None:
        spec = self.spec
        for a in spec.annotations:
            if a["kind"] == "scalebar":
                self.scalebar = a
                continue
            size = a["size_pt"] or spec.font_pt * 0.9
            target = self.nodes.get(a["target"]) if a["target"] else None
            if a["x_mm"] is not None and a["y_mm"] is not None:
                x, y = a["x_mm"], a["y_mm"]
            elif target is not None:
                x, y = target.cx, target.y - 3.2
            else:
                x, y = MARGIN_MM + 2, MARGIN_MM + 2
            lines = geom.wrap_text(a["text"], 40.0, size, max_lines=4)
            w = max([geom.text_width_mm(l, size) for l in lines] + [6])
            h = len(lines) * size * geom.PT2MM * 1.25
            self.annotations[a["id"]] = {"rect": Rect(x, y, w, h), "lines": lines, "size": size,
                                         "align": a["align"], "target": a["target"]}

    # ------------------------------------------------------------- helpers
    def content_bottom(self) -> float:
        ys = [r.y1 for r in self.nodes.values()]
        ys += [v["rect"].y1 for v in self.charts.values()]
        ys += [r.y1 for r in self.containers.values()]
        ys += [r.y1 for r in self.lanes.values()]
        if self.legend_rect:
            ys.append(self.legend_rect.y1)
        if self.caption_rect:
            ys.append(self.caption_rect.y1)
        return max(ys) if ys else self.canvas.y1

    def content_core_bottom(self) -> float:
        ys = [r.y1 for r in self.nodes.values()]
        ys += [v["rect"].y1 for v in self.charts.values()]
        ys += [r.y1 for r in self.containers.values()]
        ys += [r.y1 for r in self.lanes.values()]
        if self.title_rect:
            ys.append(self.title_rect.y1)
        return max(ys) if ys else 60.0

    def node_center(self, nid: str) -> tuple[float, float]:
        r = self.nodes[nid]
        return r.cx, r.cy


def label_anchor(pts: list[tuple[float, float]]) -> tuple[float, float]:
    segs, total = [], 0.0
    for i in range(len(pts) - 1):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append(d)
        total += d
    if total == 0:
        return pts[0]
    half, acc = total / 2, 0.0
    for i, d in enumerate(segs):
        if acc + d >= half:
            t = (half - acc) / (d or 1)
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                    pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        acc += d
    return pts[-1]


def any_category_rotated(c: dict) -> bool:
    if c.get("xtick_rotate"):
        return True
    cats = [r.get(c["x"]) for r in c.get("rows") or [] if isinstance(r, dict)]
    return any(isinstance(v, str) and geom.text_width_mm(v, 6.0) > 7.0 for v in cats)


def devx(r: Rect) -> float:  # pragma: no cover - placeholder for defensive branch
    return r.cx


def segment_hits(p0: tuple[float, float], p1: tuple[float, float], r: Rect) -> bool:
    x0, y0 = p0
    x1, y1 = p1
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if r.x + 0.4 < x < r.x1 - 0.4 and r.y + 0.4 < y < r.y1 - 0.4:
            return True
    return False


def count_crossings(edges: dict[str, dict]) -> int:
    segs = []
    for eid, e in edges.items():
        pts = e["poly"]
        for i in range(len(pts) - 1):
            segs.append((eid, pts[i], pts[i + 1]))
    n = 0
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if segs[i][0] == segs[j][0]:
                continue
            if _seg_intersect(segs[i][1], segs[i][2], segs[j][1], segs[j][2]):
                n += 1
    return n


def _seg_intersect(p1, p2, p3, p4) -> bool:
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))
