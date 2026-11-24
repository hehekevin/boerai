"""FigForge command line.

  python -m engine.cli probe   --case /input/case.json --input /input --out work
  python -m engine.cli extract --work work
  python -m engine.cli build   --spec spec.json --out /app/output --work work
  python -m engine.cli verify  --spec spec.json
  python -m engine.cli demo    --out /app/output/demo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

from . import emit, export, extract, probe, verify as verify_mod
from .draw import Drawing
from .ir import Spec, load_spec
from .layout import Layout


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fit_canvas(spec: Spec, layout: Layout, log: str = "") -> Layout:
    """Shrink an unspecified canvas height to the content actually drawn."""
    canvas_raw = (spec.raw.get("canvas") or {})
    if canvas_raw.get("height_mm") is not None:
        return layout
    if str(canvas_raw.get("fit_content", "true")).lower() == "false":
        return layout
    for _ in range(2):
        core = layout.content_core_bottom()
        tail = 3.0
        if layout.legend_rect:
            tail += layout.legend_rect.h + 2.0
        if layout.caption_rect:
            tail += layout.caption_rect.h + 3.0
        target = max(45.0, core + tail)
        if abs(target - spec.height_mm) < 2.0:
            break
        spec.height_mm = round(target, 1)
        spec.raw.setdefault("canvas", {})["height_mm"] = spec.height_mm
        layout = Layout(spec)
        if log:
            emit.append_log(log, f"canvas fitted to content height {spec.height_mm} mm")
    return layout


def _source_texts(work: str) -> dict[str, str]:
    """All extracted material text, plus the case's own instruction text."""
    out: dict[str, str] = {}
    full = os.path.join(work, "materials_full.json") if work else ""
    if full and os.path.exists(full):
        data = _read_json(full)
        for i, m in enumerate(data.get("materials") or [], start=1):
            out[f"S{i}"] = m.get("text") or ""
    inputs = os.path.join(work, "inputs.json") if work else ""
    if inputs and os.path.exists(inputs):
        info = _read_json(inputs)
        for i, t in enumerate(info.get("text_fields") or [], start=1):
            out[f"case_text_{i}"] = str(t.get("value") or "")
        for c in (info.get("flat") or []):
            if "value" in c:
                out[f"case_{c['key']}"] = str(c["value"])
    return out


def _fmt_num(v: float) -> str:
    return f"{v:.6g}"


def _data_numbers(spec: Spec, work: str) -> set[str]:
    nums: set[str] = set()
    from .chart import table_rows
    for c in spec.charts:
        cats, groups, cells, records = table_rows(c)
        for d in cells.values():
            for key in ("value", "err", "n"):
                if d.get(key) is not None:
                    nums.add(_fmt_num(d[key]))
            for v in d.get("raw") or []:
                nums.add(_fmt_num(v))
        for row in c.get("matrix") or []:
            for v in row:
                if isinstance(v, (int, float)):
                    nums.add(_fmt_num(v))
        for v in c.get("values") or []:
            try:
                nums.add(_fmt_num(float(v)))
            except (TypeError, ValueError):
                pass
    # numbers that the spec itself quotes with evidence are already grounded
    for ev in spec.evidence.values():
        for tok in _num_tokens(ev.get("quote", "")):
            nums.add(tok)
    return nums


