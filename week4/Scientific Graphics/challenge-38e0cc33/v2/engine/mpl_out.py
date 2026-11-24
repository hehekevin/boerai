"""Matplotlib renderer: vector PDF (TrueType-embedded text) and raster PNG."""
from __future__ import annotations

import os
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

from . import geom  # noqa: E402
from .draw import Drawing  # noqa: E402


def _available_fonts() -> set[str]:
    return {f.name for f in font_manager.fontManager.ttflist}


CJK_CANDIDATES = ("Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC", "Noto Sans CJK HK",
                  "Source Han Sans SC", "Source Han Sans CN", "Droid Sans Fallback",
                  "AR PL UMing CN", "WenQuanYi Zen Hei", "Microsoft YaHei", "SimHei")


def resolve_font_stack(stack: list[str]) -> tuple[list[str], list[str]]:
    """Resolve the requested families, and make sure a CJK-capable face leads
    the list whenever one is installed under a different family name."""
    have = _available_fonts()
    found = [f for f in stack if f in have]
    missing = [f for f in stack if f not in have]
    if not found:
        found = ["DejaVu Sans"]
    if not any(supports_cjk(f) for f in found):
        for cand in CJK_CANDIDATES:
            if cand in have and supports_cjk(cand):
                found = [cand] + found
                break
    return found, missing


def supports_cjk(font_name: str) -> bool:
    try:
        path = font_manager.findfont(font_name, fallback_to_default=False)
    except Exception:
        return False
    try:
        from matplotlib.ft2font import FT2Font
        face = FT2Font(path)
        return face.get_char_index(ord("中")) != 0
    except Exception:
        return False


def _setup_rc(spec) -> dict:
    stack, missing = resolve_font_stack(spec.font_stack)
    cjk = [f for f in stack if supports_cjk(f)]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": stack,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": 0.0,
        "figure.facecolor": spec.background,
        "savefig.facecolor": spec.background,
        "pdf.compression": 6,
        "text.antialiased": True,
    })
    return {"font_stack_resolved": stack, "fonts_missing": missing,
            "cjk_capable_fonts": cjk, "cjk_ok": bool(cjk)}


def render(drawing: Drawing, spec, pdf_path: str | None, png_path: str | None,
           dpi: int | None = None) -> dict:
    info = _setup_rc(spec)
    W, H = spec.width_mm, spec.height_mm
    fig = plt.figure(figsize=(W / 25.4, H / 25.4), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    family = info["font_stack_resolved"][0]
    for p in drawing.prims:
        _draw_prim(ax, p, family)
    out: dict[str, Any] = {"renderer": "matplotlib", **info}
    if pdf_path:
        fig.savefig(pdf_path, format="pdf", facecolor=spec.background)
        out["pdf_bytes"] = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
    if png_path:
        fig.savefig(png_path, format="png", dpi=dpi or spec.dpi, facecolor=spec.background)
        out["png_bytes"] = os.path.getsize(png_path) if os.path.exists(png_path) else 0
        out["png_dpi"] = dpi or spec.dpi
    plt.close(fig)
    return out


def _draw_prim(ax, p: dict, family: str) -> None:
    kind = p["kind"]
    if kind == "rect":
        if p.get("rx"):
            patch = FancyBboxPatch((p["x"] + p["rx"], p["y"] + p["rx"]),
                                   max(0.01, p["w"] - 2 * p["rx"]), max(0.01, p["h"] - 2 * p["rx"]),
                                   boxstyle=f"round,pad={p['rx']},rounding_size={p['rx']}",
                                   linewidth=p["sw"], facecolor=p["fill"] if p["fill"] != "none" else "none",
                                   edgecolor=p["stroke"] if p["stroke"] != "none" else "none",
                                   alpha=p["opacity"], zorder=2)
        else:
            patch = Rectangle((p["x"], p["y"]), p["w"], p["h"], linewidth=p["sw"],
                              facecolor=p["fill"] if p["fill"] != "none" else "none",
                              edgecolor=p["stroke"] if p["stroke"] != "none" else "none",
                              alpha=p["opacity"], zorder=2)
        if p.get("dash"):
            patch.set_linestyle((0, (1.2, 0.9)))
        ax.add_patch(patch)
    elif kind == "line":
        ls = (0, (3.0, 2.2)) if p.get("dash") else "-"
        ax.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color=p["stroke"], linewidth=p["sw"],
                linestyle=ls, solid_capstyle="round", alpha=p["opacity"], zorder=3)
    elif kind == "poly":
        pts = p["pts"]
        if p["closed"]:
            patch = Polygon(pts, closed=True, linewidth=p["sw"],
                            facecolor=p["fill"] if p["fill"] != "none" else "none",
                            edgecolor=p["stroke"] if p["stroke"] != "none" else "none",
                            alpha=p["opacity"], zorder=3, joinstyle="round")
            if p.get("dash"):
                patch.set_linestyle((0, (1.2, 0.9)))
            ax.add_patch(patch)
        else:
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            ls = (0, (3.0, 2.2)) if p.get("dash") else "-"
            ax.plot(xs, ys, color=p["stroke"], linewidth=p["sw"], linestyle=ls,
                    solid_capstyle="round", solid_joinstyle="round", alpha=p["opacity"], zorder=3)
    elif kind == "circle":
        ax.add_patch(Circle((p["cx"], p["cy"]), p["r"], linewidth=p["sw"],
                            facecolor=p["fill"] if p["fill"] != "none" else "none",
                            edgecolor=p["stroke"] if p["stroke"] != "none" else "none",
                            alpha=p["opacity"], zorder=3))
    elif kind == "ellipse":
        ax.add_patch(Ellipse((p["cx"], p["cy"]), p["rx"] * 2, p["ry"] * 2, linewidth=p["sw"],
                             facecolor=p["fill"] if p["fill"] != "none" else "none",
                             edgecolor=p["stroke"] if p["stroke"] != "none" else "none",
                             alpha=p["opacity"], zorder=3))
    elif kind == "text":
        _draw_text(ax, p, family)


def _draw_text(ax, p: dict, family: str) -> None:
    ha = {"middle": "center", "end": "right", "start": "left"}.get(p["anchor"], "left")
    va = {"middle": "center", "top": "top", "bottom": "bottom"}.get(p["baseline"], "baseline")
    kw = {}
    if p.get("bg"):
        kw["bbox"] = dict(boxstyle="square,pad=0.18", facecolor="#FFFFFF", edgecolor="none", alpha=0.9)
    ax.text(p["x"], p["y"], p["text"], fontsize=p["size"], color=p["fill"], ha=ha, va=va,
            rotation=p.get("rotate", 0) or 0, rotation_mode="anchor",
            fontweight="bold" if p.get("weight") == "bold" else "normal",
            fontstyle="italic" if p.get("style") == "italic" else "normal",
            family=family, zorder=5, clip_on=False, **kw)
