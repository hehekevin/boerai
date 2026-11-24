"""Colour, typography and arrow-style policy.

All colours are colour-blind safe (Okabe-Ito derived) and remain distinguishable
in greyscale printing; every categorical assignment is deterministic, so a
legend, a bar series and a node of the same category always get the same colour.
"""
from __future__ import annotations

from . import geom

OKABE_ITO = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#8C564B",  # brown
    "#7F7F7F",  # grey
]

MUTED = ["#4E79A7", "#F28E2B", "#59A14F", "#B07AA1", "#76B7B2", "#EDC948", "#9C755F", "#BAB0AC"]

PASTEL_FILLS = ["#E8F1F8", "#FBEDE3", "#E6F4EE", "#F7EAF1", "#FDF3E0", "#EAF4FB", "#F1ECE9", "#F2F2F2"]

SEMANTIC = {
    "activate": "#0072B2",
    "promote": "#0072B2",
    "upregulate": "#0072B2",
    "inhibit": "#D55E00",
    "repress": "#D55E00",
    "bind": "#009E73",
    "modify": "#CC79A7",
    "phosphorylate": "#CC79A7",
    "transport": "#E69F00",
    "translocate": "#E69F00",
    "flow": "#595959",
    "sequence": "#595959",
    "connect": "#7F7F7F",
    "contain": "#BFBFBF",
    "part_of": "#BFBFBF",
    "catalyze": "#009E73",
    "convert": "#56B4E9",
    "signal": "#8C564B",
    "associate": "#8C564B",
    "secrete": "#E69F00",
    "complex": "#009E73",
}

# Arrow end style per relation type: filled head = positive/flow,
# flat T-bar = negative, open diamond = binding, none = structural.
END_STYLE = {
    "activate": "arrow", "promote": "arrow", "upregulate": "arrow",
    "inhibit": "bar", "repress": "bar", "bind": "diamond",
    "complex": "none", "modify": "arrow", "phosphorylate": "arrow",
    "transport": "arrow", "translocate": "arrow", "secrete": "arrow",
    "flow": "arrow", "sequence": "arrow", "contain": "none",
    "part_of": "none", "catalyze": "arrow", "convert": "arrow",
    "connect": "none", "signal": "arrow", "associate": "none",
}

# Class -> (fill, stroke) for entity boxes.
CLASS_STYLE = {
    "gene": ("#E6F4EE", "#009E73"),
    "protein": ("#E8F1F8", "#0072B2"),
    "receptor": ("#E8F1F8", "#0072B2"),
    "kinase": ("#E8F1F8", "#0072B2"),
    "complex": ("#EAF4FB", "#56B4E9"),
    "ligand": ("#FDF3E0", "#E69F00"),
    "metabolite": ("#FDF3E0", "#E69F00"),
    "ion": ("#FDF3E0", "#E69F00"),
    "cell": ("#F7EAF1", "#CC79A7"),
    "cell_type": ("#F7EAF1", "#CC79A7"),
    "organelle": ("#F7EAF1", "#CC79A7"),
    "nucleus": ("#F7EAF1", "#CC79A7"),
    "tissue": ("#F7EAF1", "#CC79A7"),
    "organism": ("#F7EAF1", "#CC79A7"),
    "process": ("#F2F2F2", "#666666"),
    "step": ("#F2F2F2", "#666666"),
    "stage": ("#F2F2F2", "#666666"),
    "phenotype": ("#F1ECE9", "#8C564B"),
    "condition": ("#F2F2F2", "#666666"),
    "instrument": ("#F2F2F2", "#4E79A7"),
    "device": ("#F2F2F2", "#4E79A7"),
    "component": ("#F2F2F2", "#4E79A7"),
    "material": ("#F1ECE9", "#8C564B"),
    "sample": ("#F1ECE9", "#8C564B"),
    "reagent": ("#F1ECE9", "#8C564B"),
    "data": ("#EAF4FB", "#56B4E9"),
    "concept": ("#FFFFFF", "#333333"),
    "entity": ("#FFFFFF", "#333333"),
}


def category_colors(n: int, palette: str = "okabe_ito") -> list[str]:
    base = OKABE_ITO if palette in {"", "okabe_ito", "okabe-ito"} else MUTED
    if n <= len(base):
        return base[:n]
    out = list(base)
    while len(out) < n:
        out.append(base[(len(out)) % len(base)])
    return out[:n]


def color_for(key: str, names: list[str], palette: str = "okabe_ito") -> str:
    cols = category_colors(max(1, len(names)), palette)
    try:
        return cols[names.index(key) % len(cols)]
    except ValueError:
        return cols[0]


def class_colors(cls: str) -> tuple[str, str]:
    return CLASS_STYLE.get(cls.lower(), CLASS_STYLE["entity"])


def heat_color(v: float, vmin: float, vmax: float, cmap: str = "viridis") -> str:
    """Sequential ramp that also reads correctly in greyscale."""
    if vmax <= vmin:
        t = 0.5
    else:
        t = (v - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    if cmap in {"blue", "blues"}:
        stops = ["#F7FBFF", "#C6DBEF", "#6BAED6", "#2171B5", "#08306B"]
    elif cmap in {"diverging", "rdbu"}:
        stops = ["#2166AC", "#92C5DE", "#F7F7F7", "#F4A582", "#B2182B"]
    else:
        stops = ["#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725"]
    pos = t * (len(stops) - 1)
    i = int(pos)
    if i >= len(stops) - 1:
        return stops[-1]
    return geom.mix(stops[i], stops[i + 1], pos - i)


def line_width_mm(spec) -> float:
    return geom.pt2mm(spec.line_pt)


def arrow_width_mm(spec, edge_type: str) -> float:
    base = geom.pt2mm(spec.line_pt)
    if edge_type in {"contain", "part_of", "associate", "connect"}:
        return base * 0.9
    if edge_type in {"inhibit", "repress"}:
        return base * 1.15
    return base * 1.05