def _num_tokens(text: str) -> list[str]:
    import re
    return re.findall(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?(?![\w])", text or "")


def cmd_probe(args) -> int:
    os.makedirs(args.out, exist_ok=True)
    info = probe.probe(args.case, args.input)
    emit.write_json(os.path.join(args.out, "inputs.json"), info)
    text = probe.brief(info)
    with open(os.path.join(args.out, "brief.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0


def cmd_extract(args) -> int:
    work = args.work
    os.makedirs(work, exist_ok=True)
    inputs = _read_json(os.path.join(work, "inputs.json"))
    files, seen = [], set()
    for f in inputs.get("files") or []:
        if f["path"] in seen:
            continue
        seen.add(f["path"])
        files.append(f)
    result = extract.extract_all(files, work)
    emit.write_json(os.path.join(work, "materials.json"), result["summary"])
    emit.write_json(os.path.join(work, "materials_full.json"),
                    {"materials": [{k: v for k, v in m.items() if k != "data"} for m in result["materials"]]})
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"\ntext dumps: {result['text_dir']}")
    return 0


def cmd_build(args) -> int:
    t0 = time.time()
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    log = os.path.join(outdir, "run.log")
    emit.append_log(log, f"build start spec={args.spec} out={outdir}")
    spec = load_spec(args.spec)
    layout = _fit_canvas(spec, Layout(spec), log)
    drawing = Drawing(spec, layout)
    stem = args.stem or spec.figure_id or "figure"
    export_report = export.export_all(drawing, spec, outdir, stem, want_tiff=not args.no_tiff)
    texts = _source_texts(args.work) if args.work else {}
    case_id = ""
    if args.work and os.path.exists(os.path.join(args.work, "inputs.json")):
        case_id = str(_read_json(os.path.join(args.work, "inputs.json")).get("case_id") or "")
    vreport = verify_mod.verify(spec, drawing, layout, texts, _data_numbers(spec, args.work or ""),
                                case_id, [dict(i) for i in spec.issues])
    spec_copy = os.path.join(outdir, f"{stem}_spec.json")
    emit.write_json(spec_copy, spec.raw)

    artifacts = {
        "editable_source": {"path": export_report["artifacts"].get("svg", {}).get("path"),
                            "format": "SVG 1.1 (layered, live text, provenance attributes)",
                            "layers": export_report["artifacts"].get("svg", {}).get("layers", [])},
        "pdf": {"path": export_report["artifacts"].get("pdf", {}).get("path"),
                "format": "PDF (vector, TrueType-embedded text)"},
        "png": {"path": export_report["artifacts"].get("png", {}).get("path"),
                "format": "PNG", "dpi": export_report["artifacts"].get("png", {}).get("dpi")},
        "png_preview": {"path": export_report["artifacts"].get("png_preview", {}).get("path")},
        "tiff": {"path": export_report["artifacts"].get("tiff", {}).get("path")},
        "spec": {"path": spec_copy, "format": "JSON figure specification (single source of truth)"},
        "checks": {"path": os.path.join(outdir, f"{stem}_checks.json")},
        "provenance": {"path": os.path.join(outdir, f"{stem}_provenance.csv")},
        "report": {"path": os.path.join(outdir, f"{stem}_report.md")},
        "caption": spec.caption,
    }
    for key in list(artifacts):
        if isinstance(artifacts[key], dict) and not artifacts[key].get("path"):
            artifacts[key] = {"status": "not_produced", "path": None}
    emit.write_json(artifacts["checks"]["path"], vreport)
    emit.write_provenance(artifacts["provenance"]["path"], spec, emit.element_inventory(spec))

    case_meta = {}
    if args.work and os.path.exists(os.path.join(args.work, "inputs.json")):
        case_meta = _read_json(os.path.join(args.work, "inputs.json"))
    runtime = {"seconds": round(time.time() - t0, 2), "python": sys.version.split()[0],
               "cwd": os.getcwd(), "spec_path": os.path.abspath(args.spec)}
    artifacts["result"] = {"path": os.path.join(outdir, "result.json"),
                            "format": "JSON structured result"}
    result = emit.build_result(spec, export_report, vreport, artifacts, case_meta, runtime)
    result_path = os.path.join(outdir, "result.json")
    artifacts["result"] = {"path": result_path}
    result["artifacts"] = artifacts
    emit.write_json(result_path, result)
    emit.write_report(artifacts["report"]["path"], result, spec)
    emit.append_log(log, f"build done status={result['status']} checks={vreport['summary']} "
                         f"seconds={runtime['seconds']}")

    print(f"figure      : {stem}.svg / .pdf / .png")
    print(f"canvas      : {spec.width_mm}×{spec.height_mm} mm, {spec.dpi} dpi, preset={spec.preset}")
    print(f"elements    : {len(spec.nodes)} nodes, {len(spec.edges)} edges, {len(spec.charts)} charts")
    print(f"checks      : {vreport['summary']['pass']} pass / {vreport['summary']['warn']} warn / "
          f"{vreport['summary']['fail']} fail  -> {vreport['summary']['verdict']}")
    for c in vreport["checks"]:
        if c["status"] == "fail":
            print(f"  FAIL {c['id']}: {c['message']}  [fix: {c['fix']}]")
    ex = export_report["checks"]
    print("export      : " + ", ".join(f"{k}={v}" for k, v in ex.items() if k in
                                       ("pdf_present", "pdf_vector_text_embedded", "pdf_text_selectable",
                                        "png_dpi_ok", "svg_text_editable")))
    print(f"status      : {result['status']}")
    print(f"outputs     : {outdir}")
    if args.strict and vreport["summary"]["fail"]:
        return 2
    return 0


def cmd_verify(args) -> int:
    spec = load_spec(args.spec)
    layout = _fit_canvas(spec, Layout(spec))
    drawing = Drawing(spec, layout)
    texts = _source_texts(args.work) if args.work else {}
    v = verify_mod.verify(spec, drawing, layout, texts, _data_numbers(spec, args.work or ""),
                          spec_issues=[dict(i) for i in spec.issues])
    print(json.dumps(v["summary"], ensure_ascii=False))
    for c in v["checks"]:
        if c["status"] != "pass":
            print(f"{c['status'].upper():4} {c['id']}: {c['message']}")
    return 0 if v["summary"]["verdict"] != "fail" else 2


def cmd_table(args) -> int:
    """Print one extracted table as JSON rows, ready to paste into charts[].data.rows."""
    path = os.path.join(args.work, "materials_full.json")
    if not os.path.exists(path):
        print("no materials_full.json; run `extract` first")
        return 1
    data = _read_json(path)
    tables = [m for m in data.get("materials") or [] if m.get("kind") == "table"]
    if not tables:
        print("no table material found")
        return 1
    if args.list:
        for i, m in enumerate(tables, start=1):
            header = m.get("header") or []
            print(f"[{i}] {m.get('rel')}  rows={m.get('n_rows')}  columns={header}")
        return 0
    idx = max(1, min(args.index, len(tables)))
    m = tables[idx - 1]
    payload = {"rel": m.get("rel"), "header": m.get("header"), "units_hint": m.get("units_hint"),
               "rows": (m.get("rows") or [])[: args.limit]}
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


def cmd_demo(args) -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example = os.path.join(here, "examples", "example_spec.json")
    spec = load_spec(example)
    os.makedirs(args.out, exist_ok=True)
    layout = _fit_canvas(spec, Layout(spec))
    drawing = Drawing(spec, layout)
    rep = export.export_all(drawing, spec, args.out, "example_figure", want_tiff=False)
    v = verify_mod.verify(spec, drawing, layout, {}, set())
    print(json.dumps({"artifacts": {k: (v2.get("path") if isinstance(v2, dict) else v2)
                                    for k, v2 in rep["artifacts"].items()},
                      "checks": v["summary"]}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="figforge", description="Source-bound scientific figure engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="inspect case.json and the input directory")
    p.add_argument("--case", default="/input/case.json")
    p.add_argument("--input", default="/input")
    p.add_argument("--out", default="work")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("extract", help="extract text and tables with locators")
    p.add_argument("--work", default="work")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("build", help="render, export, verify and emit result.json")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default="/app/output")
    p.add_argument("--work", default="work")
    p.add_argument("--stem", default="")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--no-tiff", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("verify", help="run the consistency checks only")
    p.add_argument("--spec", required=True)
    p.add_argument("--work", default="work")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("table", help="print an extracted table as JSON rows")
    p.add_argument("--work", default="work")
    p.add_argument("--index", type=int, default=1)
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("demo", help="render the shipped example spec")
    p.add_argument("--out", default="demo_out")
    p.set_defaults(func=cmd_demo)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
