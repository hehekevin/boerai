"""Verification: does the drawing say only what the sources say?

Checks fall into four groups:
  A. traceability  - every element label is bound to a verbatim source quote;
  B. semantics     - relation type vs the wording of the quote, and edge direction;
  C. numbers/units - every number in the figure exists in the source or the table;
  D. geometry      - overflow, overlap, crossings, glyph coverage, exit criteria.
Each check returns a machine-readable record with a fix hint.
"""
from __future__ import annotations

import re
from typing import Any

from . import geom
from .draw import Drawing
from .geom import Rect
from .ir import RELATION_TYPES, Spec
from .layout import Layout

INHIBIT_WORDS = ("inhibit", "suppress", "repress", "reduce", "decrease", "block", "prevent",
                 "attenuate", "impair", "abolish", "limit", "downregulate", "down-regulate",
                 "抑制", "阻遏", "降低", "减少", "阻断", "削弱", "下调", "拮抗")
ACTIVATE_WORDS = ("activate", "induce", "promote", "enhance", "increase", "stimulate", "drive",
                  "upregulate", "up-regulate", "trigger", "facilitate", "phosphorylat",
                  "激活", "促进", "上调", "增强", "诱导", "提高", "触发", "磷酸化")


def _norm(text: str) -> str:
    t = text.replace("\u00ad", "").replace("-\n", "")
    t = re.sub(r"\s+", " ", t)
    return t.lower()


