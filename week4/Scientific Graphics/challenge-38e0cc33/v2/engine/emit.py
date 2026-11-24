"""Structured result emission: result.json, provenance.csv, report.md, run.log."""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
from typing import Any

ENGINE = "FigForge"

CONTRACT_PATTERNS = {
    "editable_source": ("editable_source", "source_file", "svg", "editable", "source"),
    "pdf": ("pdf",),
    "png": ("png", "image", "figure", "raster"),
    "tiff": ("tif", "tiff"),
    "result": ("result", "manifest", "answer", "submission"),
    "caption": ("caption", "legend_text"),
    "provenance": ("provenance", "evidence", "trace", "source_map"),
    "report": ("report", "summary", "notes"),
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_contract(contract: Any, artifacts: dict) -> dict:
    """Mirror whatever keys the case declared, resolved to real artifact paths."""
    out: dict[str, Any] = {}
    if not contract:
        return out
    keys: list[str] = []
    if isinstance(contract, dict):
        if "output_contract" in contract and isinstance(contract["output_contract"], dict):
            keys = list(contract["output_contract"].keys())
        else:
            keys = list(contract.keys())
        template = contract.get("output_contract", contract)
    elif isinstance(contract, list):
        for item in contract:
            if isinstance(item, str):
                keys.append(item)
            elif isinstance(item, dict):
                keys += [str(item.get("name") or item.get("field") or item.get("key") or "")]
        template = {}
    else:
        return out
    for key in keys:
        if not key:
            continue
        low = key.lower()
        val: Any = None
        if "editable" in low or "source" in low or "svg" in low:
            val = artifacts.get("editable_source")
        elif "pdf" in low:
            val = artifacts.get("pdf")
        elif "tiff" in low or "tif" in low:
            val = artifacts.get("tiff")
        elif "png" in low or "image" in low or "figure" in low or "preview" in low:
            val = artifacts.get("png")
        elif "png" in low:
            val = artifacts.get("png")
        elif "provenance" in low or "evidence" in low or "trace" in low or "mapping" in low:
            val = artifacts.get("provenance")
        elif "caption" in low:
            val = artifacts.get("caption")
        elif "report" in low or "summary" in low or "note" in low:
            val = artifacts.get("report")
        elif "result" in low or "manifest" in low or "answer" in low:
            val = artifacts.get("result")
        if val is None:
            val = {"status": "not_produced", "reason": f"no artifact matched contract key '{key}'",
                   "see": "artifacts"}
        out[key] = val
    return out


def _ev(spec, key: str) -> dict:
    ev = dict(spec.evidence.get(key) or {})
    if ev and key:
        ev.setdefault("id", key)
    return ev


def element_inventory(spec) -> list[dict]:
    inv = []
    for n in spec.nodes:
        ev = _ev(spec, n["source"])
        inv.append({"element": f"node:{n['id']}", "type": "node", "label": n["label"],
                    "class": n["class"], "evidence": ev or {"status": "untraced"}})
    for e in spec.edges:
        ev = _ev(spec, e["source"])
        inv.append({"element": f"edge:{e['id']}", "type": f"relation:{e['type']}",
                    "label": f"{e['from']}->{e['to']}" + (f" [{e['label']}]" if e["label"] else ""),
                    "evidence": ev or {"status": "untraced"}})
    for c in spec.charts:
        ev = _ev(spec, c["source"])
        inv.append({"element": f"chart:{c['id']}", "type": f"chart:{c['type']}",
                    "label": f"{c.get('xlabel') or c.get('x')} vs {c.get('ylabel') or c.get('y')}",
                    "evidence": ev or {"status": "untraced"}})
    return inv


def data_mapping(spec) -> list[dict]:
    from .chart import table_rows
    rows_out = []
    for c in spec.charts:
        cats, groups, cells, records = table_rows(c)
        for (cat, grp), d in cells.items():
            rows_out.append({"chart": c["id"], "category": cat, "series": grp,
                             "field_x": c.get("x"), "field_y": c.get("y"),
                             "value": d.get("value"), "error": d.get("err"), "n": d.get("n"),
                             "mark": f"bar:{cat}:{grp}" if c["type"] == "bar" else f"pt:{cat}:{grp}"})
        if c["type"] == "heatmap" and c.get("matrix"):
            for i, row in enumerate(c["matrix"]):
                for j, v in enumerate(row):
                    rows_out.append({"chart": c["id"], "row": (c.get("row_labels") or [])[i] if i < len(c.get("row_labels") or []) else i,
                                     "col": (c.get("col_labels") or [])[j] if j < len(c.get("col_labels") or []) else j,
                                     "value": v, "mark": f"cell:{i}:{j}"})
    return rows_out


def write_provenance(path: str, spec, inventory: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["element", "type", "label", "evidence_id", "source_file", "locator", "quote"])
        for item in inventory:
            ev = item.get("evidence") or {}
            w.writerow([item["element"], item["type"], item["label"],
                        ev.get("id", ""), ev.get("source", ""), ev.get("locator", ""),
                        (ev.get("quote", "") or "").replace("\n", " ")[:500]])


def build_result(spec, export_report: dict, verify_report: dict, artifacts: dict,
                 case_meta: dict | None = None, runtime: dict | None = None,
                 status: str | None = None) -> dict:
    case_meta = case_meta or {}
    inv = element_inventory(spec)
    vsum = verify_report.get("summary", {})
    ex_checks = export_report.get("checks", {})
    failed_export = [k for k, v in ex_checks.items() if v is False]
    if status is None:
        status = "success"
        if vsum.get("verdict") == "fail" or failed_export:
            status = "partial"
        if not spec.nodes and not spec.charts:
            status = "failed"
    limits = []
    for k in failed_export:
        limits.append(f"export check failed: {k}")
    if not ex_checks.get("cjk_font_available", True):
        limits.append("no CJK-capable font in the environment; CJK glyphs may not render")
    for c in verify_report.get("checks", []):
        if c["status"] == "fail":
            limits.append(f"{c['id']}: {c['message']}")
    out = {
        "case_id": spec.case_id,
        "figure_id": spec.figure_id,
        "figure_kind": spec.figure_kind,
        "status": status,
        "generated_at": _now(),
        "engine": {"name": ENGINE, "spec_version": "1.0"},
        "output_contract": resolve_contract(case_meta.get("output_contract"), artifacts),
        "artifacts": artifacts,
        "figure_summary": {
            "title": spec.title,
            "caption": spec.caption,
            "canvas_mm": [spec.width_mm, spec.height_mm],
            "preset": spec.preset,
            "panels": [p["id"] for p in spec.panels],
            "counts": {"nodes": len(spec.nodes), "edges": len(spec.edges),
                       "containers": len(spec.containers), "charts": len(spec.charts),
                       "legend_items": len(spec.legend["items"]),
                       "panels": len(spec.panels)},
            "relation_types": sorted({e["type"] for e in spec.edges}),
        },
        "element_inventory": inv,
        "data_mapping": data_mapping(spec),
        "checks": verify_report,
        "export_report": {k: v for k, v in export_report.items() if k != "artifacts"},
        "sources": spec.sources,
        "evidence": spec.evidence,
        "uncertainty": spec.uncertainty,
        "changes": spec.changes,
        "limits": limits,
        "runtime": runtime or {},
        "case_meta": {k: v for k, v in case_meta.items() if k not in {"flat", "files"}},
    }
    return out


def write_report(path: str, result: dict, spec) -> None:
    r = result
    lines = [f"# {spec.title or spec.figure_id}", ""]
    lines.append(f"* case_id: `{r['case_id']}`  figure: `{r['figure_id']}`  kind: `{r['figure_kind']}`")
    lines.append(f"* status: **{r['status']}**  canvas: {r['figure_summary']['canvas_mm'][0]}×"
                 f"{r['figure_summary']['canvas_mm'][1]} mm ({spec.preset}), {spec.dpi} dpi")
    c = r["figure_summary"]["counts"]
    lines.append(f"* elements: {c['nodes']} nodes, {c['edges']} relations, {c['containers']} groups, "
                 f"{c['charts']} charts, {c['legend_items']} legend items")
    lines += ["", "## Artifacts", ""]
    for key, val in (r["artifacts"] or {}).items():
        if isinstance(val, dict) and val.get("path"):
            lines.append(f"* {key}: `{os.path.basename(val['path'])}` "
                         f"({val.get('bytes', val.get('pdf_bytes', ''))} B)")
    lines += ["", "## Checks", ""]
    for chk in r["checks"]["checks"]:
        mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[chk["status"]]
        lines.append(f"* [{mark}] {chk['id']}: {chk['message']}")
    lines += ["", "## Export", ""]
    for k, v in (r["export_report"].get("checks") or {}).items():
        lines.append(f"* {k}: {v}")
    if r["limits"]:
        lines += ["", "## Limits and open issues", ""]
        for l in r["limits"]:
            lines.append(f"* {l}")
    if r["uncertainty"]:
        lines += ["", "## Uncertainty declared in the spec", ""]
        for u in r["uncertainty"]:
            lines.append(f"* {u}")
    lines += ["", "## Sources", ""]
    for s in spec.sources:
        lines.append(f"* {s['id']}: `{s['path']}` sha256 `{(s['sha256'] or '')[:16]}`")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def append_log(path: str, message: str) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"[{_now()}] {message}\n")
