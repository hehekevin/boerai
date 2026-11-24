"""Synthesis audit: classify every conclusion sentence and bound every claim.

Each conclusion sentence in the review/synthesis must be classified by the
agent as exactly one of:
  fact          材料事实  -- directly stated in the cited source passage(s)
  inference     合理推断  -- follows from >=1 cited passage; basis required
  undetermined  无法确定  -- evidence missing/conflicting; basis must say what
Engine rules:
  - fact/inference sentences MUST cite >=1 claim id that exists in the
    validated evidence matrix (no dangling citations, no invented support)
  - inference requires a non-empty basis (the reasoning step)
  - undetermined requires a basis stating what is missing; this is honest
    required behaviour, never a failure
  - coverage: every subquestion in the plan must be addressed by >=1
    conclusion OR explicitly listed in gaps[] -- silent omission fails

Synthesis file:
{"conclusions": [{"id": "N1", "sentence": "...", "class": "fact|inference|undetermined",
                  "subq_id": "Q1", "claim_ids": ["C1"], "basis": "..."}],
 "gaps": [{"subq_id": "Q3", "reason": "...", "gap_id": "G1"}]}
"""
from __future__ import annotations

import json
import sys

VALID_CLASSES = {"fact", "inference", "undetermined"}
MIN_BASIS = 10


def audit_synthesis(synthesis: dict, matrix: dict, plan: dict | None = None) -> dict:
    valid_claims = {str(c.get("id")) for c in matrix.get("claims") or []}
    problems, rows = [], []
    for n in synthesis.get("conclusions") or []:
        nid = str(n.get("id"))
        cls = str(n.get("class") or "")
        sent = (n.get("sentence") or "").strip()
        cids = [str(x) for x in (n.get("claim_ids") or [])]
        basis = (n.get("basis") or "").strip()
        if not sent:
            problems.append({"conclusion": nid, "problem": "empty sentence"})
        if cls not in VALID_CLASSES:
            problems.append({"conclusion": nid,
                             "problem": f"class must be one of {sorted(VALID_CLASSES)} "
                                        "(材料事实/合理推断/无法确定)"})
            continue
        dangling = [c for c in cids if c not in valid_claims]
        if dangling:
            problems.append({"conclusion": nid,
                             "problem": f"claim_ids not in evidence matrix: {dangling} "
                                        "(疑似编造引用)"})
        if cls in ("fact", "inference") and not cids:
            problems.append({"conclusion": nid,
                             "problem": f"{cls} sentence without any supporting claim; "
                                        "结论句必须回链"})
        if cls == "inference" and len(basis) < MIN_BASIS:
            problems.append({"conclusion": nid,
                             "problem": "inference requires basis describing the reasoning step"})
        if cls == "undetermined" and len(basis) < MIN_BASIS:
            problems.append({"conclusion": nid,
                             "problem": "undetermined requires basis stating exactly what is "
                                        "missing (如实说明是诚实行为，但必须说清缺什么)"})
        rows.append({"conclusion": nid, "class": cls, "subq_id": str(n.get("subq_id") or ""),
                     "claims": len(cids), "ok": not any(p["conclusion"] == nid for p in problems)})
    rep = {"ok": not problems, "conclusions": len(rows),
           "by_class": {c: sum(1 for r in rows if r["class"] == c) for c in sorted(VALID_CLASSES)},
           "problems": problems, "per_conclusion": rows}
    if plan is not None:
        rep["coverage"] = check_coverage(synthesis, plan)
        if rep["coverage"]["silently_omitted"]:
            rep["ok"] = False
            rep["problems"] = problems + [{"conclusion": "*",
                                           "problem": "subquestions silently omitted: "
                                           f"{rep['coverage']['silently_omitted']}; 每个子问题必须被"
                                           "结论覆盖或显式标注为缺口"}]
    return rep


def check_coverage(synthesis: dict, plan: dict) -> dict:
    addressed = {str(n.get("subq_id") or "") for n in synthesis.get("conclusions") or []}
    gapped = {str(g.get("subq_id") or "") for g in synthesis.get("gaps") or []}
    rows, omitted = [], []
    for s in plan.get("subquestions") or []:
        sid = str(s.get("id"))
        if sid in addressed:
            st = "addressed"
        elif sid in gapped:
            st = "explicit_gap"
        else:
            st = "silently_omitted"
            omitted.append(sid)
        rows.append({"subq_id": sid, "status": st})
    return {"per_subquestion": rows, "silently_omitted": omitted,
            "complete": not omitted,
            "note": "显式缺口是合法收尾；静默遗漏不是"}


def _demo() -> int:
    matrix = {"claims": [{"id": "C1"}, {"id": "C2"}]}
    plan = {"subquestions": [{"id": "Q1"}, {"id": "Q2"}, {"id": "Q3"}]}
    syn = {"conclusions": [
        {"id": "N1", "sentence": "X 在该数据集中提高 Y。", "class": "fact",
         "subq_id": "Q1", "claim_ids": ["C1"]},
        {"id": "N2", "sentence": "X 的效果可能随剂量增强。", "class": "inference",
         "subq_id": "Q2", "claim_ids": ["C1", "C2"],
         "basis": "两项研究剂量梯度与效应量同向变化"},
        {"id": "N3", "sentence": "长期安全性无法确定。", "class": "undetermined",
         "subq_id": "Q2", "claim_ids": [],
         "basis": "纳入研究随访均短于 6 个月，无长期数据"}],
        "gaps": [{"subq_id": "Q3", "reason": "检索无相关记录", "gap_id": "G1"}]}
    rep = audit_synthesis(syn, matrix, plan)
    assert rep["ok"], rep["problems"]
    assert rep["by_class"] == {"fact": 1, "inference": 1, "undetermined": 1}
    assert rep["coverage"]["complete"]
    # negative: dangling citation (fabricated support) must be rejected
    bad = {"conclusions": [{"id": "N9", "sentence": "断言", "class": "fact",
                            "subq_id": "Q1", "claim_ids": ["C99"]}]}
    assert not audit_synthesis(bad, matrix)["ok"]
    # negative: silently omitted subquestion must fail coverage
    bad2 = {"conclusions": [syn["conclusions"][0]], "gaps": []}
    r2 = audit_synthesis(bad2, matrix, plan)
    assert not r2["ok"] and set(r2["coverage"]["silently_omitted"]) == {"Q2", "Q3"}
    # undetermined without basis is rejected (honesty must be specific)
    bad3 = {"conclusions": [{"id": "N8", "sentence": "不知道", "class": "undetermined",
                             "subq_id": "Q1", "basis": ""}]}
    assert not audit_synthesis(bad3, matrix)["ok"]
    print(json.dumps({"demo": "synthesis", "by_class": rep["by_class"],
                      "coverage_complete": rep["coverage"]["complete"],
                      "fabricated_citation_rejected": True,
                      "silent_omission_rejected": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    syn = json.load(open(sys.argv[2], encoding="utf-8"))
    matrix = json.load(open(sys.argv[3], encoding="utf-8"))
    if cmd == "audit":
        plan = json.load(open(sys.argv[5], encoding="utf-8")) if len(sys.argv) > 5 else None
        rep = audit_synthesis(syn, matrix, plan)
    elif cmd == "coverage":
        plan = json.load(open(sys.argv[5], encoding="utf-8"))
        rep = check_coverage(syn, plan)
    else:
        print("usage: synthesis.py [audit|coverage] synthesis.json matrix.json out.json [plan.json]")
        sys.exit(2)
    json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": rep.get("ok", rep.get("complete")), "->": sys.argv[4]},
                     ensure_ascii=False))
