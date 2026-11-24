"""Geometry, units and text metrics for FigForge.

Internal coordinate system: millimetres, origin at top-left, y increases downward.
Font sizes are stored in points, converted to mm with PT2MM when geometry is needed.
"""
from __future__ import annotations

import math
import re

PT2MM = 25.4 / 72.0
MM2PT = 72.0 / 25.4


def mm2pt(v: float) -> float:
    return v * MM2PT


def pt2mm(v: float) -> float:
    return v * PT2MM


# --- text metrics -----------------------------------------------------------
# Helvetica/Arial advance widths (1/1000 em) for the printable ASCII range.
_ASCII_W = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, "0": 556, "1": 556, "2": 556, "3": 556, "4": 556,
    "5": 556, "6": 556, "7": 556, "8": 556, "9": 556, ":": 278, ";": 278,
    "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015, "A": 667, "B": 667,
    "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722, "I": 278,
    "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667,
    "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 278, "\\": 278, "]": 278, "^": 469,
    "_": 556, "`": 333, "a": 556, "b": 556, "c": 500, "d": 556, "e": 556,
    "f": 278, "g": 556, "h": 556, "i": 222, "j": 222, "k": 500, "l": 222,
    "m": 833, "n": 556, "o": 556, "p": 556, "q": 556, "r": 333, "s": 500,
    "t": 278, "u": 556, "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "{": 334, "|": 260, "}": 334, "~": 584,
}

_WIDE = set("，。、；：？！（）【】《》“”‘’…—－·　")


def _char_em(ch: str) -> float:
    if ch in _WIDE:
        return 1.0
    code = ord(ch)
    if code < 128:
        return _ASCII_W.get(ch, 556) / 1000.0
    # CJK / full-width forms
    if 0x2E80 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF or 0xFF00 <= code <= 0xFFEF:
        return 1.0
    if 0x0370 <= code <= 0x03FF:  # greek
        return 0.60
    return 0.62


def text_width_mm(text: str, size_pt: float, tracking: float = 0.0) -> float:
    """Approximate rendered width of a single-line string, in millimetres."""
    em = sum(_char_em(c) for c in text) + tracking * max(0, len(text) - 1)
    return em * size_pt * PT2MM


def string_width_units(text: str, size_pt: float) -> float:
    """Approximate width with size expressed in the same unit as the result."""
    return sum(_char_em(c) for c in text) * size_pt


