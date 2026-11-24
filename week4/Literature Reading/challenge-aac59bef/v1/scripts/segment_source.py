#!/usr/bin/env python3
"""trans-align-forge: source extraction, segmentation, token inventory.

Backends for PDF text (tried in order): PyMuPDF(fitz) -> pdfminer -> pypdf ->
pdftotext CLI. If none available, prints a clear signal so the agent can use
platform tools (e.g. pdf-text-tool output) and call --segment on plain text.

Usage:
  python segment_source.py --inspect /input/case.json
  python segment_source.py --extract paper.pdf --out source.json
  python segment_source.py --segment source.json --out segments.json
  python segment_source.py --segment paper.txt --text --out segments.json
Exit: 0 ok; 2 usage/backend-missing (message explains fallback).
"""
import argparse
import json
import os
import re
import sys
import shutil
import subprocess

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
UNIT_RE = re.compile(
    r"(?<![\w.])(?:nm|um|μm|mm|cm|m|km|mg|ug|μg|g|kg|mL|ml|L|mol|mol/L|M|mM|%"
    r"|ms|s|min|h|Hz|kHz|MHz|GHz|bp|kb|ppm|eV|keV|MeV|V|mV|kV|A|mA|μA|K|°C|W|kW)\b\.?")
CIT_RE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
REF_RE = re.compile(
    r"(?i)\((?:([A-Z][A-Za-z\-']+(?:\s+et\s+al\.?)?|[^)]{0,40}?),\s*(\d{4})[a-z]?)\)")
REFWORD_RE = re.compile(r"(?i)\b((?:fig(?:ure)?|table|eq(?:uation)?|section|algorithm|ref)\.?)\s*\((\d+[a-z]?|\d+\.\d+)")
FORMULA_RE = re.compile(r"Eq\.?\s*\(\d+\)|\\begin\{equation\}|\$\$?")
SENT_END = re.compile(r"[.。!?！？][\"'’”)\]]?\s*$")

PDF_BACKENDS_DONE = []


def pdf_text(path):
    """Try every backend; return (text, backend) or (None, error_summary)."""
    tried = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        pages = [p.get_text("text") for p in doc]
        PDF_BACKENDS_DONE.append("pymupdf")
        return "\n\f".join(pages), "pymupdf"
    except Exception as e:
        tried.append("pymupdf:%s" % type(e).__name__)
    try:
        from pdfminer.high_level import extract_text
        t = extract_text(path)
        PDF_BACKENDS_DONE.append("pdfminer")
        return t, "pdfminer"
    except Exception as e:
        tried.append("pdfminer:%s" % type(e).__name__)
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        pages = [(p.extract_text() or "") for p in r.pages]
        PDF_BACKENDS_DONE.append("pypdf")
        return "\n\f".join(pages), "pypdf"
    except Exception as e:
        tried.append("pypdf:%s" % type(e).__name__)
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            out = subprocess.run([pdftotext, "-layout", path, "-"],
                                 capture_output=True, timeout=120)
            if out.returncode == 0:
                PDF_BACKENDS_DONE.append("pdftotext")
                return out.stdout.decode("utf-8", "replace"), "pdftotext"
            tried.append("pdftotext:rc=%d" % out.returncode)
        except Exception as e:
            tried.append("pdftotext:%s" % type(e).__name__)
    return None, "; ".join(tried) or "no backend found"


def inventory(text):
    return {
        "numbers": sorted(set(NUM_RE.findall(text)))[:50],
        "units": sorted(set(u.strip(".") for u in UNIT_RE.findall(text)))[:50],
        "citations": sorted(set(CIT_RE.findall(text)))[:50],
        "author_year": sorted(set(m.group(0) for m in REF_RE.finditer(text)))[:50],
        "ref_markers": sorted(set(m.group(0) for m in REFWORD_RE.finditer(text)))[:50],
        "formula_refs": sorted(set(m.group(0) for m in FORMULA_RE.finditer(text)))[:30],
    }


def split_paragraphs(pages_text):
    """Split page texts into paragraphs; merge obvious cross-page continuations."""
    paras, pid, page = [], 0, 0
    for pno, ptext in enumerate(pages_text, 1):
        blocks = [b.strip() for b in re.split(r"\n\s*\n", ptext) if b.strip()]
        for b in blocks:
            pid += 1
            page = pno
            if paras and not SENT_END.search(paras[-1]["text"]) and \
               (b[:1].islower() or b[:1] in "([{"):
                # continuation of previous paragraph across page break
                paras[-1]["text"] += " " + b
                paras[-1]["pages"].append(pno)
                paras[-1]["continued"] = True
            else:
                paras.append({"seg_id": "P%03d" % pid, "text": b,
                              "pages": [pno], "continued": False})
    return paras


def inspect_case(path):
    report = {"path": path, "exists": os.path.exists(path), "anomalies": []}
    if not report["exists"]:
        report["anomalies"].append("case.json not found")
        print(json.dumps(report, ensure_ascii=False, indent=2)); return
    try:
        case = json.load(open(path, encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        report["anomalies"].append("invalid JSON: %s" % e)
        print(json.dumps(report, ensure_ascii=False, indent=2)); return
    if isinstance(case, dict):
        report["top_level_keys"] = sorted(case.keys())
        for k in ("case_id", "output_contract", "materials", "task"):
            v = case.get(k)
            report[k] = sorted(v.keys()) if isinstance(v, dict) else v if isinstance(v, list) else str(v)[:120] if v is not None else None
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect"); ap.add_argument("--extract")
    ap.add_argument("--segment"); ap.add_argument("--text", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not a.out:
        ap.error("--out required")

    if a.inspect:
        inspect_case(a.inspect); return 0

    if a.extract:
        text, backend = pdf_text(a.extract)
        if text is None:
            print(json.dumps({"error": "no PDF backend available",
                              "tried": backend,
                              "fallback": "produce plain text with platform pdf-text-tool / ocr-tool, then run --segment <txt> --text"}, ensure_ascii=False, indent=2))
            return 2
        json.dump({"backend": backend, "source": a.extract, "pages_text": text.split("\f")},
                  open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("extracted via %s -> %s" % (backend, a.out)); return 0

    if a.segment:
        if a.text:
            pages = open(a.segment, encoding="utf-8", errors="replace").read().split("\f")
        else:
            pages = json.load(open(a.segment, encoding="utf-8"))["pages_text"]
        paras = split_paragraphs(pages)
        for p in paras:
            p["tokens"] = inventory(p["text"])
        json.dump({"schema": "trans-align-forge/segments@1", "n_segments": len(paras),
                   "segments": paras}, open(a.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        cont = sum(1 for p in paras if p["continued"])
        print("segments=%d (cross-page merged=%d) -> %s" % (len(paras), cont, a.out))
        return 0
    ap.error("choose --inspect / --extract / --segment")


if __name__ == "__main__":
    sys.exit(main())
