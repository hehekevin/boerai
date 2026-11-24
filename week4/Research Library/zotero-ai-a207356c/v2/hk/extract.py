"""Material extraction with locators.

Every block of text keeps a locator (PDF page, slide, sheet row range, line
number) so that an element in the figure can cite the exact place it came from.
Tables are parsed into typed rows, because chart values must be read from data,
never re-typed by hand.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from .probe import sha256_file


def _run(cmd: list[str], timeout: int = 180) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, p.stdout if p.returncode == 0 else (p.stdout + p.stderr)
    except Exception as exc:
        return False, str(exc)


# ------------------------------------------------------------------- PDF
def read_pdf(path: str) -> dict:
    out: dict[str, Any] = {"kind": "pdf", "blocks": [], "text": "", "pages": 0, "engine": ""}
    pages = 0
    info_ok, info = _run(["pdfinfo", path])
    if info_ok:
        m = re.search(r"Pages:\s+(\d+)", info)
        pages = int(m.group(1)) if m else 0
    if shutil.which("pdftotext"):
        ok, txt = _run(["pdftotext", "-layout", "-enc", "UTF-8", path, "-"])
        if ok and txt.strip():
            out["engine"] = "pdftotext -layout"
            out["text"] = txt
            out["blocks"] = _pdf_blocks(txt)
            out["pages"] = pages or len(out["blocks"])
            return out
    for mod in ("pypdf", "PyPDF2", "fitz"):
        try:
            if mod == "fitz":
                import fitz  # type: ignore
                doc = fitz.open(path)
                blocks = []
                for i, page in enumerate(doc):
                    t = page.get_text("text")
                    blocks.append({"loc": f"p.{i + 1}", "text": t})
                out.update(engine="pymupdf", blocks=blocks, pages=len(blocks),
                           text="\n".join(b["text"] for b in blocks))
                return out
            mod_obj = __import__(mod)
            reader = mod_obj.PdfReader(path)
            blocks = []
            for i, page in enumerate(reader.pages):
                blocks.append({"loc": f"p.{i + 1}", "text": page.extract_text() or ""})
            out.update(engine=mod, blocks=blocks, pages=len(blocks),
                       text="\n".join(b["text"] for b in blocks))
            return out
        except Exception:
            continue
    out["error"] = "no PDF text engine available (pdftotext/pypdf/pymupdf)"
    return out


def _pdf_blocks(txt: str) -> list[dict]:
    blocks = []
    for i, page in enumerate(txt.split("\f")):
        if not page.strip():
            continue
        blocks.append({"loc": f"p.{i + 1}", "text": page})
    return blocks


# ---------------------------------------------------------------- tables
def read_table(path: str, max_rows: int = 5000) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".csv", ".tsv"}:
        raw = open(path, "r", encoding="utf-8-sig", errors="replace").read()
        sample = raw[:8000]
        delim = ","
        if ext == ".tsv" or sample.count("\t") > sample.count(","):
            delim = "\t"
        else:
            try:
                delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except Exception:
                delim = ","
        rows = list(csv.reader(io.StringIO(raw), delimiter=delim))
        rows = rows[:max_rows]
    elif ext in {".xlsx", ".xlsm"}:
        return read_xlsx(path, max_rows)
    else:
        return {"kind": "table", "error": f"unsupported table type {ext}"}
    header = [h.strip() for h in rows[0]] if rows else []
    body = rows[1:] if rows else []
    typed = []
    for r in body:
        row = {}
        for i, h in enumerate(header):
            if not h:
                continue
            v = r[i].strip() if i < len(r) else ""
            row[h] = _coerce(v)
        if any(v not in (None, "") for v in row.values()):
            typed.append(row)
    return {"kind": "table", "header": header, "rows": typed,
            "n_rows": len(typed), "units_hint": _units_hint(header)}


def _coerce(v: str) -> Any:
    if v == "":
        return None
    s = v.replace("−", "-").strip()
    if re.fullmatch(r"[-+]?\d+", s):
        try:
            return int(s)
        except ValueError:
            return s
    if re.fullmatch(r"[-+]?\d*\.\d+([eE][-+]?\d+)?", s) or re.fullmatch(r"[-+]?\d+[eE][-+]?\d+", s):
        try:
            return float(s)
        except ValueError:
            return s
    return v


def _units_hint(header: list[str]) -> dict[str, str]:
    hint = {}
    for h in header:
        m = re.search(r"[\(\[]([^\)\]]+)[\)\]]", h or "")
        if m:
            hint[h] = m.group(1).strip()
    return hint


def read_xlsx(path: str, max_rows: int = 5000) -> dict:
    try:
        import openpyxl  # type: ignore
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        sheets = []
        for ws in wb.worksheets:
            rows = []
            for r in ws.iter_rows(values_only=True):
                rows.append(["" if c is None else c for c in r])
                if len(rows) > max_rows:
                    break
            sheets.append({"name": ws.title, "rows": rows})
        return _sheets_to_table(sheets)
    except Exception:
        pass
    try:
        return _sheets_to_table(_xlsx_minimal(path))
    except Exception as exc:
        return {"kind": "table", "error": f"xlsx unreadable: {exc}"}


def _xlsx_minimal(path: str) -> list[dict]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(
                    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        names = [s.get("name") for s in wb.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")]
        sheets = []
        for i, name in enumerate(names, start=1):
            fn = f"xl/worksheets/sheet{i}.xml"
            if fn not in z.namelist():
                continue
            root = ET.fromstring(z.read(fn))
            rows = []
            for row in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                vals = {}
                for c in row:
                    ref = c.get("r", "")
                    col = re.match(r"([A-Z]+)", ref)
                    idx = _col_index(col.group(1)) if col else len(vals)
                    t = c.get("t")
                    v = c.find("m:v", ns)
                    isv = c.find("m:is", ns)
                    if t == "s" and v is not None:
                        val = shared[int(v.text)] if v.text and int(v.text) < len(shared) else ""
                    elif t == "inlineStr" and isv is not None:
                        val = "".join(x.text or "" for x in isv.iter(
                            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
                    else:
                        val = v.text if v is not None else ""
                    vals[idx] = val
                if vals:
                    width = max(vals) + 1
                    rows.append([vals.get(k, "") for k in range(width)])
            sheets.append({"name": name, "rows": rows})
        return sheets
    return []


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _sheets_to_table(sheets: list[dict]) -> dict:
    table_sheets = []
    for sh in sheets:
        rows = [r for r in sh["rows"] if any(str(c).strip() for c in r)]
        if len(rows) < 2:
            continue
        header = [str(c).strip() for c in rows[0]]
        body = []
        for r in rows[1:]:
            row = {}
            for i, h in enumerate(header):
                if not h:
                    continue
                row[h] = _coerce(str(r[i]) if i < len(r) else "")
            if any(v not in (None, "") for v in row.values()):
                body.append(row)
        table_sheets.append({"name": sh["name"], "header": header, "rows": body, "n_rows": len(body)})
    if not table_sheets:
        return {"kind": "table", "error": "no non-empty sheet"}
    first = table_sheets[0]
    return {"kind": "table", "sheets": table_sheets, "header": first["header"],
            "rows": first["rows"], "n_rows": sum(s["n_rows"] for s in table_sheets),
            "units_hint": _units_hint(first["header"])}


# --------------------------------------------------------------- documents
def read_docx(path: str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        paras = []
        for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            text = "".join(t.text or "" for t in p.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
            if text.strip():
                paras.append(text)
        blocks = [{"loc": f"para.{i + 1}", "text": t} for i, t in enumerate(paras)]
        return {"kind": "document", "blocks": blocks, "text": "\n".join(paras),
                "pages": max(1, len(paras) // 30)}
    except Exception as exc:
        return {"kind": "document", "error": str(exc), "blocks": [], "text": ""}


def read_plain(path: str) -> dict:
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    blocks = []
    for i, para in enumerate(re.split(r"\n\s*\n", text)):
        if para.strip():
            blocks.append({"loc": f"block.{i + 1}", "text": para})
    return {"kind": "text", "blocks": blocks, "text": text, "pages": 1}


def read_json(path: str) -> dict:
    try:
        data = json.load(open(path, "r", encoding="utf-8"))
    except Exception as exc:
        return {"kind": "json", "error": str(exc), "blocks": [], "text": ""}
    text = json.dumps(data, ensure_ascii=False, indent=1)
    return {"kind": "json", "data": data, "blocks": [{"loc": "json", "text": text}],
            "text": text, "pages": 1}


# ------------------------------------------------------------------ driver
def extract_file(path: str) -> dict:
    kind = os.path.splitext(path)[1].lower()
    base = {"path": path, "sha256": sha256_file(path) if os.path.getsize(path) < 60_000_000 else "",
            "bytes": os.path.getsize(path)}
    try:
        if kind == ".pdf":
            base.update(read_pdf(path))
        elif kind in {".csv", ".tsv", ".xlsx", ".xlsm"}:
            base.update(read_table(path))
            base["text"] = _table_text(base)
            base["blocks"] = [{"loc": "table", "text": base["text"]}]
        elif kind == ".docx":
            base.update(read_docx(path))
        elif kind in {".md", ".txt", ".tex", ".bib"}:
            base.update(read_plain(path))
        elif kind == ".json":
            base.update(read_json(path))
        else:
            base.update({"kind": "binary", "blocks": [], "text": "",
                         "note": f"no text extractor for {kind}"})
    except Exception as exc:
        base.update({"kind": "error", "error": str(exc), "blocks": [], "text": ""})
    base["kind_hint"] = kind
    return base


def _table_text(t: dict) -> str:
    if "sheets" in t:
        parts = []
        for sh in t["sheets"]:
            parts.append(f"# sheet: {sh['name']}  rows={sh['n_rows']}")
            parts.append(", ".join(sh["header"]))
            for r in sh["rows"][:80]:
                parts.append(", ".join("" if r.get(h) is None else str(r[h]) for h in sh["header"]))
        return "\n".join(parts)
    if "header" not in t:
        return t.get("error", "")
    lines = ["# table  rows=%d" % t.get("n_rows", 0), ", ".join(t["header"])]
    for r in t["rows"][:120]:
        lines.append(", ".join("" if r.get(h) is None else str(r[h]) for h in t["header"]))
    return "\n".join(lines)


def extract_all(files: list[dict], outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    textdir = os.path.join(outdir, "material_text")
    os.makedirs(textdir, exist_ok=True)
    materials = []
    for f in files:
        if f["kind"] in {"image", "vector", "archive", "other"}:
            materials.append({"path": f["path"], "rel": f["rel"], "kind": f["kind"],
                              "sha256": f["sha256"], "note": "binary input, not parsed",
                              "blocks": [], "text": ""})
            continue
        m = extract_file(f["path"])
        m["rel"] = f["rel"]
        materials.append(m)
        if m.get("text"):
            stem = re.sub(r"[^0-9A-Za-z_.-]+", "_", f["rel"]).strip("_")
            with open(os.path.join(textdir, stem + ".txt"), "w", encoding="utf-8") as fh:
                for b in m.get("blocks") or []:
                    fh.write(f"\n===== [{b['loc']}] =====\n{b['text']}\n")
    summary = {
        "n_files": len(materials),
        "by_kind": {},
        "materials": [{k: v for k, v in m.items() if k not in {"blocks", "text", "data"}}
                      | {"blocks": len(m.get("blocks") or []),
                         "chars": len(m.get("text") or "")}
                      for m in materials],
    }
    for m in materials:
        summary["by_kind"][m["kind"]] = summary["by_kind"].get(m["kind"], 0) + 1
    return {"materials": materials, "summary": summary, "text_dir": textdir}


def source_texts(materials: list[dict]) -> dict[str, str]:
    out = {}
    for i, m in enumerate(materials, start=1):
        sid = f"S{i}"
        out[sid] = m.get("text") or ""
    return out
