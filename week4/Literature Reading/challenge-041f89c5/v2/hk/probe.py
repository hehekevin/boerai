"""Input discovery: what did the case actually give us?

The probe never trusts labels: it reads the real files, hashes them, and prints
a compact brief (keys, workorder sentences, file inventory) so the next step can
work from evidence instead of assumptions about the schema.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from typing import Any

TEXT_KEYS = ("task", "instruction", "prompt", "question", "workorder", "request", "description",
             "goal", "objective", "figure", "caption", "requirement", "constraint", "note",
             "spec", "rubric", "hint")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def guess_kind(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".pdf": "pdf", ".csv": "table", ".tsv": "table", ".xlsx": "spreadsheet", ".xls": "spreadsheet",
        ".docx": "document", ".doc": "document", ".md": "text", ".txt": "text", ".json": "json",
        ".yaml": "text", ".yml": "text", ".png": "image", ".jpg": "image", ".jpeg": "image",
        ".tif": "image", ".tiff": "image", ".svg": "vector", ".tex": "text", ".bib": "text",
        ".ipynb": "notebook", ".zip": "archive",
    }.get(ext, "other")


def walk_inputs(root: str) -> list[dict]:
    out = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(p)
                out.append({"path": p, "rel": os.path.relpath(p, root), "bytes": size,
                            "kind": guess_kind(p), "sha256": sha256_file(p) if size < 60_000_000 else ""})
            except OSError:
                continue
    return out


def _flatten(obj: Any, prefix: str = "", depth: int = 0, acc: list | None = None) -> list[dict]:
    acc = acc if acc is not None else []
    if depth > 4:
        return acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                acc.append({"key": key, "type": type(v).__name__, "n": len(v)})
                _flatten(v, key, depth + 1, acc)
            else:
                s = str(v)
                acc.append({"key": key, "type": type(v).__name__,
                            "value": s if len(s) <= 400 else s[:400] + "…"})
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:12]):
            key = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                acc.append({"key": key, "type": type(v).__name__, "n": len(v)})
                _flatten(v, key, depth + 1, acc)
            else:
                s = str(v)
                acc.append({"key": key, "type": type(v).__name__,
                            "value": s if len(s) <= 400 else s[:400] + "…"})
    return acc


def find_paths(obj: Any, base: str, acc: list | None = None, key: str = "") -> list[dict]:
    """Any string that looks like an existing input file."""
    acc = acc if acc is not None else []
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_paths(v, base, acc, str(k))
    elif isinstance(obj, list):
        for v in obj:
            find_paths(v, base, acc, key)
    elif isinstance(obj, str):
        s = obj.strip()
        cands = [s]
        if "," in s and len(s) < 400:
            cands += [x.strip() for x in s.split(",")]
        for cand in cands:
            for root in (base, os.path.dirname(base), "/input", os.getcwd()):
                p = cand if os.path.isabs(cand) else os.path.join(root, cand)
                if os.path.exists(p) and os.path.isfile(p):
                    acc.append({"key": key, "declared": obj, "resolved": os.path.abspath(p),
                                "bytes": os.path.getsize(p)})
                    break
    return acc


def probe(case_path: str, input_dir: str = "/input") -> dict:
    data: Any = {}
    source = case_path
    if case_path and os.path.exists(case_path):
        try:
            with open(case_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            data = {"_read_error": str(exc)}
    files = walk_inputs(input_dir)
    if os.path.abspath(os.path.dirname(case_path or "")) not in {os.path.abspath(input_dir),
                                                                 os.path.dirname(os.path.abspath(input_dir))}:
        files += walk_inputs(os.path.dirname(os.path.abspath(case_path or ".")))
    flat = _flatten(data) if isinstance(data, (dict, list)) else []
    texts = [f for f in flat if isinstance(f.get("value"), str) and len(f["value"]) > 80
             and any(k in f["key"].lower() for k in TEXT_KEYS)]
    if not texts:
        texts = [f for f in flat if isinstance(f.get("value"), str) and len(f["value"]) > 200]
    refs = find_paths(data, os.path.dirname(os.path.abspath(case_path or ".")))
    contract = {}
    if isinstance(data, dict):
        for key in ("output_contract", "outputContract", "contract", "expected_outputs", "deliverables"):
            if key in data:
                contract = {key: data[key]}
                break
    case_id = ""
    if isinstance(data, dict):
        for key in ("case_id", "caseId", "id", "case"):
            if isinstance(data.get(key), str):
                case_id = data[key]
                break
    return {
        "case_path": os.path.abspath(case_path) if case_path else "",
        "case_id": case_id,
        "top_level_keys": list(data.keys()) if isinstance(data, dict) else [],
        "flat": flat[:200],
        "text_fields": texts[:12],
        "file_refs": refs,
        "files": files,
        "output_contract": contract,
        "schema_guess": _schema_guess(data),
    }


def _schema_guess(data: Any) -> dict:
    guess = {"has_case_json": isinstance(data, (dict, list))}
    if isinstance(data, dict):
        keys = {str(k).lower() for k in data}
        guess["mentions_figure"] = any("figure" in k for k in keys)
        guess["mentions_output"] = any("output" in k or "deliver" in k for k in keys)
        guess["mentions_material"] = any(k in keys for k in ("materials", "inputs", "files", "sources", "attachments"))
    return guess


def brief(p: dict) -> str:
    lines = []
    lines.append(f"case: {p['case_id'] or '(no case_id field)'}   file: {p['case_path']}")
    lines.append(f"top-level keys: {', '.join(p['top_level_keys']) or '(none)'}")
    if p["output_contract"]:
        lines.append("output_contract: " + json.dumps(p["output_contract"], ensure_ascii=False)[:600])
    lines.append("")
    lines.append("input files:")
    for f in p["files"]:
        lines.append(f"  {f['rel']:<48} {f['kind']:<11} {f['bytes']:>9} B  sha256:{f['sha256'][:12]}")
    if p["file_refs"]:
        lines.append("")
        lines.append("file references resolved from case.json:")
        for r in p["file_refs"]:
            lines.append(f"  {r['key']}: {r['resolved']}")
    if p["text_fields"]:
        lines.append("")
        lines.append("long text fields (workorder candidates):")
        for t in p["text_fields"]:
            v = t["value"].replace("\n", " ")
            lines.append(f"  [{t['key']}] {v[:700]}")
    if p["flat"]:
        lines.append("")
        lines.append("scalar fields:")
        for f in p["flat"]:
            if "value" in f:
                v = str(f["value"]).replace("\n", " ")
                lines.append(f"  {f['key']} = {v[:160]}")
    return "\n".join(lines)
