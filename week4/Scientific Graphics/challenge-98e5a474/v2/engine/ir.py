"""Figure specification: loading, defaults, validation.

The spec is the single source of truth for a figure.  Rendering never invents
content: every label, number and relation in the drawing comes from the spec,
and every spec element may carry an evidence id that points at a verbatim
source quote.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from . import geom

# --- style presets ----------------------------------------------------------
PRESETS: dict[str, dict[str, Any]] = {
    "nature_single": {"width_mm": 89, "height_mm": 70, "font_pt": 5.5, "line_pt": 0.5, "label_pt": 6.0},
    "nature_1_5": {"width_mm": 120, "height_mm": 90, "font_pt": 6.0, "line_pt": 0.5, "label_pt": 7.0},
    "nature_double": {"width_mm": 183, "height_mm": 120, "font_pt": 6.5, "line_pt": 0.6, "label_pt": 7.5},
    "science_double": {"width_mm": 175, "height_mm": 110, "font_pt": 6.5, "line_pt": 0.6, "label_pt": 7.5},
    "elsevier_double": {"width_mm": 190, "height_mm": 130, "font_pt": 7.0, "line_pt": 0.6, "label_pt": 8.0},
    "thesis_a4": {"width_mm": 160, "height_mm": 110, "font_pt": 8.0, "line_pt": 0.7, "label_pt": 9.0},
    "grant_slide": {"width_mm": 230, "height_mm": 130, "font_pt": 9.0, "line_pt": 0.8, "label_pt": 10.0},
    "ga_landscape": {"width_mm": 160, "height_mm": 80, "font_pt": 7.0, "line_pt": 0.7, "label_pt": 8.0},
}

KIND_ALIASES = {
    "relationship_schematic": "relationship_schematic",
    "schematic": "relationship_schematic",
    "relationship": "relationship_schematic",
    "concept": "relationship_schematic",
    "data_chart": "data_chart",
    "chart": "data_chart",
    "plot": "data_chart",
    "mechanism_pathway": "mechanism_pathway",
    "mechanism": "mechanism_pathway",
    "pathway": "mechanism_pathway",
    "apparatus_route": "apparatus_route",
    "apparatus": "apparatus_route",
    "technical_route": "apparatus_route",
    "workflow": "apparatus_route",
    "graphical_abstract": "graphical_abstract",
    "graphical abstract": "graphical_abstract",
    "ga": "graphical_abstract",
}

# Relation semantics: canonical type -> (arrow ending, dash, default label, meaning)
RELATION_TYPES: dict[str, dict[str, Any]] = {
    "activate": {"end": "arrow", "dash": False, "zh": "激活", "en": "activates"},
    "promote": {"end": "arrow", "dash": False, "zh": "促进", "en": "promotes"},
    "upregulate": {"end": "arrow", "dash": False, "zh": "上调", "en": "upregulates"},
    "inhibit": {"end": "bar", "dash": False, "zh": "抑制", "en": "inhibits"},
    "repress": {"end": "bar", "dash": False, "zh": "阻遏", "en": "represses"},
    "bind": {"end": "diamond", "dash": False, "zh": "结合", "en": "binds"},
    "complex": {"end": "none", "dash": False, "zh": "组成复合物", "en": "forms complex"},
    "modify": {"end": "arrow", "dash": True, "zh": "修饰", "en": "modifies"},
    "phosphorylate": {"end": "arrow", "dash": True, "zh": "磷酸化", "en": "phosphorylates"},
    "transport": {"end": "arrow", "dash": False, "zh": "转运", "en": "transports"},
    "translocate": {"end": "arrow", "dash": True, "zh": "易位", "en": "translocates"},
    "secrete": {"end": "arrow", "dash": False, "zh": "分泌", "en": "secretes"},
    "flow": {"end": "arrow", "dash": False, "zh": "流向", "en": "flows to"},
    "sequence": {"end": "arrow", "dash": False, "zh": "下一步", "en": "then"},
    "contain": {"end": "none", "dash": False, "zh": "包含", "en": "contains"},
    "part_of": {"end": "none", "dash": True, "zh": "属于", "en": "part of"},
    "catalyze": {"end": "arrow", "dash": False, "zh": "催化", "en": "catalyzes"},
    "convert": {"end": "arrow", "dash": False, "zh": "转化", "en": "converts"},
    "connect": {"end": "none", "dash": False, "zh": "连接", "en": "connects"},
    "signal": {"end": "arrow", "dash": True, "zh": "信号", "en": "signals to"},
    "associate": {"end": "none", "dash": True, "zh": "关联", "en": "associates with"},
}

_TYPE_SYNONYMS = {
    "activates": "activate", "activation": "activate", "promotes": "promote",
    "promotion": "promote", "induces": "activate", "up-regulates": "upregulate",
    "inhibits": "inhibit", "inhibition": "inhibit", "suppresses": "inhibit",
    "represses": "repress", "blocks": "inhibit", "binds": "bind", "binding": "bind",
    "phosphorylates": "phosphorylate", "phosphorylation": "phosphorylate",
    "transports": "transport", "transport": "transport", "moves to": "translocate",
    "flows to": "flow", "then": "sequence", "next": "sequence", "contains": "contain",
    "part of": "part_of", "catalyzes": "catalyze", "converts": "convert",
    "connects": "connect", "signals": "signal", "associates": "associate",
}

SHAPES = {
    "roundrect", "rect", "ellipse", "diamond", "hexagon", "cylinder",
    "membrane_receptor", "cell", "organelle", "nucleus", "vesicle", "channel",
    "instrument", "flask", "document", "person", "database",
}

DEFAULT_FONT_STACK = ["Noto Sans CJK SC", "Noto Sans CJK JP", "Source Han Sans SC",
                      "Droid Sans Fallback", "Noto Sans", "DejaVu Sans", "Arial"]


class Issue(dict):
    def __init__(self, level: str, code: str, message: str, where: str = "", fix: str = ""):
        super().__init__(level=level, code=code, message=message, where=where, fix=fix)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class Spec:
    def __init__(self, data: dict, base_dir: str = "."):
        self.raw = data
        self.base_dir = os.path.abspath(base_dir)
        self.issues: list[Issue] = []
        self.case_id = str(data.get("case_id") or "unknown-case")
        self.figure_id = str(data.get("figure_id") or "figure")
        kind = str(data.get("figure_kind") or data.get("kind") or "").strip().lower()
        self.figure_kind = KIND_ALIASES.get(kind, kind or "relationship_schematic")
        self.title = str(data.get("title") or "").strip()
        self.subtitle = str(data.get("subtitle") or "").strip()
        self.caption = str(data.get("caption") or "").strip()

        canvas = dict(data.get("canvas") or {})
        preset_name = str(canvas.get("preset") or "").strip().lower()
        if not preset_name:
            from .profiles import default_canvas
            prof = default_canvas(self.figure_kind)
            preset_name = str(prof.get("preset") or "nature_double")
            canvas.setdefault("dpi", prof.get("dpi", 600))
        preset = PRESETS.get(preset_name, {})
        self.width_mm = float(canvas.get("width_mm") or preset.get("width_mm") or 183)
        self.height_mm = float(canvas.get("height_mm") or preset.get("height_mm") or 120)
        self.dpi = int(canvas.get("dpi") or 600)
        self.font_pt = float(canvas.get("font_pt") or preset.get("font_pt") or 6.5)
        self.line_pt = float(canvas.get("line_pt") or preset.get("line_pt") or 0.6)
        self.preset = preset_name or "custom"
        self.background = str(canvas.get("background") or "#FFFFFF")
        self.color_mode = str(canvas.get("color_mode") or "RGB").upper()
        self.font_stack = _as_list(canvas.get("font_stack")) or list(DEFAULT_FONT_STACK)

        self.panels = [self._norm_panel(p, i) for i, p in enumerate(_as_list(data.get("panels")))]
        self.lanes = [self._norm_lane(l, i) for i, l in enumerate(_as_list(data.get("lanes")))]
        self.nodes = [self._norm_node(n, i) for i, n in enumerate(_as_list(data.get("nodes")))]
        self.containers = [self._norm_container(c, i) for i, c in enumerate(_as_list(data.get("containers")))]
        self.edges = [self._norm_edge(e, i) for i, e in enumerate(_as_list(data.get("edges")))]
        self.charts = [self._norm_chart(c, i) for i, c in enumerate(_as_list(data.get("charts")))]
        self.annotations = [self._norm_annotation(a, i) for i, a in enumerate(_as_list(data.get("annotations")))]
        self.legend = self._norm_legend(data.get("legend"))
        self.evidence: dict[str, dict] = {}
        for key, val in (data.get("evidence") or {}).items():
            if isinstance(val, dict):
                self.evidence[str(key)] = {
                    "source": str(val.get("source") or ""),
                    "locator": str(val.get("locator") or ""),
                    "quote": str(val.get("quote") or ""),
                }
        self.sources = [self._norm_source(s, i) for i, s in enumerate(_as_list(data.get("sources")))]
        self.uncertainty = [str(u) for u in _as_list(data.get("uncertainty")) if str(u).strip()]
        self.changes = [c for c in _as_list(data.get("changes")) if c]
        self.style = dict(data.get("style") or {})

        if not self.panels:
            # a spec without explicit panels is a single-panel figure: panel ids
            # on elements are advisory only and must not hide content
            for coll in (self.nodes, self.charts, self.lanes, self.containers):
                for item in coll:
                    item["panel"] = ""
        self._index()
        self._validate()

    # -- normalisers ---------------------------------------------------------
    def _norm_panel(self, p: Any, i: int) -> dict:
        p = dict(p or {})
        return {
            "id": str(p.get("id") or chr(65 + i)),
            "title": str(p.get("title") or ""),
            "x_mm": _opt_float(p.get("x_mm")),
            "y_mm": _opt_float(p.get("y_mm")),
            "w_mm": _opt_float(p.get("w_mm")),
            "h_mm": _opt_float(p.get("h_mm")),
            "columns": int(p.get("columns") or 0),
            "layout": str(p.get("layout") or p.get("kind") or ""),
        }

    def _norm_lane(self, l: Any, i: int) -> dict:
        l = dict(l or {})
        return {
            "id": str(l.get("id") or f"lane{i}"),
            "label": str(l.get("label") or ""),
            "panel": str(l.get("panel") or ""),
            "y_mm": _opt_float(l.get("y_mm")),
            "h_mm": _opt_float(l.get("h_mm")),
            "fill": str(l.get("fill") or ""),
            "order": float(l.get("order") if l.get("order") is not None else i),
        }

    def _norm_node(self, n: Any, i: int) -> dict:
        n = dict(n or {})
        label = str(n.get("label") or n.get("name") or n.get("id") or "").strip()
        node = {
            "id": str(n.get("id") or _slug(label) or f"n{i}"),
            "label": label,
            "sublabel": str(n.get("sublabel") or n.get("note") or "").strip(),
            "class": str(n.get("class") or n.get("type") or "entity").strip().lower(),
            "shape": str(n.get("shape") or "").strip().lower(),
            "panel": str(n.get("panel") or ""),
            "lane": str(n.get("lane") or ""),
            "group": str(n.get("group") or n.get("container") or ""),
            "order": _opt_float(n.get("order")),
            "x_mm": _opt_float(n.get("x_mm")),
            "y_mm": _opt_float(n.get("y_mm")),
            "w_mm": _opt_float(n.get("w_mm")),
            "h_mm": _opt_float(n.get("h_mm")),
            "fill": str(n.get("fill") or ""),
            "stroke": str(n.get("stroke") or ""),
            "text_color": str(n.get("text_color") or ""),
            "emphasis": str(n.get("emphasis") or ""),
            "source": str(n.get("source") or n.get("evidence") or ""),
            "note": str(n.get("note") or ""),
            "icon": str(n.get("icon") or ""),
            "italic": bool(n.get("italic") or False),
        }
        if not node["shape"]:
            node["shape"] = _default_shape(node["class"])
        return node

    def _norm_container(self, c: Any, i: int) -> dict:
        c = dict(c or {})
        return {
            "id": str(c.get("id") or f"grp{i}"),
            "label": str(c.get("label") or ""),
            "members": [str(m) for m in _as_list(c.get("members"))],
            "panel": str(c.get("panel") or ""),
            "relation": str(c.get("relation") or "contains"),
            "fill": str(c.get("fill") or ""),
            "stroke": str(c.get("stroke") or ""),
            "source": str(c.get("source") or ""),
        }

    def _norm_edge(self, e: Any, i: int) -> dict:
        e = dict(e or {})
        frm = e.get("from", e.get("source_id", e.get("src")))
        to = e.get("to", e.get("target", e.get("dst")))
        rtype = str(e.get("type") or e.get("relation") or "activate").strip().lower()
        rtype = _TYPE_SYNONYMS.get(rtype, rtype)
        if rtype not in RELATION_TYPES:
            base = rtype.replace(" ", "_")
            if base in RELATION_TYPES:
                rtype = base
            else:
                self.issues.append(Issue("warn", "EDGE_TYPE_UNKNOWN",
                                         f"unknown relation type '{rtype}', drawn as 'activate'",
                                         f"edges[{i}]", "use one of: " + ", ".join(sorted(RELATION_TYPES))))
                rtype = "activate"
        return {
            "id": str(e.get("id") or f"e{i}"),
            "from": str(frm or ""),
            "to": str(to or ""),
            "type": rtype,
            "label": str(e.get("label") or "").strip(),
            "route": str(e.get("route") or "straight"),
            "panel": str(e.get("panel") or ""),
            "source": str(e.get("source") or e.get("evidence") or ""),
            "dash": bool(e.get("dash", RELATION_TYPES[rtype]["dash"])),
            "color": str(e.get("color") or ""),
            "width_pt": _opt_float(e.get("width_pt")),
            "bidirectional": bool(e.get("bidirectional") or False),
            "waypoints": _as_list(e.get("waypoints")),
        }

    def _norm_chart(self, c: Any, i: int) -> dict:
        c = dict(c or {})
        data = dict(c.get("data") or {})
        ctype = str(c.get("type") or data.get("type") or "bar").lower()
        rows = data.get("rows")
        if rows is None:
            rows = []
        return {
            "id": str(c.get("id") or f"chart{i}"),
            "type": ctype,
            "panel": str(c.get("panel") or ""),
            "x": str(data.get("x") or c.get("x") or ""),
            "y": str(data.get("y") or c.get("y") or ""),
            "err": str(data.get("err") or data.get("error") or ""),
            "err_label": str(data.get("err_label") or ""),
            "n": str(data.get("n") or ""),
            "unit": str(data.get("unit") or c.get("unit") or ""),
            "xlabel": str(data.get("xlabel") or c.get("xlabel") or ""),
            "ylabel": str(data.get("ylabel") or c.get("ylabel") or ""),
            "title": str(data.get("title") or c.get("title") or ""),
            "rows": rows or [],
            "series": _as_list(data.get("series")),
            "categories": [str(v) for v in _as_list(data.get("categories"))],
            "values": _as_list(data.get("values")),
            "matrix": data.get("matrix"),
            "row_labels": [str(v) for v in _as_list(data.get("row_labels"))],
            "col_labels": [str(v) for v in _as_list(data.get("col_labels"))],
            "ymin": _opt_float(data.get("ymin")),
            "ymax": _opt_float(data.get("ymax")),
            "log": bool(data.get("log") or False),
            "significance": _as_list(data.get("significance")),
            "colors": _as_list(data.get("colors") or c.get("colors")),
            "legend": data.get("legend", c.get("legend")),
            "source": str(c.get("source") or c.get("evidence") or data.get("source") or ""),
            "x_mm": _opt_float(c.get("x_mm")),
            "y_mm": _opt_float(c.get("y_mm")),
            "w_mm": _opt_float(c.get("w_mm")),
            "h_mm": _opt_float(c.get("h_mm")),
            "xtick_rotate": _opt_float(data.get("xtick_rotate") or c.get("xtick_rotate")),
            "colorbar": bool(data.get("colorbar") or c.get("colorbar") or False),
            "colorbar_label": str(data.get("colorbar_label") or ""),
            "cmap": str(data.get("cmap") or "viridis"),
            "value_labels": bool(data.get("value_labels") or False),
            "reference_line": data.get("reference_line"),
        }

    def _norm_annotation(self, a: Any, i: int) -> dict:
        a = dict(a or {})
        return {
            "id": str(a.get("id") or f"ann{i}"),
            "text": str(a.get("text") or "").strip(),
            "kind": str(a.get("kind") or "note").lower(),
            "panel": str(a.get("panel") or ""),
            "target": str(a.get("target") or ""),
            "x_mm": _opt_float(a.get("x_mm")),
            "y_mm": _opt_float(a.get("y_mm")),
            "dx_mm": _opt_float(a.get("dx_mm")),
            "dy_mm": _opt_float(a.get("dy_mm")),
            "size_pt": _opt_float(a.get("size_pt")),
            "source": str(a.get("source") or ""),
            "align": str(a.get("align") or "left"),
        }

    def _norm_legend(self, lg: Any) -> dict:
        lg = dict(lg or {}) if isinstance(lg, dict) else {}
        items = []
        for i, it in enumerate(_as_list(lg.get("items"))):
            if isinstance(it, str):
                items.append({"key": f"c{i}", "label": it, "swatch": "color", "color": ""})
                continue
            it = dict(it or {})
            items.append({
                "key": str(it.get("key") or f"c{i}"),
                "label": str(it.get("label") or it.get("text") or ""),
                "swatch": str(it.get("swatch") or "color").lower(),
                "color": str(it.get("color") or ""),
                "dash": bool(it.get("dash") or False),
                "source": str(it.get("source") or ""),
            })
        return {
            "items": [x for x in items if x.get("label")],
            "title": str(lg.get("title") or ""),
            "position": str(lg.get("position") or "bottom"),
            "note": str(lg.get("note") or ""),
        }

    def _norm_source(self, s: Any, i: int) -> dict:
        s = dict(s or {}) if isinstance(s, dict) else {"path": str(s)}
        return {
            "id": str(s.get("id") or f"S{i + 1}"),
            "path": str(s.get("path") or ""),
            "sha256": str(s.get("sha256") or ""),
            "version": str(s.get("version") or ""),
            "kind": str(s.get("kind") or ""),
            "note": str(s.get("note") or ""),
        }

    # -- indexing / validation ----------------------------------------------
    def _index(self) -> None:
        self.node_by_id = {n["id"]: n for n in self.nodes}
        self.panel_by_id = {p["id"]: p for p in self.panels}
        self.lane_by_id = {l["id"]: l for l in self.lanes}
        self.source_ids = {s["id"] for s in self.sources}
        for e in self.edges:
            if e["from"] and e["from"] not in self.node_by_id:
                self.issues.append(Issue("error", "EDGE_FROM_MISSING",
                                         f"edge {e['id']} refers to missing node '{e['from']}'",
                                         f"edges[{e['id']}]", "add the node or fix the id"))
            if e["to"] and e["to"] not in self.node_by_id:
                self.issues.append(Issue("error", "EDGE_TO_MISSING",
                                         f"edge {e['id']} refers to missing node '{e['to']}'",
                                         f"edges[{e['id']}]", "add the node or fix the id"))
        for c in self.charts:
            if not _has_data(c):
                self.issues.append(Issue("error", "CHART_NO_DATA",
                                         f"chart {c['id']} has no usable rows/matrix",
                                         f"charts[{c['id']}]", "fill data.rows or data.matrix"))
            elif not c["rows"] and c["matrix"] is None and c["values"]:
                pass
        for n in self.nodes:
            if not n["label"]:
                self.issues.append(Issue("warn", "NODE_NO_LABEL", f"node {n['id']} has no label",
                                         f"nodes[{n['id']}]", "add label"))
        for e in self.edges:
            if e["from"] == e["to"] and e["from"]:
                self.issues.append(Issue("warn", "EDGE_SELF_LOOP",
                                         f"edge {e['id']} is a self-loop", f"edges[{e['id']}]",
                                         "confirm this is intended"))
        if not self.nodes and not self.charts:
            self.issues.append(Issue("error", "EMPTY_FIGURE", "spec has neither nodes nor charts",
                                     "spec", "add nodes/edges or charts"))

    def _validate(self) -> None:
        for n in self.nodes:
            if n["group"] and n["group"] not in {c["id"] for c in self.containers}:
                self.issues.append(Issue("warn", "GROUP_UNDECLARED",
                                         f"node {n['id']} references container '{n['group']}' not declared",
                                         f"nodes[{n['id']}]", "declare it in containers[]"))
            if n["lane"] and n["lane"] not in self.lane_by_id and self.lanes:
                self.issues.append(Issue("warn", "LANE_UNDECLARED",
                                         f"node {n['id']} references lane '{n['lane']}' not declared",
                                         f"nodes[{n['id']}]", "declare it in lanes[]"))
        used = {n["source"] for n in self.nodes if n["source"]} | {
            e["source"] for e in self.edges if e["source"]} | {
            c["source"] for c in self.charts if c["source"]}
        for ev in sorted(used):
            if ev and ev not in self.evidence:
                self.issues.append(Issue("warn", "EVIDENCE_UNRESOLVED",
                                         f"evidence id '{ev}' is used but not defined in evidence",
                                         "evidence", "add the quote and locator"))
        # every node/edge should be traceable
        untraced = [n["id"] for n in self.nodes if not n["source"]]
        if self.nodes and untraced:
            self.issues.append(Issue(
                "warn", "ELEMENT_NO_EVIDENCE",
                f"{len(untraced)}/{len(self.nodes)} nodes carry no evidence id: {', '.join(untraced[:8])}",
                "nodes", "set source to an evidence id for each element"))
        untraced_e = [e["id"] for e in self.edges if not e["source"]]
        if self.edges and untraced_e:
            self.issues.append(Issue(
                "warn", "EDGE_NO_EVIDENCE",
                f"{len(untraced_e)}/{len(self.edges)} edges carry no evidence id: {', '.join(untraced_e[:8])}",
                "edges", "set source to an evidence id for each edge"))
        if not self.caption:
            self.issues.append(Issue("warn", "NO_CAPTION", "spec has no caption", "caption",
                                     "write a caption that defines every symbol, n and error bar"))
        if not self.sources:
            self.issues.append(Issue("warn", "NO_SOURCES", "spec lists no sources", "sources",
                                     "record the input files with sha256"))

    # -- helpers -------------------------------------------------------------
    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i["level"] == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i["level"] == "warn"]

    def evidence_index(self) -> dict[str, dict]:
        out = {}
        for n in self.nodes:
            if n["source"]:
                out[f"node:{n['id']}"] = self.evidence.get(n["source"], {"source": n["source"]})
        for e in self.edges:
            if e["source"]:
                out[f"edge:{e['id']}"] = self.evidence.get(e["source"], {"source": e["source"]})
        for c in self.charts:
            if c["source"]:
                out[f"chart:{c['id']}"] = self.evidence.get(c["source"], {"source": c["source"]})
        return out


def _opt_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _slug(text: str) -> str:
    s = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_").lower()
    return s[:40]


def _has_data(c: dict) -> bool:
    if c.get("rows"):
        return True
    if c.get("matrix"):
        return True
    if c.get("values"):
        return True
    return False


def _default_shape(cls: str) -> str:
    cls = cls.lower()
    if cls in {"receptor", "rtk", "gpcr", "channel", "transporter"}:
        return "membrane_receptor"
    if cls in {"cell", "cell_type"}:
        return "cell"
    if cls in {"nucleus", "organelle", "vesicle", "mitochondrion"}:
        return "organelle"
    if cls in {"instrument", "device", "apparatus", "component", "pump", "valve", "detector"}:
        return "instrument"
    if cls in {"document", "paper", "report", "dataset", "database"}:
        return "document"
    if cls in {"process", "step", "stage"}:
        return "roundrect"
    if cls in {"decision"}:
        return "diamond"
    if cls in {"sample", "material", "reagent", "gas", "liquid"}:
        return "cylinder"
    return "roundrect"


def load_spec(path: str) -> Spec:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Spec(data, base_dir=os.path.dirname(os.path.abspath(path)))
