#!/usr/bin/env python3
"""Build every bundled example and print a one-line verdict per figure.

Used as a smoke test after installation: it exercises the same code path the
real cases use (spec -> layout -> SVG/PDF/PNG -> checks), without any network.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import export, verify  # noqa: E402
from engine.draw import Drawing  # noqa: E402
from engine.ir import load_spec  # noqa: E402
from engine.layout import Layout  # noqa: E402

EXAMPLES = [
    "examples/example_spec.json",
    "examples/example_relationship.json",
    "examples/example_chart.json",
    "examples/example_apparatus.json",
    "examples/example_graphical_abstract.json",
]


def main() -> int:
    outroot = tempfile.mkdtemp(prefix="figforge-selftest-")
    rows = []
    failed = 0
    for rel in EXAMPLES:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            rows.append((rel, "-", "-", "-", "missing"))
            failed += 1
            continue
        spec = load_spec(path)
        layout = Layout(spec)
        drawing = Drawing(spec, layout)
        outdir = os.path.join(outroot, os.path.splitext(os.path.basename(rel))[0])
        rep = export.export_all(drawing, spec, outdir, "figure", want_tiff=False)
        texts = {}
        for src in spec.sources:
            rel_path = str(src.get("path") or "")
            cand = os.path.join(HERE, rel_path)
            if os.path.exists(cand) and not cand.endswith(".pdf"):
                try:
                    texts[src["id"]] = open(cand, encoding="utf-8").read()
                except (OSError, UnicodeDecodeError):
                    pass
        v = verify.verify(spec, drawing, layout, texts, set())
        ex = rep["checks"]
        ok = (v["summary"]["fail"] == 0 and ex.get("pdf_present") and ex.get("png_present"))
        if not ok:
            failed += 1
        rows.append((os.path.basename(rel), f"{spec.width_mm:.0f}x{spec.height_mm:.0f}",
                     f"{v['summary']['pass']}/{v['summary']['warn']}/{v['summary']['fail']}",
                     "yes" if ex.get("pdf_text_selectable") else "no",
                     "ok" if ok else "check"))
    width = max(len(r[0]) for r in rows)
    print(f"{'example'.ljust(width)}  canvas    pass/warn/fail  pdf-text  verdict")
    for r in rows:
        print(f"{r[0].ljust(width)}  {r[1]:<8}  {r[2]:<14}  {r[3]:<8}  {r[4]}")
    print(f"\nartifacts: {outroot}")
    print(f"{len(rows) - failed}/{len(rows)} examples built cleanly")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
