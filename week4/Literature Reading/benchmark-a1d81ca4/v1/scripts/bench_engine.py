#!/usr/bin/env python3
"""bench-engine: literature-reading benchmark & evaluation toolkit.

Deterministic subcommands (0 model requests):
  --validate-card CARD_JSON   validate question card fields (task/input/reference/rubric/difficulty/license)
  --score RUBRIC_JSON OUTPUTS_JSON  rule scoring per 0/1/2 with rationale; deterministic subset
  --panel RESULTS_JSON        aggregate panel data (by question-type/agent/cardset-version)
Stdlib only.
"""
import argparse, json, re, sys

CARD_FIELDS = {"task", "input_material", "reference_answer", "scoring_rubric", "difficulty", "data_license"}

def cmd_validate_card(path):
    card = json.load(open(path, encoding="utf-8"))
    missing = [f for f in CARD_FIELDS if f not in card or not card[f]]
    checks = []
    # inter-rater determinism probe: rubric must be checkable
    rubric = card.get("scoring_rubric", "")
    deterministic = bool(re.search(r"(?i)(精确匹配|关键词|json|schema|包含|exact|keyword)", rubric)) if isinstance(rubric, str) else False
    if isinstance(rubric, dict):
        deterministic = any(re.search(r"(?i)(exact|keyword|包含|匹配)", str(v)) for v in rubric.values())
    checks.append({"check": "rubric_deterministic", "pass": deterministic,
                   "note": "不同人看同一份输出能否同一结论——规则须可机械判定或明确人工流程"})
    checks.append({"check": "reference_answer_present", "pass": bool(card.get("reference_answer"))})
    checks.append({"check": "data_license", "pass": bool(card.get("data_license"))})
    verdict = "valid" if not missing and all(c["pass"] for c in checks) else "invalid"
    print(json.dumps({"schema": "bench/card@1", "verdict": verdict, "missing_fields": missing, "checks": checks,
                      "note": "题卡缺字段=不可判定"}, ensure_ascii=False, indent=1))
    return 0 if verdict == "valid" else 1

def cmd_score(rubric_path, outputs_path):
    rubric = json.load(open(rubric_path, encoding="utf-8"))
    outputs = json.load(open(outputs_path, encoding="utf-8"))
    if isinstance(outputs, dict):
        outputs = outputs.get("outputs", [])
    scored = []
    for o in outputs:
        qid = o.get("question_id", "")
        ref = rubric.get("reference", {}).get(qid, "")
        ans = str(o.get("answer", ""))
        # deterministic scoring: exact/keyword containment
        if isinstance(ref, list):
            kws = ref
            hits = [k for k in kws if k.lower() in ans.lower()]
            s = 2 if len(hits) == len(kws) else (1 if hits else 0)
            rationale = f"关键词命中 {len(hits)}/{len(kws)}: {hits[:3]}"
        else:
            s = 2 if ans.strip().lower() == str(ref).strip().lower() else (1 if ref and ref.lower() in ans.lower() else 0)
            rationale = "精确匹配" if s == 2 else ("包含匹配" if s == 1 else "未命中")
        scored.append({"question_id": qid, "score": s, "rationale": rationale,
                       "dispute_flag": s == 1, "note": "1分（部分命中）建议人工复核"})
    total = sum(x["score"] for x in scored)
    print(json.dumps({"schema": "bench/score@1", "n_questions": len(scored), "total": total,
                      "max_total": 2 * len(scored), "scored": scored,
                      "note": "0/1/2 记分；判分依据与争议保留"}, ensure_ascii=False, indent=1))
    return 0

def cmd_panel(results_path):
    data = json.load(open(results_path, encoding="utf-8"))
    rows = data.get("results", data if isinstance(data, list) else [])
    panel = {}
    for r in rows:
        key = (r.get("question_type", "?"), r.get("agent", "?"), r.get("cardset_version", "?"))
        panel.setdefault(str(key), {"n": 0, "sum": 0, "fluctuations": []})
        panel[str(key)]["n"] += 1
        panel[str(key)]["sum"] += r.get("score", 0)
    out = []
    for k, v in panel.items():
        out.append({"group": k, "n": v["n"], "avg": round(v["sum"] / max(1, v["n"]), 2),
                    "traceability": "每个分数可顺题目ID追到原始输出/运行配置/评分记录"})
    print(json.dumps({"schema": "bench/panel@1", "groups": out,
                      "rerun_note": "固定工具权限与预算下重复运行的分数波动单独记录并解释"}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-card")
    ap.add_argument("--score", nargs=2)
    ap.add_argument("--panel")
    a = ap.parse_args()
    if a.validate_card: return cmd_validate_card(a.validate_card)
    if a.score: return cmd_score(a.score[0], a.score[1])
    if a.panel: return cmd_panel(a.panel)
    ap.error("choose --validate-card / --score / --panel")

if __name__ == "__main__":
    sys.exit(main())