def wrap_text(text: str, max_width_mm: float, size_pt: float, max_lines: int = 0) -> list[str]:
    """Greedy wrap that works for space-delimited text and for CJK runs."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []
    max_width_mm = max_width_mm * 0.97
    if text_width_mm(text, size_pt) <= max_width_mm:
        return [text]
    tokens: list[str] = []
    buf = ""
    for ch in text:
        is_cjk = _char_em(ch) >= 0.99 and ch not in " "
        if ch == " ":
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(" ")
        elif is_cjk:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        else:
            buf += ch
    if buf:
        tokens.append(buf)

    lines: list[str] = []
    cur = ""
    for tok in tokens:
        cand = cur + tok
        if text_width_mm(cand.rstrip(), size_pt) <= max_width_mm or not cur:
            cur = cand
        else:
            lines.append(cur.strip())
            cur = "" if tok == " " else tok
    if cur.strip():
        lines.append(cur.strip())
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and text_width_mm(last + "…", size_pt) > max_width_mm:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


GLYPH_FALLBACK = {
    "\u2212": "-", "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...",
    "\u00a0": " ", "\u2009": " ", "\u200a": " ", "\u202f": " ", "\u200b": "",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u21d2": "=>", "\u2265": ">=",
    "\u2264": "<=", "\u2260": "!=", "\u00b7": "\u00b7",
}


def sanitize(text: str) -> tuple[str, list[str]]:
    """Replace characters a sans-serif stack often lacks with safe equivalents."""
    subs = []
    out = []
    for ch in str(text):
        if ch in GLYPH_FALLBACK:
            out.append(GLYPH_FALLBACK[ch])
            subs.append(ch)
        else:
            out.append(ch)
    return "".join(out), subs


# --- rectangles -------------------------------------------------------------
class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float):
        self.x, self.y, self.w, self.h = float(x), float(y), float(w), float(h)

    @property
    def x1(self) -> float:
        return self.x + self.w

    @property
    def y1(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def union(self, other: "Rect") -> "Rect":
        x0 = min(self.x, other.x)
        y0 = min(self.y, other.y)
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        return Rect(x0, y0, x1 - x0, y1 - y0)

    def expand(self, pad: float) -> "Rect":
        return Rect(self.x - pad, self.y - pad, self.w + 2 * pad, self.h + 2 * pad)

    def intersects(self, other: "Rect", tol: float = 0.0) -> bool:
        return not (
            self.x1 - tol <= other.x
            or other.x1 - tol <= self.x
            or self.y1 - tol <= other.y
            or other.y1 - tol <= self.y
        )

    def contains_center(self, other: "Rect") -> bool:
        return self.x <= other.cx <= self.x1 and self.y <= other.cy <= self.y1

    def as_list(self) -> list[float]:
        return [round(self.x, 3), round(self.y, 3), round(self.w, 3), round(self.h, 3)]

    def __repr__(self) -> str:  # pragma: no cover
        return f"Rect({self.x:.1f},{self.y:.1f},{self.w:.1f},{self.h:.1f})"


def clip_to_rect(rect: Rect, px: float, py: float, tx: float, ty: float, pad: float = 0.0,
                 far: bool = True) -> tuple[float, float]:
    """Intersection of the segment (px,py)->(tx,ty) with the boundary of rect(pad).

    far=True returns the exit point of the rectangle the segment starts in;
    far=False returns the entry point of a rectangle the segment ends in.
    """
    r = rect.expand(pad)
    dx, dy = tx - px, ty - py
    if dx == 0 and dy == 0:
        return px, py
    ts: list[float] = []
    if dx:
        for xb in (r.x, r.x1):
            t = (xb - px) / dx
            if 0 <= t <= 1:
                y = py + t * dy
                if r.y - 1e-6 <= y <= r.y1 + 1e-6:
                    ts.append(t)
    if dy:
        for yb in (r.y, r.y1):
            t = (yb - py) / dy
            if 0 <= t <= 1:
                x = px + t * dx
                if r.x - 1e-6 <= x <= r.x1 + 1e-6:
                    ts.append(t)
    if not ts:
        return px, py
    t = (max(ts) if far else min(ts)) if (tx, ty) != (px, py) else min(ts)
    return px + t * dx, py + t * dy


def nice_ticks(vmin: float, vmax: float, target: int = 5) -> list[float]:
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        return [0.0, 1.0]
    if vmax < vmin:
        vmin, vmax = vmax, vmin
    if abs(vmax - vmin) < 1e-12:
        vmax = vmin + (abs(vmin) * 0.1 or 1.0)
    
    raw = (vmax - vmin) / max(1, target)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if (vmax - vmin) / step <= target:
            break
    lo = math.floor(vmin / step) * step
    hi = math.ceil(vmax / step) * step
    n = int(round((hi - lo) / step))
    if n > 50:
        step *= 2
        lo = math.floor(vmin / step) * step
        n = int(round((hi - lo) / step))
    return [round(lo + i * step, 10) for i in range(n + 1)]


def fmt_num(v: float, sig: int = 3) -> str:
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e4 or a < 1e-3:
        s = f"{v:.{max(0, sig - 1)}e}"
        mant, exp = s.split("e")
        return f"{mant}×10^{int(exp)}"
    if a >= 100:
        s = f"{v:.0f}"
    elif a >= 10:
        s = f"{v:.1f}"
    elif a >= 1:
        s = f"{v:.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s


def hex_to_rgb(color: str) -> tuple[float, float, float]:
    c = (color or "#000000").strip()
    if c.startswith("#"):
        c = c[1:]
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return (0.0, 0.0, 0.0)
    return tuple(int(c[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def mix(c1: str, c2: str, t: float) -> str:
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#" + "".join(f"{int(round((a[i] * (1 - t) + b[i] * t) * 255)):02X}" for i in range(3))


def luminance(color: str) -> float:
    r, g, b = hex_to_rgb(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_ink(fill: str, dark: str = "#111111", light: str = "#FFFFFF") -> str:
    return dark if luminance(fill) > 0.55 else light
