"""Export adapters and export-level compliance checks.

Order of preference for PDF/PNG: matplotlib (always present with the scientific
python stack) -> cairosvg -> rsvg-convert -> inkscape -> ImageMagick.  Every
attempt is recorded, so a degraded export is visible instead of silent.
"""
from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from typing import Any

from . import geom
from .draw import Drawing
from .svg_out import write_svg


def _run(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def export_all(drawing: Drawing, spec, outdir: str, stem: str, want_tiff: bool = True) -> dict:
    os.makedirs(outdir, exist_ok=True)
    svg_path = os.path.join(outdir, stem + ".svg")
    pdf_path = os.path.join(outdir, stem + ".pdf")
    png_path = os.path.join(outdir, stem + ".png")
    preview_path = os.path.join(outdir, stem + "_preview.png")

    report: dict[str, Any] = {"requested": {"svg": True, "pdf": True, "png": True, "tiff": want_tiff},
                              "attempts": [], "artifacts": {}, "checks": {}}
    svg_info = write_svg(drawing, svg_path, spec)
    report["artifacts"]["svg"] = {"path": svg_path, **svg_info}

    pdf_ok = png_ok = False
    try:
        from . import mpl_out
        info = mpl_out.render(drawing, spec, pdf_path, png_path, dpi=spec.dpi)
        report["attempts"].append({"backend": "matplotlib", "ok": True, **info})
        pdf_ok = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000
        png_ok = os.path.exists(png_path) and os.path.getsize(png_path) > 5000
        report["checks"]["cjk_font_available"] = info.get("cjk_ok")
        report["checks"]["fonts_missing"] = info.get("fonts_missing")
    except Exception as exc:  # pragma: no cover
        report["attempts"].append({"backend": "matplotlib", "ok": False, "error": str(exc)})

    if not pdf_ok:
        ok, msg = _convert_svg(svg_path, pdf_path, "pdf")
        report["attempts"].append({"backend": "svg->pdf fallback", "ok": ok, "message": msg[-400:]})
        pdf_ok = ok and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 500
    if not png_ok:
        ok, msg = _convert_svg(svg_path, png_path, "png", dpi=spec.dpi)
        report["attempts"].append({"backend": "svg->png fallback", "ok": ok, "message": msg[-400:]})
        png_ok = ok and os.path.exists(png_path) and os.path.getsize(png_path) > 3000

    if png_ok:
        try:
            from PIL import Image
            with Image.open(png_path) as im:
                im.load()
                w, h = im.size
                dpi_val = im.info.get("dpi", (None, None))
                preview = im.copy()
            report["artifacts"]["png"] = {"path": png_path, "px": [w, h], "dpi": dpi_val[0],
                                          "mode": preview.mode,
                                          "bytes": os.path.getsize(png_path),
                                          "physical_mm": [round(w / (dpi_val[0] or spec.dpi) * 25.4, 1),
                                                          round(h / (dpi_val[0] or spec.dpi) * 25.4, 1)]}
            max_w = 1600
            if preview.width > max_w:
                ratio = max_w / preview.width
                preview = preview.resize((max_w, max(1, int(preview.height * ratio))))
            preview.save(preview_path, dpi=(200, 200))
            report["artifacts"]["png_preview"] = {"path": preview_path,
                                                  "px": [preview.width, preview.height]}
        except Exception as exc:  # pragma: no cover
            report["artifacts"]["png"] = {"path": png_path, "error": str(exc)}

    if pdf_ok:
        report["artifacts"]["pdf"] = _pdf_info(pdf_path)
    if want_tiff and png_ok:
        tif_path = os.path.join(outdir, stem + ".tif")
        try:
            from PIL import Image
            with Image.open(png_path) as im:
                im.convert("RGB").save(tif_path, format="TIFF", compression="tiff_lzw",
                                       dpi=(spec.dpi, spec.dpi))
            report["artifacts"]["tiff"] = {"path": tif_path, "bytes": os.path.getsize(tif_path),
                                           "compression": "LZW", "dpi": spec.dpi}
        except Exception as exc:
            report["artifacts"]["tiff"] = {"path": tif_path, "error": str(exc)}

    report["checks"].update(_export_checks(report, spec))
    return report


def _convert_svg(svg: str, out: str, fmt: str, dpi: int = 600) -> tuple[bool, str]:
    try:
        import cairosvg  # type: ignore
        if fmt == "pdf":
            cairosvg.svg2pdf(url=svg, write_to=out)
        else:
            cairosvg.svg2png(url=svg, write_to=out, dpi=dpi, output_width=None)
        return True, "cairosvg"
    except Exception as exc:
        last = f"cairosvg: {exc}"
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-f", fmt, "-o", out]
        if fmt == "png":
            cmd += ["-d", str(dpi), "-p", str(dpi)]
        cmd.append(svg)
        ok, msg = _run(cmd)
        if ok:
            return True, "rsvg-convert"
        last = msg
    if shutil.which("inkscape"):
        ok, msg = _run(["inkscape", svg, f"--export-type={fmt}", f"--export-filename={out}"])
        if ok:
            return True, "inkscape"
        last = msg
    if shutil.which("convert"):
        extra = ["-density", str(dpi)] if fmt == "png" else []
        ok, msg = _run(["convert"] + extra + [svg, out])
        if ok:
            return True, "imagemagick"
        last = msg
    return False, last


def _pdf_info(path: str) -> dict:
    info: dict[str, Any] = {"path": path, "bytes": os.path.getsize(path)}
    with open(path, "rb") as fh:
        blob = fh.read()
    info["fonts_embedded"] = blob.count(b"/FontFile") + blob.count(b"/FontFile2") + blob.count(b"/FontFile3")
    info["fonts_total"] = len(set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", blob)))
    info["pages"] = len(re.findall(rb"/Type\s*/Page(?![s])", blob))
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", blob)
    if m:
        w = float(m.group(3)) - float(m.group(1))
        h = float(m.group(4)) - float(m.group(2))
        info["page_pt"] = [round(w, 1), round(h, 1)]
        info["page_mm"] = [round(w * 25.4 / 72, 1), round(h * 25.4 / 72, 1)]
    info["has_cmyk"] = b"/DeviceCMYK" in blob
    text = ""
    if shutil.which("pdftotext"):
        ok, out = _run(["pdftotext", "-q", path, "-"])
        text = out if ok else ""
    info["text_chars"] = len(text.strip())
    info["text_sample"] = text.strip()[:200]
    return info


def _export_checks(report: dict, spec) -> dict:
    checks: dict[str, Any] = {}
    pdf = report["artifacts"].get("pdf") or {}
    png = report["artifacts"].get("png") or {}
    svg = report["artifacts"].get("svg") or {}
    checks["pdf_present"] = bool(pdf.get("bytes", 0) > 500)
    checks["pdf_vector_text_embedded"] = bool(pdf.get("fonts_embedded", 0) > 0)
    checks["pdf_text_selectable"] = bool(pdf.get("text_chars", 0) > 20)
    checks["pdf_single_page"] = pdf.get("pages", 0) == 1
    if pdf.get("page_mm"):
        checks["pdf_size_matches_canvas"] = (abs(pdf["page_mm"][0] - spec.width_mm) < 1.0
                                             and abs(pdf["page_mm"][1] - spec.height_mm) < 1.0)
    checks["png_present"] = bool(png.get("bytes", 0) > 3000)
    checks["png_dpi"] = png.get("dpi")
    checks["png_dpi_ok"] = bool((png.get("dpi") or 0) >= 300)
    checks["svg_layers"] = len(svg.get("layers", []))
    checks["svg_text_editable"] = bool(svg.get("text_elements", 0) > 0)
    checks["rgb_color"] = not pdf.get("has_cmyk", False)
    return checks
