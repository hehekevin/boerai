"""Data charts: value -> geometry mapping with an explicit, auditable data table.

Only the chart types named in the spec are drawn, axes are derived from the
data (never from the picture), and each drawn mark is tagged with the row it
came from so the verification step can re-read the value from the source table.
"""
from __future__ import annotations

import math
from typing import Any

from . import geom, prims, style
from .geom import Rect


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("−", "-").strip())
    except ValueError:
        return None


def _field(row: dict, name: str) -> Any:
    if not name:
        return None
    if name in row:
        return row[name]
    low = {str(k).lower(): k for k in row}
    return row.get(low.get(name.lower(), ""), None)


def table_rows(c: dict) -> tuple[list[str], list[str], dict, list[dict]]:
    """Normalise any accepted data shape into (categories, groups, cells, records)."""
    cats: list[str] = []
    groups: list[str] = []
    cells: dict[tuple[str, str], dict] = {}
    records: list[dict] = []
    rows = [r for r in (c.get("rows") or []) if isinstance(r, dict)]

    if rows and c.get("x") and c.get("y"):
        group_field = ""
        forbidden = {str(c.get("x") or "").lower(), str(c.get("y") or "").lower(),
                     str(c.get("err") or "").lower(), str(c.get("n") or "").lower()}
        for cand in ("group", "series", "treatment_group", "genotype_group", "condition_group"):
            if cand in forbidden:
                continue
            if any(cand in {str(k).lower() for k in r} for r in rows):
                group_field = cand
                break
        for r in rows:
            cat = _field(r, c["x"])
            if cat is None:
                continue
            cat = str(cat)
            grp = str(_field(r, group_field)) if group_field else ""
            val = _num(_field(r, c["y"]))
            if val is None:
                continue
            err = _num(_field(r, c["err"])) if c.get("err") else None
            n = _num(_field(r, c["n"])) if c.get("n") else None
            if cat not in cats:
                cats.append(cat)
            if grp not in groups:
                groups.append(grp)
            cell = cells.setdefault((cat, grp), {"vals": [], "errs": [], "ns": [], "rows": []})
            cell["vals"].append(val)
            if err is not None:
                cell["errs"].append(err)
            if n is not None:
                cell["ns"].append(n)
            cell["rows"].append(r)
        out = {}
        for key, cell in cells.items():
            vals = cell["vals"]
            out[key] = {
                "value": sum(vals) / len(vals),
                "err": (sum(cell["errs"]) / len(cell["errs"])) if cell["errs"] else None,
                "n": (int(sum(cell["ns"]) / len(cell["ns"])) if cell["ns"] else (len(vals) if len(vals) > 1 else None)),
                "raw": vals,
                "records": cell["rows"],
            }
        return cats, [g for g in groups], out, records

    series = [s for s in (c.get("series") or []) if isinstance(s, dict)]
    if series:
        cats = [str(v) for v in (c.get("categories") or [])]
        n = max((len(s.get("values") or []) for s in series), default=0)
        if len(cats) < n:
            cats += [str(i + 1) for i in range(len(cats), n)]
        out = {}
        for s in series:
            name = str(s.get("name") or s.get("label") or "series")
            groups.append(name)
            errs = s.get("err") or s.get("errors") or []
            for i, v in enumerate(s.get("values") or []):
                val = _num(v)
                if val is None or i >= len(cats):
                    continue
                out[(cats[i], name)] = {"value": val,
                                        "err": _num(errs[i]) if i < len(errs) else None,
                                        "n": s.get("n"), "raw": [val], "records": [{"value": val}]}
        return cats, groups, out, []

    # simple categories/values pair
    cats = [str(v) for v in (c.get("categories") or [])]
    vals = [_num(v) for v in (c.get("values") or [])]
    out = {}
    for cat, val in zip(cats, vals):
        if val is None:
            continue
        out[(cat, "")] = {"value": val, "err": None, "n": None, "raw": [val], "records": [{"value": val}]}
    return cats, [""], out, []


def draw_chart(c: dict, rects: dict, spec, layer: str = "chart") -> tuple[list[dict], dict]:
    ctype = c["type"]
    if ctype in {"heatmap", "matrix"}:
        return _draw_heatmap(c, rects, spec, layer)
    if ctype in {"box", "boxplot"}:
        return _draw_box(c, rects, spec, layer)
    return _draw_xy(c, rects, spec, layer)


