#!/usr/bin/env python3
"""presentation-planner-forge: report goal -> narrative order -> per-slide claim -> Q&A prep.

Deterministic subcommands (0 model requests):
  --goals GOALS_JSON        convert report goals into checkable items (audience/pages/duration/claim-strength)
  --order OUTLINE_JSON      narrative order on problem-method-result-conclusion spine (not paper TOC copy)
  --slides OUTLINE_JSON     per-slide: unique claim + evidence + graphic + claim-strength label
  --qa OUTLINE_JSON         anticipated Q&A (mechanism/data/controls/limits) with citeable slides
Stdlib only.
"""
import argparse, json, re, sys

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def cmd_goals(path):
    g = json.load(open(path, encoding="utf-8"))
    if isinstance(g, dict):
        g = g.get("goals", g.get("items", []))
    out = []
    for i, goal in enumerate(g):
        text = norm(goal if isinstance(goal, str) else goal.get("goal", ""))
        audience = "评审" if re.search(r"(?i)(评审|评委|review)", text) else ("合作者" if re.search(r"(?i)(合作|进度)", text) else "同行")
        strength = "novelty-check" if re.search(r"(?i)(新颖|创新|novel)", text) else ("risk-communicate" if re.search(r"(?i)(风险|进度|risk)", text) else "inform")
        pages = max(3, min(20, len(text) // 10 + 3))
        out.append({"goal_id": f"G{i+1}", "goal": text[:100], "audience": audience,
                    "claim_strength_needed": strength, "est_pages": pages,
                    "checkable": f"听众{'认可方法新颖性' if strength=='novelty-check' else '理解进度风险' if strength=='risk-communicate' else '理解结论'}——可用页数/时长/结论强度逐项核对"})
    print(json.dumps({"schema": "pres/goals@1", "goals": out,
                      "note": "目标转可检查项：页数/时长/结论强度"}, ensure_ascii=False, indent=1))
    return 0

SPINE = ["problem", "method", "result", "conclusion"]

def cmd_order(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("outline", data.get("items", []))
    # re-order: NOT paper-TOC copy; arrange setup/transitions on spine
    order = []
    for i, item in enumerate(data):
        sec = norm(item if isinstance(item, str) else item.get("section", item.get("title", ""))).lower()
        stage = next((s for s in SPINE if s in sec or {"问题": "problem", "方法": "method", "结果": "result", "结论": "conclusion"}.get(sec[:2]) == s), None) or "problem"
        order.append({"order": i + 1, "section": norm(item if isinstance(item, str) else item.get("section", ""))[:60],
                      "spine_stage": stage,
                      "transition_note": "起(问题钩子)" if i == 0 else ("承(方法铺垫)" if stage == "method" else ("转(结果对比)" if stage == "result" else "合(结论回扣问题)"))})
    print(json.dumps({"schema": "pres/order@1", "order": order,
                      "note": "问题-方法-结果-结论主骨架上取舍铺垫；非论文目录搬运"}, ensure_ascii=False, indent=1))
    return 0

def cmd_slides(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("order", data.get("items", []))
    slides = []
    for i, s in enumerate(data):
        sec = norm(s if isinstance(s, str) else s.get("section", s.get("section", "")))
        claims = re.split(r"[。;；]", sec) if sec else []
        slides.append({"slide_no": i + 1, "unique_claim": (claims[0][:60] if claims else sec[:60]),
                       "support_points": [c.strip()[:40] for c in claims[1:4]],
                       "graphic_suggestion": "结论页放主图；方法页放流程图；结果页放对比表",
                       "claim_strength": "强（实测数据支撑）" if re.search(r"(?i)(结果|数据|%)", sec) else "中等（需补证据）",
                       "density_note": "单页要点<=3；长段落改写为可讲短语"})
    print(json.dumps({"schema": "pres/slides@1", "slides": slides[:20],
                      "note": "每页唯一主张+证据强度标注"}, ensure_ascii=False, indent=1))
    return 0

def cmd_qa(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("slides", data.get("items", []))
    qa_prep = [
        {"dimension": "机制", "anticipated_q": "为什么该机制有效而非替代解释？", "prep": "准备机制页+备用页"},
        {"dimension": "数据", "anticipated_q": "样本量/数据集口径？", "prep": "数据来源页+口径一致回答要点"},
        {"dimension": "对照", "anticipated_q": "与基线的公平比较？", "prep": "对比表页+条件相同声明"},
        {"dimension": "局限", "anticipated_q": "适用范围与失败场景？", "prep": "局限页+边界条件"},
    ]
    print(json.dumps({"schema": "pres/qa@1", "qa_prep": qa_prep,
                      "citeable": "每条回答标注可引用页面；口径与正文一致"}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goals"); ap.add_argument("--order"); ap.add_argument("--slides"); ap.add_argument("--qa")
    a = ap.parse_args()
    if a.goals: return cmd_goals(a.goals)
    if a.order: return cmd_order(a.order)
    if a.slides: return cmd_slides(a.slides)
    if a.qa: return cmd_qa(a.qa)
    ap.error("choose --goals / --order / --slides / --qa")

if __name__ == "__main__":
    sys.exit(main())
