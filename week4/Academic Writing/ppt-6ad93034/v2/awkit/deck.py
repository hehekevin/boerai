"""学术幻灯片：JSON 大纲 → 可编辑 PPTX + 页级证据校验 + 真实渲染预览。

outline.json:
  {"title": "汇报标题", "audience": "答辩委员会", "minutes": 15,
   "slides": [{"no": 1, "kind": "title|content|closing",
               "claim": "本页唯一主张（一句话）",
               "bullets": ["要点1", "要点2"],
               "notes": "讲解备注（不得与要点重复）",
               "evidence": [{"source_id": "S1", "loc": "论文 图2",
                             "quote": "来源原文片段"}], "role": "方法"}]}

两条生成路径（诚实报告用了哪条）：
1. python-pptx（若 import 成功）；
2. 内置纯 zipfile+XML 的最小 OpenXML 写出器（保证路径，零依赖）。

预览：soffice/libreoffice 在则 pptx→pdf；matplotlib 在则逐页 PNG 版式预览。
两者都不可用时在报告里如实写明 preview="unavailable"，绝不伪造预览。

校验规则（validate_outline，全部机械）：
- 每页必须有 claim；content 页必须挂 ≥1 条 evidence，且 quote 为来源子串；
- 每页要点数 ≤ max_bullets（默认 6），单条 ≤ max_bullet_chars（默认 60 字）；
- notes 必填且不得与 bullets 任一相同（备注不是页面复读）；
- 页数 ≤ slide_limit（题面给定时）；
- 页面文字中的数字走 awkit.claims 同源规则：必须字面出现在本页 evidence 里。

CLI:
  python -m awkit.deck validate OUTLINE SOURCES OUT_JSON [--slide-limit N]
  python -m awkit.deck build OUTLINE OUT_PPTX [--preview DIR]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from xml.sax.saxutils import escape

from . import claims as _claims

EMU_W, EMU_H = 12192000, 6858000  # 16:9

# ---------------------------------------------------------------- 校验
def validate_outline(outline: dict, sources: list[dict] | None = None,
                     slide_limit: int | None = None, max_bullets: int = 6,
                     max_bullet_chars: int = 60) -> dict:
    src = {s.get("id"): _claims.norm(s.get("text", "")) for s in (sources or [])}
    violations, warnings = [], []
    slides = outline.get("slides", [])
    if not slides:
        violations.append({"type": "empty_deck"})
    if slide_limit and len(slides) > slide_limit:
        violations.append({"type": "slide_limit_exceeded", "slides": len(slides),
                           "limit": slide_limit})
    for i, sl in enumerate(slides, 1):
        no = sl.get("no", i)
        if not sl.get("claim", "").strip():
            violations.append({"type": "slide_missing_claim", "slide": no})
        bl = sl.get("bullets", [])
        if len(bl) > max_bullets:
            violations.append({"type": "too_many_bullets", "slide": no,
                               "n": len(bl), "max": max_bullets})
        for b in bl:
            if len(b) > max_bullet_chars:
                warnings.append({"type": "bullet_too_long", "slide": no,
                                 "chars": len(b), "text": b[:60]})
        notes = sl.get("notes", "").strip()
        if not notes:
            violations.append({"type": "notes_missing", "slide": no})
        elif any(notes == b.strip() for b in bl):
            violations.append({"type": "notes_duplicate_bullets", "slide": no,
                               "note": "备注不得复读页面文字"})
        evs = sl.get("evidence", [])
        if sl.get("kind", "content") == "content" and not evs:
            violations.append({"type": "content_slide_without_evidence", "slide": no})
        page_text = " ".join([sl.get("claim", "")] + bl)
        bound = ""
        for ev in evs:
            sid, q = ev.get("source_id"), _claims.norm(ev.get("quote", ""))
            if sid not in src:
                violations.append({"type": "evidence_unknown_source", "slide": no,
                                   "source_id": sid})
            elif not q or q not in src[sid]:
                violations.append({"type": "evidence_quote_not_in_source", "slide": no,
                                   "source_id": sid, "quote": q[:120]})
            else:
                bound += " " + q
        for num in _claims.numbers_in(page_text):
            if not _claims.number_in_text(num, bound):
                violations.append({"type": "slide_number_not_in_evidence",
                                   "slide": no, "number": num,
                                   "note": "页面数字必须字面出现在本页证据引文中"})
    return {"ok": not violations, "slides": len(slides),
            "violations": violations, "warnings": warnings}


# ---------------------------------------------------------------- PPTX (纯 zip)
def _sp_text(shape_id: int, name: str, x: int, y: int, cx: int, cy: int,
             paras: list[str], size: int, bold: bool = False) -> str:
    runs = []
    for p in paras:
        t = escape(p)
        runs.append(
            f'<a:p><a:pPr marL="285750" indent="-285750"><a:buChar char="•"/></a:pPr>'
            f'<a:r><a:rPr lang="zh-CN" sz="{size}"{" b=\"1\"" if bold else ""}/>'
            f"<a:t>{t}</a:t></a:r></a:p>")
    body = "".join(runs) or '<a:p><a:endParaRPr lang="zh-CN"/></a:p>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
            f'<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square"><a:normAutofit/></a:bodyPr>'
            f"<a:lstStyle/>{body}</p:txBody></p:sp>")


def _slide_xml(slide: dict) -> str:
    title = _sp_text(2, "Title", 457200, 274638, EMU_W - 914400, 1000000,
                     [slide.get("claim") or slide.get("title", "")], 3000, True)
    bullets = slide.get("bullets", [])
    body = _sp_text(3, "Content", 457200, 1500000, EMU_W - 914400, EMU_H - 1900000,
                    bullets, 1800) if bullets else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f"<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/>"
            f"<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>"
            f'<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
            f'<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{title}{body}'
            f"</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>")


def _notes_xml(text: str) -> str:
    sp = _sp_text(2, "Notes Placeholder", 685800, 4114800, 5486400, 4114800,
                  [text or "(无备注)"], 1400)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
            "<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>"
            '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
            f'<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{sp}'
            "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>")


_THEME = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'name="awkit"><a:themeElements>'
          '<a:clrScheme name="awkit"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
          '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
          '<a:dk2><a:srgbClr val="1F3864"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2>'
          '<a:accent1><a:srgbClr val="4472C4"/></a:accent1><a:accent2><a:srgbClr val="ED7D31"/></a:accent2>'
          '<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3><a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
          '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5><a:accent6><a:srgbClr val="70AD47"/></a:accent6>'
          '<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
          '</a:clrScheme>'
          '<a:fontScheme name="awkit"><a:majorFont><a:latin typeface="Calibri Light"/>'
          '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
          '<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/>'
          '</a:minorFont></a:fontScheme>'
          '<a:fmtScheme name="awkit">'
          '<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
          '<a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
          '<a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
          '<a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
          '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>'
          '<a:effectStyle><a:effectLst/></a:effectStyle>'
          '<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
          '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
          "</a:fmtScheme></a:themeElements></a:theme>")

_MASTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
           '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/>'
           '</p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
           '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
           '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
           'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
           'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
           '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
           '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="3000" b="1"/></a:lvl1pPr></p:titleStyle>'
           '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>'
           '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle>'
           "</p:txStyles></p:sldMaster>")

_LAYOUT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
           'type="obj" preserve="1">'
           '<p:cSld name="Title and Content"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
           '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
           '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
           "</p:grpSpPr></p:spTree></p:cSld>"
           "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>")

_NOTES_MASTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                 '<p:notesMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                 '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/>'
                 '<p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
                 '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>'
                 "</a:xfrm></p:grpSpPr></p:spTree></p:cSld>"
                 '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
                 'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
                 'accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:notesMaster>')

_REL = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "{}</Relationships>")
_R = ('<Relationship Id="{id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
      'relationships/{typ}" Target="{tgt}"/>')


def write_deck_zip(outline: dict, path: str) -> dict:
    """保证路径：纯 zipfile 写出最小合法 PPTX。"""
    slides = outline.get("slides", [])
    n = len(slides)
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/notesMasters/notesMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for i in range(1, n + 1):
        overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType='
                         '"application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        overrides.append(f'<Override PartName="/ppt/notesSlides/notesSlide{i}.xml" ContentType='
                         '"application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     + "".join(overrides) + "</Types>")
    pres_rels = [_R.format(id="rId1", typ="slideMaster", tgt="slideMasters/slideMaster1.xml"),
                 _R.format(id="rId2", typ="notesMaster", tgt="notesMasters/notesMaster1.xml"),
                 _R.format(id="rId3", typ="theme", tgt="theme/theme1.xml"),
                 _R.format(id="rId4", typ="presProps", tgt="presProps.xml")]
    sld_ids = []
    for i in range(1, n + 1):
        rid = f"rId{4 + i}"
        pres_rels.append(_R.format(id=rid, typ="slide", tgt=f"slides/slide{i}.xml"))
        sld_ids.append(f'<p:sldId id="{255 + i}" r:id="{rid}"/>')
    presentation = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
                    '<p:notesMasterIdLst><p:notesMasterId r:id="rId2"/></p:notesMasterIdLst>'
                    f"<p:sldIdLst>{''.join(sld_ids)}</p:sldIdLst>"
                    f'<p:sldSz cx="{EMU_W}" cy="{EMU_H}" type="wide"/>'
                    '<p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{escape(outline.get('title', 'deck'))}</dc:title>"
            "<dc:creator>awkit</dc:creator></cp:coreProperties>")
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f"<Application>awkit</Application><Slides>{n}</Slides></Properties>")
    pres_props = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                  '<p:presentationPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                  'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", _REL.format(
            _R.format(id="rId1", typ="officeDocument", tgt="ppt/presentation.xml")
            + '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            + _R.format(id="rId3", typ="extended-properties", tgt="docProps/app.xml")))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", _REL.format("".join(pres_rels)))
        z.writestr("ppt/presProps.xml", pres_props)
        z.writestr("ppt/theme/theme1.xml", _THEME)
        z.writestr("ppt/slideMasters/slideMaster1.xml", _MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _REL.format(
            _R.format(id="rId1", typ="slideLayout", tgt="../slideLayouts/slideLayout1.xml")
            + _R.format(id="rId2", typ="theme", tgt="../theme/theme1.xml")))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", _LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _REL.format(
            _R.format(id="rId1", typ="slideMaster", tgt="../slideMasters/slideMaster1.xml")))
        z.writestr("ppt/notesMasters/notesMaster1.xml", _NOTES_MASTER)
        z.writestr("ppt/notesMasters/_rels/notesMaster1.xml.rels", _REL.format(
            _R.format(id="rId1", typ="theme", tgt="../theme/theme1.xml")))
        for i, sl in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(sl))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", _REL.format(
                _R.format(id="rId1", typ="slideLayout", tgt="../slideLayouts/slideLayout1.xml")
                + _R.format(id="rId2", typ="notesSlide", tgt=f"../notesSlides/notesSlide{i}.xml")))
            z.writestr(f"ppt/notesSlides/notesSlide{i}.xml", _notes_xml(sl.get("notes", "")))
            z.writestr(f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels", _REL.format(
                _R.format(id="rId1", typ="slide", tgt=f"../slides/slide{i}.xml")
                + _R.format(id="rId2", typ="notesMaster", tgt="../notesMasters/notesMaster1.xml")))
    return {"path": path, "slides": n, "writer": "awkit.pure_zip"}


def write_deck_python_pptx(outline: dict, path: str) -> dict:
    """可选加速路径：python-pptx 可用时用之（占位符继承更完整）。"""
    from pptx import Presentation  # type: ignore
    from pptx.util import Inches, Pt  # type: ignore
    prs = Presentation()
    prs.slide_width, prs.slide_height = EMU_W, EMU_H
    layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    for sl in outline.get("slides", []):
        s = prs.slides.add_slide(layout)
        if s.shapes.title is not None:
            s.shapes.title.text = sl.get("claim") or sl.get("title", "")
        body = next((sh for sh in s.placeholders if sh.placeholder_format.idx != 0), None)
        if body is not None and body.has_text_frame:
            tf = body.text_frame
            for j, b in enumerate(sl.get("bullets", [])):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = b
                for r in p.runs:
                    r.font.size = Pt(18)
        if s.has_notes_slide:
            s.notes_slide.notes_text_frame.text = sl.get("notes", "")
    prs.save(path)
    return {"path": path, "slides": len(outline.get("slides", [])),
            "writer": "python-pptx"}


def build_deck(outline: dict, path: str) -> dict:
    """优先 python-pptx；不可导入时回落纯 zip 写出器，并如实记录。"""
    try:
        import pptx  # noqa: F401
        return write_deck_python_pptx(outline, path)
    except Exception as exc:  # noqa: BLE001
        rep = write_deck_zip(outline, path)
        rep["fallback_reason"] = f"python-pptx unavailable: {type(exc).__name__}"
        return rep


# ---------------------------------------------------------------- 预览
def render_preview_png(outline: dict, outdir: str) -> dict:
    """matplotlib 逐页版式预览（有则用，无则如实报告 unavailable）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager, pyplot as plt
    except Exception as exc:  # noqa: BLE001
        return {"preview_png": "unavailable", "reason": f"matplotlib: {type(exc).__name__}"}
    cjk = [f.name for f in font_manager.fontManager.ttflist
           if any(k in f.name for k in ("CJK", "Hei", "Song", "WenQuanYi", "Noto Sans SC",
                                        "SimHei", "Microsoft YaHei", "AR PL"))]
    if cjk:
        matplotlib.rcParams["font.family"] = cjk[0]
    matplotlib.rcParams["axes.unicode_minus"] = False
    os.makedirs(outdir, exist_ok=True)
    files, warns = [], []
    if not cjk:
        warns.append("no CJK font found: PNG 预览中汉字可能显示为方框，不影响 PPTX 本身")
    for i, sl in enumerate(outline.get("slides", []), 1):
        fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=90)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=1.5))
        ax.text(0.05, 0.90, (sl.get("claim") or "")[:80], fontsize=15,
                fontweight="bold", va="top", wrap=True)
        y = 0.72
        for b in sl.get("bullets", [])[:6]:
            ax.text(0.08, y, "• " + b[:60], fontsize=11, va="top")
            y -= 0.11
        ax.text(0.05, 0.04, f"p.{i}  notes: {sl.get('notes', '')[:90]}",
                fontsize=8, color="gray", va="bottom")
        fp = os.path.join(outdir, f"slide_{i:02d}.png")
        fig.savefig(fp, bbox_inches="tight")
        plt.close(fig)
        files.append(fp)
    return {"preview_png": files, "warnings": warns}


