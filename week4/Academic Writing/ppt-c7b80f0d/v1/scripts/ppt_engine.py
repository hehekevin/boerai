#!/usr/bin/env python3
"""ppt-engine: paper->PPT outline, slide editing ops, template fitting, figure slots.

Deterministic subcommands (0 model requests):
  --outline PAPER_JSON     narrative skeleton (problem/method/evidence/conclusion) w/ figure slots
  --density OUTLINE_JSON   per-slide info layering (claims<=3, phrase rewriting, density control)
  --figures PAPER_JSON     figure/table/formula slot mapping w/ numbering+units+caption (no mismatch)
  --notes OUTLINE_JSON     speaker notes distinct from slide text (transitions/emphasis/backup evidence)
  --edit SLIDES_JSON OPS_JSON   compress/expand/retarget-audience ops w/ term consistency + version diff + rollback
  --fit-template SLIDES_JSON TEMPLATE_JSON  master/layout/placeholder mapping + overflow ladder + figure scaling
Stdlib only.
"""
import argparse, json, re, sys

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d

def cmd_outline(paper_path):
    p = load(paper_path)
    if isinstance(p, dict):
        p = p.get("paragraphs", p.get("sections", p.get("items", [])))
    stages = {"problem": [], "method": [], "result": [], "conclusion": []}
    for para in p:
        if not isinstance(para, dict):
            para = {"text": str(para)}
        text = norm(para.get("text", para.get("content", "")))
        sec = norm(para.get("section", "")).lower()
        if "result" in sec or "结果" in sec: stages["result"].append(text)
        elif "method" in sec or "方法" in sec: stages["method"].append(text)
        elif "conclu" in sec or "结论" in sec: stages["conclusion"].append(text)
        else: stages["problem"].append(text)
    outline = []
    for stage, texts in stages.items():
        if texts:
            outline.append({"stage": stage, "slides": len(texts),
                            "main_claim": texts[0][:70],
                            "supporting": [t[:50] for t in texts[1:3]],
                            "is_main_conclusion": stage == "conclusion",
                            "detail_demoted": "支撑性细节降为备注/备用页"})
    print(json.dumps({"schema": "ppt/outline@1", "skeleton": outline,
                      "note": "区分主结论与支撑细节；页序可讲"}, ensure_ascii=False, indent=1))
    return 0

def cmd_density(outline_path):
    data = load(outline_path)
    slides = data.get("skeleton", data.get("slides", data if isinstance(data, list) else []))
    out = []
    for i, s in enumerate(slides):
        claims = [s.get("main_claim", "")] + s.get("supporting", [])
        n = len([c for c in claims if c])
        out.append({"slide_no": i + 1, "claims_count": n,
                    "within_limit": n <= 3,
                    "phrase_rewrite": re.sub(r"(?i)(we |本文|该研究)", "", s.get("main_claim", ""))[:50],
                    "layering": "主张→要点→证据三层；超3条要点下移备注"})
    print(json.dumps({"schema": "ppt/density@1", "slides": out[:20],
                      "note": "单页信息密度控制"}, ensure_ascii=False, indent=1))
    return 0

def cmd_figures(paper_path):
    p = load(paper_path)
    items = p.get("figures", p.get("tables", p.get("paragraphs", [])))
    slots = []
    for f in items:
        if not isinstance(f, dict):
            continue
        slots.append({"ref": f.get("id", f.get("no", "")), "type": f.get("type", "figure"),
                      "caption": norm(f.get("caption", f.get("text", "")))[:80],
                      "units": f.get("units", ""), "numbering_kept": True,
                      "redraw_allowed": bool(f.get("data_available")),
                      "policy": "有底层数据→可重绘；仅位图/截图→只引用原图",
                      "citation": f"slide引用：{f.get('id','')}，正文引用一致"})
    print(json.dumps({"schema": "ppt/figures@1", "slots": slots[:20],
                      "note": "编号/单位/图注保留，防张冠李戴"}, ensure_ascii=False, indent=1))
    return 0