# --------------------------------------------------------------------- xy
def _draw_xy(c: dict, rects: dict, spec, layer: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    plot: Rect = rects["plot"]
    size = max(4.6, spec.font_pt * 0.88)
    small = size * 0.92
    ink = "#1A1A1A"
    cats, groups, cells, records = table_rows(c)
    ctype = c["type"]
    if not cats or not cells:
        out.append(prims.text(plot.cx, plot.cy, "no data", size=size, fill="#999999",
                              layer=layer, tag="chart:empty"))
        return out, {"categories": [], "groups": []}

    multi = len([g for g in groups if any((cat, g) in cells for cat in cats)]) > 1
    if not multi:
        groups = [g for g in groups if any((cat, g) in cells for cat in cats)] or [""]

    if ctype in {"line", "scatter"}:
        xs = {cat: i for i, cat in enumerate(cats)}
        numeric_x = all(_num(cat) is not None for cat in cats) and ctype == "scatter"
        allv = [d["value"] for d in cells.values() if d.get("value") is not None]
        lo = min(allv) if allv else 0.0
        hi = max(allv) if allv else 1.0
        pad = (hi - lo) * 0.12 or max(1.0, abs(hi) * 0.1)
        lo_p = lo - pad
        if lo >= 0 and lo < 0.4 * (hi or 1):
            lo_p = 0.0
        vmin, vmax = (c["ymin"] if c["ymin"] is not None else lo_p,
                      c["ymax"] if c["ymax"] is not None else hi + pad)
    else:
        allv = [d["value"] for d in cells.values() if d.get("value") is not None]
        hi = max(allv + [d.get("err") or 0 for d in cells.values()] or [1.0])
        vmin = c["ymin"] if c["ymin"] is not None else 0.0
        vmax = c["ymax"] if c["ymax"] is not None else hi * 1.14 if hi > 0 else 1.0

    if c["log"]:
        vmin = max(1e-9, vmin if vmin > 0 else min([v for v in allv if v > 0] or [1e-9]) * 0.8)

    ticks = geom.nice_ticks(vmin, vmax, target=max(3, int(plot.h / 11)))
    vmin, vmax = min(vmin, ticks[0]), max(vmax, ticks[-1])

    def sy(v: float) -> float:
        if c["log"]:
            a, b = math.log10(max(vmin, 1e-12)), math.log10(max(vmax, 1e-12))
            t = (math.log10(max(v, 1e-12)) - a) / (b - a or 1)
        else:
            t = (v - vmin) / ((vmax - vmin) or 1)
        return plot.y1 - t * plot.h

    # frame + gridlines
    out.append(prims.line(plot.x, plot.y, plot.x, plot.y1, stroke=ink, sw=0.25, layer=layer, tag="axis:y"))
    out.append(prims.line(plot.x, plot.y1, plot.x1, plot.y1, stroke=ink, sw=0.25, layer=layer, tag="axis:x"))
    for t in ticks:
        y = sy(t)
        if y < plot.y - 0.5 or y > plot.y1 + 0.5:
            continue
        out.append(prims.line(plot.x, y, plot.x1, y, stroke="#E3E3E3", sw=0.16, dash=True,
                              layer=layer + ":grid", tag="grid"))
        out.append(prims.text(plot.x - 1.2, y, geom.fmt_num(t), size=small, anchor="end",
                              fill=ink, layer=layer, tag="ytick"))
    # axis labels
    ylab = c["ylabel"] or c["y"] or ""
    if c["unit"] and c["unit"].lower() not in ylab.lower():
        ylab = f"{ylab} ({c['unit']})" if ylab else f"({c['unit']})"
    if ylab:
        out.append(prims.text(plot.x - 8.6, plot.cy, ylab, size=size, anchor="middle",
                              fill=ink, rotate=-90, layer=layer, tag="ylabel"))
    xlab = c["xlabel"] or c["x"]
    if xlab:
        out.append(prims.text(plot.cx, plot.y1 + rects["xlabel_h"] - 1.6, xlab, size=size,
                              anchor="middle", fill=ink, layer=layer, tag="xlabel"))
    if c["title"]:
        out.append(prims.text(rects["rect"].x, plot.y - 2.2, c["title"], size=size,
                              anchor="start", weight="bold", fill=ink, layer=layer, tag="chart:title"))

    ncat = len(cats)
    slot = plot.w / ncat
    colors = c.get("colors") or style.category_colors(max(1, len(groups)))

    # significance brackets
    brackets = [b for b in (c.get("significance") or []) if isinstance(b, dict)]
    if brackets:
        top_used = min([sy(d["value"] + (d.get("err") or 0)) for d in cells.values()] or [plot.y])
        lvl = top_used - 2.4
        for b in brackets:
            i0 = cats.index(str(b.get("from"))) if str(b.get("from")) in cats else None
            i1 = cats.index(str(b.get("to"))) if str(b.get("to")) in cats else None
            if i0 is None or i1 is None:
                continue
            x0 = plot.x + slot * (i0 + 0.5)
            x1 = plot.x + slot * (i1 + 0.5)
            out.append(prims.poly([(x0, lvl + 1.1), (x0, lvl), (x1, lvl), (x1, lvl + 1.1)],
                                  closed=False, stroke=ink, sw=0.22, layer=layer, tag="signif"))
            out.append(prims.text((x0 + x1) / 2, lvl - 1.4, str(b.get("label") or "*"),
                                  size=size, fill=ink, layer=layer, tag="signif:text"))
            lvl -= 3.4

    if ctype in {"bar", "column"}:
        ng = max(1, len(groups))
        bw = slot * 0.72 / ng
        if ng == 1:
            colors = style.category_colors(max(1, len(cats)))
        for gi, g in enumerate(groups):
            for ci, cat in enumerate(cats):
                d = cells.get((cat, g))
                if not d:
                    continue
                cx = plot.x + slot * (ci + 0.5) + (gi - (ng - 1) / 2) * bw
                y0 = sy(max(0.0, vmin) if vmin <= 0 else vmin)
                y1 = sy(d["value"])
                color = colors[(ci if ng == 1 else gi) % len(colors)]
                out.append(prims.rect(cx - bw / 2 * 0.92, min(y0, y1), bw * 0.92, abs(y1 - y0),
                                      fill=color, stroke=color, sw=0.1, layer=layer,
                                      tag=f"bar:{cat}:{g}", src=c.get("source", "")))
                if d.get("err"):
                    ey0, ey1 = sy(d["value"] - d["err"]), sy(d["value"] + d["err"])
                    out.append(prims.line(cx, ey0, cx, ey1, stroke=ink, sw=0.22, layer=layer,
                                          tag=f"err:{cat}:{g}"))
                    cap = bw * 0.26
                    out.append(prims.line(cx - cap, ey1, cx + cap, ey1, stroke=ink, sw=0.22, layer=layer))
                    out.append(prims.line(cx - cap, ey0, cx + cap, ey0, stroke=ink, sw=0.22, layer=layer))
                if c.get("value_labels"):
                    out.append(prims.text(cx, min(y0, y1) - 1.3, geom.fmt_num(d["value"]),
                                          size=small, fill=ink, layer=layer, tag="value"))
    elif ctype in {"line", "scatter"}:
        for gi, g in enumerate(groups):
            pts = []
            for ci, cat in enumerate(cats):
                d = cells.get((cat, g))
                if not d:
                    continue
                x = plot.x + slot * (ci + 0.5)
                pts.append((x, sy(d["value"])))
            color = colors[gi % len(colors)]
            if ctype == "line" and len(pts) > 1:
                out.append(prims.poly(pts, closed=False, stroke=color, sw=0.35, layer=layer,
                                      tag=f"line:{g}", src=c.get("source", "")))
            for (x, y), ci in zip(pts, range(len(pts))):
                d = cells.get((cats[ci], g))
                if d.get("err"):
                    out.append(prims.line(x, sy(d["value"] - d["err"]), x, sy(d["value"] + d["err"]),
                                          stroke=color, sw=0.2, layer=layer))
                out.append(prims.circle(x, y, 0.85, fill=color, stroke="#FFFFFF", sw=0.15,
                                        layer=layer, tag=f"pt:{cats[ci]}:{g}", src=c.get("source", "")))
    # x ticks
    for ci, cat in enumerate(cats):
        x = plot.x + slot * (ci + 0.5)
        rot = c.get("xtick_rotate")
        if rot is None:
            rot = -40 if geom.text_width_mm(cat, small) > slot * 0.95 else 0
        if rot:
            out.append(prims.text(x, plot.y1 + 1.6, cat, size=small, anchor="end", fill=ink,
                                  rotate=rot, layer=layer, tag="xtick"))
        else:
            out.append(prims.text(x, plot.y1 + 1.7, cat, size=small, anchor="middle", fill=ink,
                                  layer=layer, tag="xtick"))

    # series legend inside the chart area
    if multi:
        lh = size * geom.PT2MM * 1.5
        lx = rects["rect"].x
        ly = rects["rect"].y1 - rects["legend_h"] + 1.0
        for gi, g in enumerate(groups):
            out.append(prims.rect(lx, ly, 2.6, 1.6, fill=colors[gi % len(colors)], stroke="none",
                                  layer=layer, tag="chart:legend"))
            out.append(prims.text(lx + 3.4, ly + 0.85, g, size=small, anchor="start", fill=ink,
                                  layer=layer, tag="chart:legend"))
            lx += 3.4 + geom.text_width_mm(g, small) + 4.0
    return out, {"categories": cats, "groups": groups, "cells": cells}


# -------------------------------------------------------------------- box
def _draw_box(c: dict, rects: dict, spec, layer: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    plot: Rect = rects["plot"]
    size = max(4.6, spec.font_pt * 0.88)
    ink = "#1A1A1A"
    cats, groups, cells, _ = table_rows(c)
    if not cells:
        return out, {"categories": []}
    stats = []
    for cat in cats:
        vals: list[float] = []
        for g in groups:
            d = cells.get((cat, g))
            if d:
                vals.extend(d.get("raw") or [d["value"]])
        if not vals:
            continue
        vals.sort()
        q1, med, q3 = _quantile(vals, 0.25), _quantile(vals, 0.5), _quantile(vals, 0.75)
        iqr = q3 - q1
        lo = min([v for v in vals if v >= q1 - 1.5 * iqr] or [vals[0]])
        hi = max([v for v in vals if v <= q3 + 1.5 * iqr] or [vals[-1]])
        outl = [v for v in vals if v < lo or v > hi]
        stats.append((cat, q1, med, q3, lo, hi, outl, vals))
    allv = [v for s in stats for v in s[7]]
    vmin = c["ymin"] if c["ymin"] is not None else min(allv) - (max(allv) - min(allv)) * 0.12
    vmax = c["ymax"] if c["ymax"] is not None else max(allv) + (max(allv) - min(allv)) * 0.12
    ticks = geom.nice_ticks(vmin, vmax, target=max(3, int(plot.h / 11)))
    vmin, vmax = min(vmin, ticks[0]), max(vmax, ticks[-1])

    def sy(v):
        return plot.y1 - (v - vmin) / ((vmax - vmin) or 1) * plot.h

    out.append(prims.line(plot.x, plot.y, plot.x, plot.y1, stroke=ink, sw=0.25, layer=layer, tag="axis:y"))
    out.append(prims.line(plot.x, plot.y1, plot.x1, plot.y1, stroke=ink, sw=0.25, layer=layer, tag="axis:x"))
    for t in ticks:
        y = sy(t)
        out.append(prims.line(plot.x, y, plot.x1, y, stroke="#E9E9E9", sw=0.14, dash=True, layer=layer + ":grid"))
        out.append(prims.text(plot.x - 1.2, y, geom.fmt_num(t), size=size * 0.92, anchor="end", fill=ink, layer=layer))
    ylab = c["ylabel"] or c["y"]
    if ylab:
        out.append(prims.text(plot.x - 8.6, plot.cy, ylab, size=size, rotate=-90, fill=ink, layer=layer, tag="ylabel"))
    slot = plot.w / max(1, len(stats))
    colors = c.get("colors") or style.category_colors(max(1, len(stats)))
    for i, (cat, q1, med, q3, lo, hi, outl, vals) in enumerate(stats):
        x = plot.x + slot * (i + 0.5)
        bw = slot * 0.42
        color = colors[i % len(colors)]
        out.append(prims.rect(x - bw / 2, sy(q3), bw, sy(q1) - sy(q3), fill=color, stroke=ink,
                              sw=0.18, opacity=0.55, layer=layer, tag=f"box:{cat}", src=c.get("source", "")))
        out.append(prims.line(x - bw / 2, sy(med), x + bw / 2, sy(med), stroke=ink, sw=0.45, layer=layer))
        out.append(prims.line(x, sy(q3), x, sy(hi), stroke=ink, sw=0.2, layer=layer))
        out.append(prims.line(x, sy(q1), x, sy(lo), stroke=ink, sw=0.2, layer=layer))
        for yy in (hi, lo):
            out.append(prims.line(x - bw * 0.28, sy(yy), x + bw * 0.28, sy(yy), stroke=ink, sw=0.2, layer=layer))
        for v in outl:
            out.append(prims.circle(x, sy(v), 0.6, fill="#FFFFFF", stroke=ink, sw=0.18, layer=layer, tag="outlier"))
        rot = -35 if geom.text_width_mm(cat, size * 0.92) > slot * 0.95 else 0
        out.append(prims.text(x, plot.y1 + 1.7, cat, size=size * 0.92, anchor="end" if rot else "middle",
                              rotate=rot, fill=ink, layer=layer, tag="xtick"))
    if c["xlabel"] or c["x"]:
        out.append(prims.text(plot.cx, plot.y1 + rects["xlabel_h"] - 1.4, c["xlabel"] or c["x"],
                              size=size, fill=ink, layer=layer, tag="xlabel"))
    if c["title"]:
        out.append(prims.text(rects["rect"].x, plot.y - 2.2, c["title"], size=size, anchor="start",
                              weight="bold", fill=ink, layer=layer))
    return out, {"categories": [s[0] for s in stats], "stats": stats}


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


# ---------------------------------------------------------------- heatmap
def _draw_heatmap(c: dict, rects: dict, spec, layer: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    rect = rects["rect"]
    size = max(4.4, spec.font_pt * 0.86)
    ink = "#1A1A1A"
    matrix = c.get("matrix")
    if not matrix:
        cats, groups, cells, _ = table_rows(c)
        rows = [[cells.get((cat, g), {}).get("value") for g in groups] for cat in cats]
        matrix = rows
        row_labels = cats
        col_labels = groups
    else:
        row_labels = c.get("row_labels") or [str(i + 1) for i in range(len(matrix))]
        col_labels = c.get("col_labels") or [str(i + 1) for i in range(len(matrix[0]) if matrix else 0)]
    vals = [v for r in matrix for v in r if isinstance(v, (int, float))]
    if not vals:
        return out, {}
    vmin = min(vals) if c["ymin"] is None else c["ymin"]
    vmax = max(vals) if c["ymax"] is None else c["ymax"]
    cbar_w = 4.0 if c["colorbar"] else 0.0
    left = max([geom.text_width_mm(str(l), size) for l in row_labels] + [6]) + 2.0
    top_off = 5.0 if c["title"] else 0.0
    top = rect.y + top_off
    label_h = min(18.0, max([geom.text_width_mm(str(l), size) for l in col_labels] + [6]) * 0.8)
    grid_w = rect.w - left - cbar_w - (6.0 if cbar_w else 2.0)
    grid_h = max(8.0, rect.h - top_off - label_h - 1.5)
    nr, nc = len(matrix), len(matrix[0])
    cw, chh = grid_w / nc, grid_h / nr
    for i, row in enumerate(matrix):
        for j, v in enumerate(row):
            if not isinstance(v, (int, float)):
                continue
            col = style.heat_color(v, vmin, vmax, c.get("cmap", "viridis"))
            x, y = left + j * cw, top + i * chh
            out.append(prims.rect(x, y, cw, chh, fill=col, stroke="#FFFFFF", sw=0.25,
                                  layer=layer, tag=f"cell:{row_labels[i]}:{col_labels[j]}", src=c.get("source", "")))
            if c.get("value_labels"):
                out.append(prims.text(x + cw / 2, y + chh / 2, geom.fmt_num(v), size=size * 0.85,
                                      fill=geom.readable_ink(col), layer=layer))
    for i, lab in enumerate(row_labels):
        out.append(prims.text(left - 1.2, top + chh * (i + 0.5), str(lab), size=size, anchor="end",
                              fill=ink, layer=layer, tag="rowlabel"))
    for j, lab in enumerate(col_labels):
        out.append(prims.text(left + cw * (j + 0.5), top + grid_h + 1.2, str(lab), size=size,
                              anchor="end", rotate=-40 if geom.text_width_mm(str(lab), size) > cw * 1.1 else 0,
                              fill=ink, layer=layer, tag="collabel"))
    if c["colorbar"]:
        bx = left + grid_w + 2.2
        steps = 12
        for k in range(steps):
            t = k / (steps - 1)
            v = vmin + t * (vmax - vmin)
            out.append(prims.rect(bx, top + grid_h * (1 - (k + 1) / steps), cbar_w, grid_h / steps + 0.05,
                                  fill=style.heat_color(v, vmin, vmax, c.get("cmap", "viridis")),
                                  stroke="none", layer=layer, tag="colorbar"))
        for t in [t for t in geom.nice_ticks(vmin, vmax, target=4) if vmin - 1e-9 <= t <= vmax + 1e-9]:
            y = top + grid_h * (1 - (t - vmin) / ((vmax - vmin) or 1))
            out.append(prims.text(bx + cbar_w + 0.8, y, geom.fmt_num(t), size=size * 0.9, anchor="start",
                                  fill=ink, layer=layer, tag="cbar:tick"))
        if c["colorbar_label"]:
            out.append(prims.text(bx + cbar_w + 8.0, top + grid_h / 2, c["colorbar_label"], size=size,
                                  rotate=-90, fill=ink, layer=layer))
    if c["title"]:
        out.append(prims.text(rect.x, rect.y + 2.4, c["title"], size=size, anchor="start",
                              weight="bold", fill=ink, layer=layer))
    return out, {"vmin": vmin, "vmax": vmax, "n_cols": nc, "n_rows": nr}