def _numbers(text: str) -> list[str]:
    return re.findall(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?(?![\w])", text)


def _same_number(a: str, b: str) -> bool:
    try:
        fa = float(a.replace("−", "-").replace(",", "."))
        fb = float(b.replace("−", "-").replace(",", "."))
    except ValueError:
        return False
    if fa == fb:
        return True
    return abs(fa - fb) <= 1e-6 * max(1.0, abs(fa), abs(fb))


class Check:
    def __init__(self, cid: str, status: str, message: str, where: str = "", fix: str = "",
                 evidence: str = ""):
        self.d = {"id": cid, "status": status, "message": message, "where": where,
                  "fix": fix, "evidence": evidence}

    def as_dict(self) -> dict:
        return self.d


def verify(spec: Spec, drawing: Drawing, layout: Layout, source_texts: dict[str, str] | None = None,
           data_numbers: set[str] | None = None, case_id: str = "",
           spec_issues: list[dict] | None = None) -> dict:
    source_texts = source_texts or {}
    checks: list[Check] = []
    joined = _norm(" ".join(source_texts.values()))
    for iss in (spec_issues or []):
        checks.append(Check(f"SPEC-{iss.get('code', 'ISSUE')}",
                            "fail" if iss.get("level") == "error" else "warn",
                            iss.get("message", ""), iss.get("where", ""), iss.get("fix", "")))
    if case_id:
        checks.append(Check("CASE-ID", "pass" if case_id == spec.case_id else "warn",
                            f"spec case_id '{spec.case_id}' matches the case file"
                            if case_id == spec.case_id else
                            f"spec case_id '{spec.case_id}' differs from the case file '{case_id}'",
                            "case_id", "copy case_id from /input/case.json"))
    checks += _evidence_checks(spec, joined, source_texts)
    checks += _semantic_checks(spec, joined)
    checks += _number_checks(spec, joined, data_numbers or set())
    checks += _legend_checks(spec)
    checks += _geometry_checks(spec, drawing, layout)
    checks += _completeness_checks(spec, drawing)
    checks += _glyph_checks(spec)

    failed = [c for c in checks if c.d["status"] == "fail"]
    warned = [c for c in checks if c.d["status"] == "warn"]
    passed = [c for c in checks if c.d["status"] == "pass"]
    return {
        "checks": [c.as_dict() for c in checks],
        "summary": {"total": len(checks), "pass": len(passed), "warn": len(warned), "fail": len(failed),
                    "verdict": "fail" if failed else ("warn" if warned else "pass")},
    }


# ------------------------------------------------------------------ A evidence
def _evidence_checks(spec: Spec, joined: str, source_texts: dict[str, str]) -> list[Check]:
    out: list[Check] = []
    ev_ids = set(spec.evidence)
    used = {n["source"] for n in spec.nodes if n["source"]}
    used |= {e["source"] for e in spec.edges if e["source"]}
    used |= {c["source"] for c in spec.charts if c["source"]}
    missing = sorted(i for i in used if i and i not in ev_ids)
    out.append(Check("EVID-IDs", "fail" if missing else "pass",
                     f"{len(missing)} element(s) reference undefined evidence ids: {', '.join(missing[:6])}"
                     if missing else "all element evidence ids resolve",
                     "evidence", "define each id in evidence{} with source, locator and quote"))
    untraced = [n["id"] for n in spec.nodes if not n["source"]]
    out.append(Check("EVID-NODES", "warn" if untraced else "pass",
                     f"{len(untraced)} node(s) without evidence: {', '.join(untraced[:6])}"
                     if untraced else "every node is bound to evidence", "nodes",
                     "set nodes[].source to an evidence id"))
    untraced_e = [e["id"] for e in spec.edges if not e["source"]]
    out.append(Check("EVID-EDGES", "warn" if untraced_e else "pass",
                     f"{len(untraced_e)} edge(s) without evidence: {', '.join(untraced_e[:6])}"
                     if untraced_e else "every edge is bound to evidence", "edges",
                     "set edges[].source to an evidence id"))

    not_found, empty_quote, no_locator = [], [], []
    for eid, ev in spec.evidence.items():
        q = (ev.get("quote") or "").strip()
        if not q:
            empty_quote.append(eid)
            continue
        if not ev.get("locator"):
            no_locator.append(eid)
        if joined:
            probe = _norm(q)[:180]
            probe = re.sub(r"[^0-9a-z\u4e00-\u9fff ]+", " ", probe).strip()
            hay = re.sub(r"[^0-9a-z\u4e00-\u9fff ]+", " ", joined)
            words = [w for w in probe.split(" ") if len(w) > 3]
            hit = probe and probe in hay
            if not hit and words:
                hits = sum(1 for w in words if w in hay)
                hit = hits / len(words) >= 0.8
            if not hit:
                not_found.append(eid)
    out.append(Check("EVID-QUOTE-PRESENT", "fail" if not_found else "pass",
                     f"{len(not_found)} quote(s) could not be located in the supplied source text: "
                     f"{', '.join(not_found[:6])}" if not_found else
                     "every evidence quote was found in the supplied source text",
                     "evidence", "copy the quote verbatim from the source, or fix the file reference",
                     evidence=", ".join(not_found[:6])))
    out.append(Check("EVID-QUOTE-FILLED", "warn" if empty_quote else "pass",
                     f"{len(empty_quote)} evidence entr(ies) have no quote: {', '.join(empty_quote[:6])}"
                     if empty_quote else "every evidence entry carries a quote", "evidence",
                     "add the verbatim sentence that supports the element"))
    out.append(Check("EVID-LOCATOR", "warn" if no_locator else "pass",
                     f"{len(no_locator)} evidence entr(ies) have no locator: {', '.join(no_locator[:6])}"
                     if no_locator else "every evidence entry carries a locator", "evidence",
                     "add page/panel/row locator, e.g. 'p.7, Fig. 3 legend'"))
    return out


# ------------------------------------------------------------------ B semantics
def _semantic_checks(spec: Spec, joined: str) -> list[Check]:
    out: list[Check] = []
    mism, dirs = [], []
    for e in spec.edges:
        ev = spec.evidence.get(e["source"], {})
        q = _norm(ev.get("quote", ""))
        rtype = e["type"]
        is_inh = rtype in {"inhibit", "repress"}
        is_act = rtype in {"activate", "promote", "upregulate"}
        if q and (is_inh or is_act):
            has_inh = any(w in q for w in INHIBIT_WORDS)
            has_act = any(w in q for w in ACTIVATE_WORDS)
            if is_inh and has_act and not has_inh:
                mism.append((e["id"], rtype, "quote only contains an activating verb"))
            if is_act and has_inh and not has_act:
                mism.append((e["id"], rtype, "quote only contains an inhibiting verb"))
        # direction: if the quote names both endpoints in the opposite order
        a = spec.node_by_id.get(e["from"], {})
        b = spec.node_by_id.get(e["to"], {})
        if q and a.get("label") and b.get("label"):
            la, lb = _norm(a["label"]), _norm(b["label"])
            ia, ib = q.find(la), q.find(lb)
            if ia >= 0 and ib >= 0 and ia > ib and abs(ia - ib) > 2:
                between = q[ib:ia]
                passive = any(tok in between for tok in (" by ", "被", "由", " mediated by "))
                if passive:
                    continue
                if any(w in between for w in ACTIVATE_WORDS + INHIBIT_WORDS):
                    dirs.append((e["id"], f"{a['label']}->{b['label']}", "quote mentions the target before the source"))
    out.append(Check("SEM-RELATION-WORD", "fail" if mism else "pass",
                     "; ".join(f"{i}: {t} but {m}" for i, t, m in mism[:5]) if mism else
                     "relation types agree with the wording of their evidence", "edges",
                     "change edges[].type to match the source sentence"))
    out.append(Check("SEM-DIRECTION", "warn" if dirs else "pass",
                     "; ".join(f"{i}: {d} ({m})" for i, d, m in dirs[:5]) if dirs else
                     "edge directions are consistent with the order of entities in the quotes",
                     "edges", "swap from/to, or record the sentence that states the direction"))
    # every relation type in use must be documented in the legend when the figure has a legend
    types = sorted({e["type"] for e in spec.edges})
    legend_keys = {it["key"] for it in spec.legend["items"]}
    if spec.legend["items"] and types:
        covered = {t for t in types if t in legend_keys or
                   any(t in k or k in t for k in legend_keys)}
        missing = [t for t in types if t not in covered]
        out.append(Check("SEM-LEGEND-TYPES", "warn" if missing else "pass",
                         f"relation types not explained in the legend: {', '.join(missing)}" if missing
                         else "every relation type used is explained in the legend", "legend",
                         "add a legend item per arrow semantics (activate/inhibit/…)"))
    else:
        out.append(Check("SEM-LEGEND-TYPES", "warn" if types else "pass",
                         "figure has relations but no legend" if types else "no relations to explain",
                         "legend", "add legend items for arrow semantics"))
    return out


# ------------------------------------------------------------------ C numbers
def _number_checks(spec: Spec, joined: str, data_numbers: set[str]) -> list[Check]:
    out: list[Check] = []
    labels: list[tuple[str, str]] = []
    for n in spec.nodes:
        labels.append((f"node:{n['id']}", " ".join([n["label"], n["sublabel"]])))
    for e in spec.edges:
        if e["label"]:
            labels.append((f"edge:{e['id']}", e["label"]))
    for a in spec.annotations:
        labels.append((f"ann:{a['id']}", a["text"]))
    if spec.caption:
        labels.append(("caption", spec.caption))
    unknown: list[str] = []
    unknown_caption: list[str] = []
    known_pool = list(data_numbers)
    for where, text in labels:
        for tok in _numbers(text):
            ok = any(_same_number(tok, k) for k in known_pool)
            if not ok and joined:
                ok = any(_same_number(tok, k) for k in _numbers(joined))
            if not ok:
                if where == "caption":
                    unknown_caption.append(tok)
                else:
                    unknown.append(f"{where}:{tok}")
    if unknown_caption:
        out.append(Check("NUM-CAPTION", "warn",
                         f"{len(unknown_caption)} caption number(s) not found verbatim in the sources: "
                         f"{', '.join(sorted(set(unknown_caption))[:6])}", "caption",
                         "keep caption numbers identical to the source, or move them into evidence"))
    out.append(Check("NUM-TRACEABLE", "fail" if unknown else "pass",
                     f"{len(unknown)} number(s) in the figure are absent from sources/tables: "
                     f"{', '.join(unknown[:8])}" if unknown else
                     "every number printed in the figure is present in the sources or data table",
                     "labels", "remove the number, or add the evidence that contains it"))
    # unit consistency between chart data unit and axis label
    bad_units = []
    for c in spec.charts:
        unit = (c.get("unit") or "").strip()
        ylab = (c.get("ylabel") or "").strip()
        if unit and ylab:
            paren = [p.strip().lower() for p in re.findall(r"[\(\[]([^\)\]]+)[\)\]]", ylab)]
            u = unit.strip().lower()
            if paren:
                ok = any(u == p or u in p or p in u or u.split()[0] == p.split()[0] for p in paren)
                if not ok:
                    bad_units.append(f"{c['id']}: axis '{ylab}' vs data unit '{unit}'")
        if unit and not ylab:
            bad_units.append(f"{c['id']}: unit '{unit}' declared but no axis label")
    out.append(Check("UNIT-CONSISTENT", "warn" if bad_units else "pass",
                     "; ".join(bad_units) if bad_units else "axis labels and data units agree",
                     "charts", "put the unit in the axis label and keep one unit per axis"))
    # decimal precision: value labels must not exceed the source precision
    return out


# ------------------------------------------------------------------ legend
def _legend_checks(spec: Spec) -> list[Check]:
    out: list[Check] = []
    items = spec.legend["items"]
    needs_legend = bool(spec.edges) or any(len(c.get("colors") or []) > 1 for c in spec.charts)
    if not items:
        if needs_legend:
            return [Check("LEG-EXISTS", "warn", "figure has no legend", "legend",
                          "add a legend whenever colour, line style or arrow type encodes meaning")]
        return [Check("LEG-EXISTS", "pass", "no legend needed: nothing encodes meaning by style", "legend")]
    keys = [it["key"] for it in items]
    dup = {k for k in keys if keys.count(k) > 1}
    out.append(Check("LEG-UNIQUE", "fail" if dup else "pass",
                     f"duplicate legend keys: {', '.join(sorted(dup))}" if dup else
                     "legend keys are unique", "legend", "give each legend item a distinct key"))
    empty = [it["key"] for it in items if not it["label"].strip()]
    out.append(Check("LEG-LABELS", "fail" if empty else "pass",
                     f"legend items without a label: {', '.join(empty)}" if empty else
                     "every legend item has a label", "legend", "label every swatch"))
    # colour-coded categories: legend colour items should match chart series colours
    chart_cats = 0
    for c in spec.charts:
        if c.get("colors"):
            chart_cats = max(chart_cats, len(c["colors"]))
        rows = c.get("rows") or []
        if rows and c.get("type") in {"bar", "line", "scatter"}:
            groups = {str(r.get("group") or r.get("series") or "") for r in rows if isinstance(r, dict)}
            groups.discard("")
            chart_cats = max(chart_cats, len(groups))
    colour_items = [it for it in items if it["swatch"] in {"color", "bar", "box", "fill"}]
    if chart_cats and colour_items:
        ok = len(colour_items) == chart_cats
        out.append(Check("LEG-MATCHES-DATA", "fail" if not ok else "pass",
                         f"{len(colour_items)} colour legend items vs {chart_cats} data categories"
                         if not ok else
                         f"legend colour items ({len(colour_items)}) match the data categories ({chart_cats})",
                         "legend", "one legend item per category, no more, no fewer"))
    return out


# ------------------------------------------------------------------ geometry
def _geometry_checks(spec: Spec, drawing: Drawing, layout: Layout) -> list[Check]:
    out: list[Check] = []
    canvas = layout.canvas
    # text vs canvas
    outside = [tb["text"] for tb in drawing.text_boxes
               if tb["rect"].x < -0.6 or tb["rect"].y < -0.6 or tb["rect"].x1 > canvas.x1 + 0.6
               or tb["rect"].y1 > canvas.y1 + 0.6]
    out.append(Check("GEO-CANVAS", "fail" if outside else "pass",
                     f"{len(outside)} text element(s) outside the canvas: {outside[:4]}" if outside else
                     "all text lies inside the canvas", "canvas", "reduce label length or canvas padding"))
    # text inside its node
    overflow = []
    for n in spec.nodes:
        r = layout.nodes.get(n["id"])
        if not r:
            continue
        for tb in drawing.text_boxes:
            if tb["tag"] == f"node:label:{n['id']}" and (tb["rect"].w > r.w - 0.8):
                overflow.append(n["id"])
                break
    out.append(Check("GEO-OVERFLOW", "warn" if overflow else "pass",
                     f"label wider than its box: {', '.join(overflow[:6])}" if overflow else
                     "no label overflows its node box", "nodes",
                     "shorten the label or let the layout widen the node"))
    # node overlap
    rects = list(layout.nodes.items())
    overlaps = []
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if rects[i][1].intersects(rects[j][1], tol=0.15):
                overlaps.append(f"{rects[i][0]}~{rects[j][0]}")
    out.append(Check("GEO-NODE-OVERLAP", "fail" if overlaps else "pass",
                     f"{len(overlaps)} overlapping node pair(s): {', '.join(overlaps[:6])}" if overlaps else
                     "no two nodes overlap", "nodes", "reduce node count per lane or enlarge the canvas"))
    # text-text overlap (different layers, both visible)
    tbs = [tb for tb in drawing.text_boxes if tb["layer"] not in {"canvas"}]
    t_ov = []
    for i in range(len(tbs)):
        for j in range(i + 1, len(tbs)):
            a, b = tbs[i], tbs[j]
            if a["rect"].intersects(b["rect"], tol=0.35) and a["text"] != b["text"]:
                t_ov.append(f"{a['text'][:12]}|{b['text'][:12]}")
    out.append(Check("GEO-TEXT-OVERLAP", "warn" if len(t_ov) > 2 else "pass",
                     f"{len(t_ov)} overlapping text pair(s): {', '.join(t_ov[:4])}" if t_ov else
                     "no text overlaps", "text", "move labels or increase spacing"))
    out.append(Check("GEO-EDGE-CROSSINGS", "warn" if getattr(layout, "edge_crossings", 0) > 6 else "pass",
                     f"{getattr(layout, 'edge_crossings', 0)} edge crossings", "edges",
                     "reorder nodes inside a lane, or use an orthogonal route"))
    # margin balance
    right = max([r.x1 for r in layout.nodes.values()] + [layout.canvas.x1])
    out.append(Check("GEO-FILL", "pass" if right > spec.width_mm * 0.55 else "warn",
                     "figure area is well used" if right > spec.width_mm * 0.55 else
                     "content occupies less than 55% of the canvas width", "canvas",
                     "raise node sizes or reduce the canvas width"))
    return out


# ------------------------------------------------------------------ completeness
def _completeness_checks(spec: Spec, drawing: Drawing) -> list[Check]:
    out: list[Check] = []
    out.append(Check("CMP-CAPTION", "pass" if spec.caption else "warn",
                     "caption present" if spec.caption else "no caption: symbols, n and error bars are undefined",
                     "caption", "write a caption defining every abbreviation, n and error bar"))
    has_units = any(re.search(r"[\(\[]\s*[^()\[\]]{1,24}\s*[\)\]]", (c.get("ylabel") or ""))
                    for c in spec.charts)
    if spec.charts:
        out.append(Check("CMP-AXIS-UNITS", "pass" if has_units else "warn",
                         "quantitative axes carry units" if has_units else
                         "chart axes carry no unit", "charts",
                         "give every quantitative axis a unit or state 'dimensionless'"))
    if len(spec.panels) > 1:
        out.append(Check("CMP-PANEL-LETTERS", "pass" if all(p["id"] for p in spec.panels) else "warn",
                         "multi-panel figure with panel letters", "panels", "label panels A, B, C"))
    if spec.nodes and not spec.edges:
        out.append(Check("CMP-RELATIONS", "warn", "nodes present but no relations", "edges",
                         "add the relations the source states, or state that the figure is a list"))
    labels = [n["label"] for n in spec.nodes if n["label"]]
    dup = {l for l in labels if labels.count(l) > 1}
    out.append(Check("CMP-DUPLICATE-LABELS", "warn" if dup else "pass",
                     f"duplicate entity labels: {', '.join(sorted(dup)[:5])}" if dup else
                     "entity labels are unique", "nodes", "disambiguate labels (isoform, compartment)"))
    return out


# ------------------------------------------------------------------ glyphs
def _glyph_checks(spec: Spec) -> list[Check]:
    text = " ".join([spec.title, spec.caption] + [n["label"] + n["sublabel"] for n in spec.nodes]
                    + [e["label"] for e in spec.edges] + [it["label"] for it in spec.legend["items"]])
    cjk = [ch for ch in text if 0x2E80 <= ord(ch) <= 0x9FFF]
    if not cjk:
        return [Check("GLYPH-CJK", "pass", "no CJK glyphs required", "text")]
    try:
        from .mpl_out import resolve_font_stack, supports_cjk
        stack, _ = resolve_font_stack(spec.font_stack)
        ok = any(supports_cjk(f) for f in stack)
    except Exception:
        ok = False
    return [Check("GLYPH-CJK", "pass" if ok else "fail",
                  "a CJK-capable font is available for all labels" if ok else
                  "CJK labels present but no CJK-capable font was found: text would render as boxes",
                  "text", "install Noto Sans CJK SC or set canvas.font_stack to an installed CJK font")]