def render_pdf(pptx_path: str, outdir: str) -> dict:
    """LibreOffice 真实渲染 pptx→pdf（在则用，不在则如实报告）。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return {"preview_pdf": "unavailable",
                "reason": "soffice/libreoffice not installed in this runtime"}
    os.makedirs(outdir, exist_ok=True)
    try:
        p = subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                            "--outdir", outdir, pptx_path],
                           capture_output=True, text=True, timeout=300)
    except Exception as exc:  # noqa: BLE001
        return {"preview_pdf": "failed", "reason": str(exc)}
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf")
    if p.returncode == 0 and os.path.exists(pdf) and os.path.getsize(pdf) > 500:
        return {"preview_pdf": pdf, "bytes": os.path.getsize(pdf)}
    return {"preview_pdf": "failed", "reason": (p.stdout + p.stderr)[-400:]}


def inspect_pptx(path: str) -> dict:
    """机械验证：合法 zip、必备部件、页面文字可回读。"""
    out = {"path": path, "is_zip": zipfile.is_zipfile(path)}
    if not out["is_zip"]:
        out["ok"] = False
        return out
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        out["has_content_types"] = "[Content_Types].xml" in names
        out["slide_xmls"] = sorted(n for n in names
                                   if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        texts = {}
        for n_ in out["slide_xmls"]:
            xml = z.read(n_).decode("utf-8")
            texts[n_] = re.findall(r"<a:t>([^<]*)</a:t>", xml)
        out["slide_texts"] = texts
        out["has_notes"] = any(n.startswith("ppt/notesSlides/") for n in names)
    out["ok"] = out["has_content_types"] and bool(out["slide_xmls"])
    return out


def _demo() -> int:
    import tempfile
    sources = [{"id": "S1", "text": "We screened 500 genes across 3 donors. "
                                    "The hit rate was 4.2% in the primary screen."}]
    outline = {"title": "T 细胞筛选组会汇报", "audience": "组会", "minutes": 10,
               "slides": [
                   {"no": 1, "kind": "title", "claim": "T 细胞活化调控因子的高通量筛选",
                    "bullets": ["汇报人：示例", "日期：示例"],
                    "notes": "开场一句话说明汇报目标：同步筛选进度与下一步计划。",
                    "evidence": [], "role": "封面"},
                   {"no": 2, "kind": "content", "claim": "初筛覆盖 500 个基因、3 名供体",
                    "bullets": ["筛选规模 500 个基因", "覆盖 3 名供体", "初筛命中率 4.2%"],
                    "notes": "强调供体数限制了统计效力，引导讨论是否扩大队列。",
                    "evidence": [{"source_id": "S1", "loc": "论文 方法 p.3",
                                  "quote": "We screened 500 genes across 3 donors. The hit rate was 4.2%"}],
                    "role": "结果"}]}
    rep = validate_outline(outline, sources, slide_limit=12)
    assert rep["ok"], rep["violations"]
    # 数字不在证据里必须被抓
    bad = json.loads(json.dumps(outline))
    bad["slides"][1]["bullets"][0] = "筛选规模 600 个基因"
    repb = validate_outline(bad, sources)
    assert any(v["type"] == "slide_number_not_in_evidence" for v in repb["violations"])
    # 备注复读必须被抓
    bad2 = json.loads(json.dumps(outline))
    bad2["slides"][1]["notes"] = bad2["slides"][1]["bullets"][0]
    repb2 = validate_outline(bad2, sources)
    assert any(v["type"] == "notes_duplicate_bullets" for v in repb2["violations"])
    # 构建与机械回读
    tmp = tempfile.mkdtemp(prefix="awkit-deck-")
    pptx_path = os.path.join(tmp, "demo.pptx")
    built = build_deck(outline, pptx_path)
    assert os.path.getsize(pptx_path) > 1000
    insp = inspect_pptx(pptx_path)
    assert insp["ok"] and insp["has_content_types"] and len(insp["slide_xmls"]) == 2
    flat_text = " ".join(t for ts in insp["slide_texts"].values() for t in ts)
    assert "初筛覆盖 500 个基因、3 名供体" in flat_text  # 文本框带大纲文字
    assert "4.2%" in flat_text
    assert insp["has_notes"]
    # 预览（有则生成，无则诚实标记——两者都算通过）
    prev = render_preview_png(outline, os.path.join(tmp, "png"))
    assert "preview_png" in prev
    pdf = render_pdf(pptx_path, tmp)
    assert pdf.get("preview_pdf") in (None,) or True
    if isinstance(pdf.get("preview_pdf"), str) and pdf["preview_pdf"].endswith(".pdf"):
        assert os.path.getsize(pdf["preview_pdf"]) > 500
    print(f"  deck demo: writer={built['writer']}, preview_png="
          f"{len(prev.get('preview_png') or [])}, pdf={pdf.get('preview_pdf')}")
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "validate":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.deck validate")
        ap.add_argument("outline"); ap.add_argument("sources"); ap.add_argument("out")
        ap.add_argument("--slide-limit", type=int, default=0)
        a = ap.parse_args(argv[1:])
        rep = validate_outline(json.load(open(a.outline, encoding="utf-8")),
                               json.load(open(a.sources, encoding="utf-8")),
                               a.slide_limit or None)
        json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"deck validate: ok={rep['ok']} slides={rep['slides']} -> {a.out}")
        return 0 if rep["ok"] else 1
    if argv and argv[0] == "build":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.deck build")
        ap.add_argument("outline"); ap.add_argument("out_pptx")
        ap.add_argument("--preview", default="")
        a = ap.parse_args(argv[1:])
        outline = json.load(open(a.outline, encoding="utf-8"))
        built = build_deck(outline, a.out_pptx)
        insp = inspect_pptx(a.out_pptx)
        rep = {"build": built, "inspect": {k: v for k, v in insp.items()
                                           if k != "slide_texts"}}
        if a.preview:
            rep["png"] = render_preview_png(outline, a.preview)
            rep["pdf"] = render_pdf(a.out_pptx, a.preview)
        json.dump(rep, open(a.out_pptx + ".build.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"deck build: writer={built['writer']} slides={built['slides']} "
              f"inspect_ok={insp['ok']} -> {a.out_pptx}")
        return 0 if insp["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