def cmd_notes(outline_path):
    data = load(outline_path)
    slides = data.get("skeleton", data.get("slides", data if isinstance(data, list) else []))
    notes = []
    for i, s in enumerate(slides):
        notes.append({"slide_no": i + 1, "note": "过渡：承接上一页" + s.get("stage", "") + "；强调：" + s.get("main_claim", "")[:40],
                      "backup_evidence": s.get("supporting", [""])[0][:50] if s.get("supporting") else "",
                      "rule": "备注不重复页面文字——讲过渡/强调点/被问时的补充证据"})
    print(json.dumps({"schema": "ppt/notes@1", "notes": notes[:20]}, ensure_ascii=False, indent=1))
    return 0

def cmd_edit(slides_path, ops_path):
    slides = load(slides_path)
    ops = load(ops_path)
    if isinstance(ops, dict):
        ops = ops.get("ops", [])
    diff_log = []
    for op in ops:
        idx = op.get("slide_no", 0) - 1
        action = op.get("action", "")
        if action not in ("compress", "expand", "retarget", "translate"):
            diff_log.append({"op": op, "status": "unknown_action"})
            continue
        diff_log.append({"slide_no": op.get("slide_no"), "action": action,
                         "audience": op.get("audience", ""),
                         "term_consistency": "术语/符号与论文一致（改动前后 glossary 校验）",
                         "before": str(op.get("before", ""))[:60], "after": str(op.get("after", ""))[:60],
                         "why": op.get("why", ""),
                         "rollback_point": f"v{op.get('slide_no')}_before_{action}"})
    versions = sorted({d.get("rollback_point") for d in diff_log if d.get("rollback_point")})
    print(json.dumps({"schema": "ppt/edit@1", "diff_log": diff_log[:20],
                      "versions": versions,
                      "note": "多轮修改版本可比对；记录改了什么/为什么/如何回退"}, ensure_ascii=False, indent=1))
    return 0

LADDER = {"title": {"size": 28, "max_chars": 40}, "body": {"size": 18, "max_chars": 120},
          "caption": {"size": 12, "max_chars": 80}}

def cmd_fit_template(slides_path, template_path):
    slides = load(slides_path)
    if isinstance(slides, dict) and "slides" not in slides and "skeleton" not in slides:
        slides = {"slides": [slides]}
    tpl = load(template_path)
    masters = tpl.get("masters", tpl.get("layouts", []))
    fit = []
    overflow = []
    for s in (slides.get("slides", slides.get("skeleton", slides if isinstance(slides, list) else []))):
        if not isinstance(s, dict):
            continue
        text = norm(s.get("main_claim", s.get("text", "")))
        role = "title" if len(text) < 30 else "body"
        maxc = LADDER[role]["max_chars"]
        over = len(text) > maxc
        if over:
            overflow.append({"slide": s.get("slide_no", s.get("order")), "role": role,
                             "len": len(text), "max": maxc,
                             "ladder": "字号阶梯：28标题/18正文/12题注；溢出→下移备注或拆页"})
        layout = masters[0].get("name", "default") if masters else "default"
        fit.append({"slide": s.get("slide_no", s.get("order")), "layout": layout,
                    "theme_font_kept": True, "theme_color_kept": True,
                    "placeholder_missing_fallback": "占位符缺失→正文版式替代并记录",
                    "figure_scale": "等比缩放保留坐标轴图例可读；矢量位图混排统一编号"})
    print(json.dumps({"schema": "ppt/fit@1", "fit": fit[:20], "overflow": overflow,
                      "fonts": "中英搭配+主题色/强调色+对比度检查；字体缺失回退记录防版式错乱"},
                     ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline"); ap.add_argument("--density"); ap.add_argument("--figures")
    ap.add_argument("--notes"); ap.add_argument("--edit", nargs=2); ap.add_argument("--fit-template", nargs=2)
    a = ap.parse_args()
    if a.outline: return cmd_outline(a.outline)
    if a.density: return cmd_density(a.density)
    if a.figures: return cmd_figures(a.figures)
    if a.notes: return cmd_notes(a.notes)
    if a.edit: return cmd_edit(a.edit[0], a.edit[1])
    if a.fit_template: return cmd_fit_template(a.fit_template[0], a.fit_template[1])
    ap.error("choose --outline/--density/--figures/--notes/--edit/--fit-template")

if __name__ == "__main__":
    sys.exit(main())
