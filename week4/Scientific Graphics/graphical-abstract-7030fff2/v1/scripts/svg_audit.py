#!/usr/bin/env python3
"""diagram-forge: SVG source audit for scientific diagrams / graphical abstracts.

--check FILE.svg      XML validity; text-editability (text/tspan elements vs
                      outlined paths); layer structure (named <g> groups);
                      canvas size (viewBox); palette inventory (fill colors)
                      with counts; missing legend hints; tiny font sizes
--pair SRC EXPORT...  source+export manifest check (source exists, export
                      named variants listed; sizes reported if readable)
Stdlib only.
"""
import argparse
import json
import re
import sys
import os
import xml.etree.ElementTree as ET


def check_svg(path):
    problems, warnings, info = [], [], {}
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"error": "XML parse failed: %s" % e}, problems, warnings
    info["root_tag"] = root.tag.split("}")[-1]
    vb = root.get("viewBox") or root.get("viewbox")
    info["viewBox"] = vb
    if not vb:
        problems.append("no viewBox — canvas size undefined, export scaling will drift")
    w = root.get("width"); h = root.get("height")
    info["size_attr"] = [w, h]

    texts = list(root.iter() ) if False else []
    ns_strip = lambda t: t.split("}")[-1]
    text_els, tspan_els, groups, paths = 0, 0, [], 0
    fills = {}
    for el in root.iter():
        tag = ns_strip(el.tag)
        if tag == "text":
            text_els += 1
        elif tag == "tspan":
            tspan_els += 1
        elif tag == "g":
            gid = el.get("id") or el.get("data-role") or ""
            groups.append(gid)
        elif tag == "path":
            paths += 1
        f = el.get("fill") or el.get("stroke")
        if f and f not in ("none",):
            fills[f] = fills.get(f, 0) + 1
    info["n_text"] = text_els
    info["n_tspan"] = tspan_els
    info["n_path"] = paths
    info["groups"] = [g for g in groups if g] or ["(unnamed groups)"]
    info["unnamed_group_ratio"] = round(1 - (len([g for g in groups if g]) / max(1, len(groups))), 2)
    info["palette"] = sorted(fills.items(), key=lambda x: -x[1])[:20]

    if text_els + tspan_els == 0 and paths > 0:
        problems.append("TEXT: no <text> elements — all text likely outlined to paths, source no longer editable")
    unnamed = sum(1 for g in groups if not g)
    if groups and unnamed / len(groups) > 0.5:
        warnings.append("LAYERS: %d/%d groups unnamed — add data-role/id per panel (可编辑分层)" % (unnamed, len(groups)))
    # font sizes
    tiny = []
    for el in root.iter():
        if ns_strip(el.tag) in ("text", "tspan"):
            fs = el.get("font-size") or el.get("style") and re.search(r"font-size:\s*([\d.]+)", el.get("style") or "")
            if fs:
                v = float(re.findall(r"[\d.]+", str(fs))[0]) if re.findall(r"[\d.]+", str(fs)) else None
                if v and v < 8:
                    tiny.append(v)
    if tiny:
        warnings.append("FONT: %d text elements below 8px — unreadable in print" % len(tiny))
    # legend hints
    all_text = " ".join((el.text or "") for el in root.iter() if ns_strip(el.tag) in ("text", "tspan"))
    if len(fills) >= 4 and not re.search(r"(?i)legend|图例|对照|control|treated", all_text):
        warnings.append("LEGEND: >=4 colors but no legend-like text — color encoding must map to a legend")
    # canvas overflow: x/y/w/h beyond viewBox bounds
    if vb:
        m = re.match(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", vb)
        if m:
            vx, vy, vw, vh = map(float, m.groups())
            overflow = 0
            for el in root.iter():
                tag = ns_strip(el.tag)
                if tag in ("rect", "image", "circle", "ellipse", "text"):
                    try:
                        x = float(el.get("x", 0) or 0); y = float(el.get("y", 0) or 0)
                        ew = float(el.get("width", 0) or 0); eh = float(el.get("height", 0) or 0)
                    except ValueError:
                        continue
                    if tag in ("circle", "ellipse"):
                        r = float(el.get("r", 0) or el.get("rx", 0) or 0)
                        ew = eh = r * 2
                    if tag == "text":
                        # estimate rendered width: chars * font-size * 0.55 (no width attr in SVG text)
                        t = (el.text or "") + "".join((c.text or "") for c in el)
                        fs = el.get("font-size") or "12"
                        mf = re.search(r"[\d.]+", str(fs))
                        est_w = len(t) * float(mf.group(0)) * 0.55 if t and mf else 0
                        ew = est_w
                    if x < vx - 1 or y < vy - 1 or (ew and x + ew > vx + vw + 1) or (eh and y + eh > vy + vh + 1) or (not ew and x > vx + vw + 1):
                        overflow += 1
            if overflow:
                problems.append("CANVAS: %d elements overflow the viewBox — 内容超出画布，导出会被裁切" % overflow)
    # font-family check
    fams = set()
    for el in root.iter():
        if ns_strip(el.tag) in ("text", "tspan"):
            fam = el.get("font-family")
            st = el.get("style") or ""
            if not fam:
                mf = re.search(r"font-family:\s*([^;\"']+)", st)
                fam = mf.group(1) if mf else None
            if fam:
                fams.add(fam.strip())
    info["font_families"] = sorted(fams) or ["(unset — renderer default, font substitution risk)"]
    if not fams:
        warnings.append("FONT-FAMILY: no font-family declared anywhere — 导出时字体替换风险（建议声明通用字体族）")
    return info, problems, warnings


def pair_check(src, exports):
    problems, info = [], {"source": src, "exports": exports}
    if not os.path.exists(src):
        problems.append("source file missing: %s" % src)
    for e in exports:
        if not os.path.exists(e):
            problems.append("export file missing: %s" % e)
    exts = {os.path.splitext(e)[1].lower() for e in exports if os.path.exists(e)}
    info["export_formats"] = sorted(exts)
    return problems, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check"); ap.add_argument("--pair", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.check:
        info, problems, warnings = check_svg(a.check)
        out = {"schema": "diagram-forge/svg-audit@1", "file": a.check, "info": info,
               "problems": problems, "warnings": warnings}
        text = json.dumps(out, ensure_ascii=False, indent=1)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(text); print("wrote", a.out)
        else:
            print(text)
        return 1 if problems else 0
    if a.pair:
        src, exports = a.pair[0], a.pair[1:]
        problems, info = pair_check(src, exports)
        if problems:
            print("FAIL (%d):" % len(problems))
            for p in problems: print("  - %s" % p)
            return 1
        print("PASS: source + %d exports present (%s)" % (len(exports), info["export_formats"]))
        return 0
    ap.error("choose --check FILE.svg / --pair SRC EXPORT...")


if __name__ == "__main__":
    sys.exit(main())
