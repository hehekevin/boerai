#!/usr/bin/env python3
"""question-driven-search-forge: research-question decomposition -> element matrix -> query plan.

Deterministic subcommands (0 model requests):
  --decompose QUESTION      decompose question into element matrix (PICO-like slots + evidence requirements)
  --plan MATRIX_JSON        generate per-element query fragments + combination templates + round plan
  --rounds LEDGER_JSON      multi-round planning: next-round queries from gap analysis
  --stop LEDGER_JSON        stop conditions (same criteria family as iterative agent)
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata

ELEMENT_SLOTS = [
    {"slot": "object", "label": "研究对象", "hint": "人群/材料/分子/系统"},
    {"slot": "mechanism", "label": "机制/现象", "hint": "被研究的过程或效应"},
    {"slot": "method", "label": "方法", "hint": "技术/算法/实验手段"},
    {"slot": "time_range", "label": "时间范围", "hint": "出版年份或研究期间；无则N/A"},
    {"slot": "comparison", "label": "比较关系", "hint": "对照组/基线；无则N/A"},
    {"slot": "evidence", "label": "证据要求", "hint": "需要的证据类型（实验/综述/数据集）"},
]


def cmd_decompose(question):
    """Slot skeleton + domain-dictionary extraction (deterministic)."""
    q = unicodedata.normalize("NFKC", question or "").strip()
    # Domain dictionary: match IN the sentence (no CJK tokenization needed)
    DOMAIN_DICT = {
        "method": ["深度学习", "机器学习", "强化学习", "神经网络", "transformer", "图神经网络", "回归", "仿真", "算法", "大模型", "Transformer", "GAN", "扩散模型", "卷积"],
        "object": ["肿瘤", "癌症", "cancer", "细胞", "蛋白", "患者", "影像", "图像", "文献", "材料", "组织", "样本", "molecule", "protein"],
        "mechanism": ["诊断", "检测", "预测", "分割", "疗效", "通路", "机制", "关联", "分类", "识别", "追踪", "优化", "生成"],
        "comparison": ["对比", "相比", "对照", "versus", "vs", "基线", "提升", "优于"],
        "evidence": ["综述", "review", "meta", "数据集", "dataset", "实验", "trial", "基准", "benchmark"],
    }
    matrix = {"schema": "qdriven/decompose@1", "question": q, "elements": []}
    used = set()
    for slot in ELEMENT_SLOTS:
        entry = {"slot": slot["slot"], "label": slot["label"], "hint": slot["hint"], "extracted_terms": [], "extraction_basis": ""}
        if slot["slot"] == "time_range":
            m = re.search(r"(20\d{2})\s*[-~到至]\s*(20\d{2})", q)
            if m:
                entry["extracted_terms"] = [m.group(0)]
                entry["extraction_basis"] = "年份区间正则"
            else:
                m2 = re.search(r"(20\d{2})", q)
                entry["extracted_terms"] = [m2.group(1)] if m2 else ["N/A"]
                entry["extraction_basis"] = "单年份正则" if m2 else "题面未出现年份"
            matrix["elements"].append(entry)
            continue
        if slot["slot"] == "comparison":
            found = [w for w in DOMAIN_DICT["comparison"] if re.search(re.escape(w), q, re.I) and w not in used]
            entry["extracted_terms"] = found or ["N/A"]
            entry["extraction_basis"] = "比较词词典直查" if found else "题面未出现比较词"
            used.update(found)
            matrix["elements"].append(entry)
            continue
        words = DOMAIN_DICT.get(slot["slot"], [])
        found = [w for w in words if re.search(re.escape(w), q, re.I) and w not in used]
        entry["extracted_terms"] = found or []
        entry["extraction_basis"] = f"领域词典直查({slot['slot']})"
        used.update(found)
        matrix["elements"].append(entry)
    gaps = [e["slot"] for e in matrix["elements"] if not e["extracted_terms"] or e["extracted_terms"] == ["N/A"]]
    matrix["gaps_for_model"] = gaps
    matrix["note"] = f"槽位 {gaps} 未能确定性提取——需模型语义补充后回填，补充词记录 extraction_basis=model"
    print(json.dumps(matrix, ensure_ascii=False, indent=1))
    return 0


def cmd_plan(matrix_path):
    m = json.load(open(matrix_path, encoding="utf-8"))
    elems = m.get("elements", [])
    frag = []
    for e in elems:
        terms = [t for t in e.get("extracted_terms", []) if t != "N/A"]
        if terms:
            frag.append({"slot": e["slot"], "fragment": "(" + " OR ".join('"%s"' % t for t in terms[:5]) + ")"})
    core = [f["fragment"] for f in frag if f["slot"] in ("object", "mechanism", "method")]
    plan = {"schema": "qdriven/plan@1", "fragments": frag, "templates": []}
    if core:
        plan["templates"].append({"name": "R1-core", "query": " AND ".join(core[:3])})
        plan["templates"].append({"name": "R1-broad", "query": " OR ".join(core[:2])})
    plan["round_plan"] = [
        {"round": 1, "purpose": "核心要素合取，建立基线命中集", "queries": ["R1-core"]},
        {"round": 2, "purpose": "补术语扩展与放宽字段，覆盖 R1 遗漏", "queries": ["R1-broad", "synonym-expanded"], "depends": "R1 漏检归因"},
        {"round": 3, "purpose": "冲突证据验证与缺口补检", "queries": ["gap-driven"], "depends": "R2 评估"},
    ]
    print(json.dumps(plan, ensure_ascii=False, indent=1))
    return 0


def cmd_rounds(ledger_path):
    """Multi-round planning: read executed-round ledger, propose next-round queries."""
    ledger = json.load(open(ledger_path, encoding="utf-8"))
    rounds = ledger.get("rounds", [])
    executed = [r["round"] for r in rounds]
    next_round = (max(executed) + 1) if executed else 1
    gains = [r.get("marginal_gain") for r in rounds[1:] if r.get("marginal_gain") is not None]
    proposal = {"schema": "qdriven/rounds@1", "executed_rounds": executed, "next_round": next_round}
    if gains and gains[-1] == 0:
        proposal["action"] = "stop_or_switch_strategy"
        proposal["reason"] = "最后轮边际收益为0"
    elif not rounds:
        proposal["action"] = "start_R1_core"
    else:
        proposal["action"] = "continue_with_gap_queries"
        proposal["gap_queries"] = ["synonym-expanded", "field-relaxed"]
    print(json.dumps(proposal, ensure_ascii=False, indent=1))
    return 0


def cmd_stop(ledger_path):
    ledger = json.load(open(ledger_path, encoding="utf-8"))
    rounds = ledger.get("rounds", [])
    gains = [r.get("marginal_gain") for r in rounds[1:] if r.get("marginal_gain") is not None]
    reasons = []
    if gains and gains[-1] == 0:
        reasons.append({"type": "marginal_gain", "detail": "最后轮新增为0"})
    if len(rounds) >= 5:
        reasons.append({"type": "max_rounds", "detail": "已达5轮"})
    evidence_sufficient = len(reasons) == 0 and len(rounds) >= 2
    print(json.dumps({"schema": "qdriven/stop@1", "should_stop": bool(reasons),
                      "evidence_sufficient": evidence_sufficient,
                      "stop_reasons": reasons,
                      "human_needed": len(rounds) >= 4 and len(reasons) == 0}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decompose")
    ap.add_argument("--plan")
    ap.add_argument("--rounds")
    ap.add_argument("--stop")
    a = ap.parse_args()
    if a.decompose:
        return cmd_decompose(a.decompose)
    if a.plan:
        return cmd_plan(a.plan)
    if a.rounds:
        return cmd_rounds(a.rounds)
    if a.stop:
        return cmd_stop(a.stop)
    ap.error("choose --decompose / --plan / --rounds / --stop")


if __name__ == "__main__":
    sys.exit(main())
