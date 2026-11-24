"""Gap analysis: research-gap claims must be grounded in actual search gaps.

A research gap ("研究空白") is only as good as its provenance. The engine maps
executed queries onto the subquestion plan and validates each gap statement:
  - type searched_no_evidence   : queries ran for this subquestion, nothing
                                  relevant returned  -> gap MUST cite query ids
  - type searched_insufficient  : something returned but below evidence_required
                                  -> cite query ids AND the shortfall numbers
  - type conflict_unresolved    : evidence exists but conflicts (needs conflict
                                  id from the evidence matrix)
  - type scope_exclusion        : never searched (out of scope / speculation)
                                  -> MUST be labelled speculation, may NOT be
                                  presented as an evidence-based finding

Queries file: {"queries": [{"id": "q1", "subq_id": "Q1", "string": "...",
               "source": "crossref", "returned": 12, "kept": 3}]}
Gaps file:    {"gaps": [{"id": "G1", "subq_id": "Q3", "statement": "...",
               "type": "searched_no_evidence", "query_ids": ["q5", "q6"],
               "conflict_id": null, "speculation": false}]}
"""
from __future__ import annotations

import json
import sys

VALID_TYPES = {"searched_no_evidence", "searched_insufficient",
               "conflict_unresolved", "scope_exclusion"}


def coverage_map(plan: dict, queries: list[dict], evidence: list[dict] | None = None) -> dict:
    """Per-subquestion search coverage: how many queries ran, what came back."""
    ev_by_sub: dict[str, int] = {}
    for e in evidence or []:
        sid = str(e.get("subq_id") or "")
        ev_by_sub[sid] = ev_by_sub.get(sid, 0) + len(e.get("record_ids") or [])
    q_by_sub: dict[str, list[dict]] = {}
    for q in queries:
        q_by_sub.setdefault(str(q.get("subq_id") or ""), []).append(q)
    rows = []
    for s in plan.get("subquestions") or []:
        sid = str(s.get("id"))
        qs = q_by_sub.get(sid, [])
        returned = sum(int(q.get("returned") or 0) for q in qs)
        kept = sum(int(q.get("kept") or 0) for q in qs)
        need = int(s.get("evidence_required") or 1)
        ev = ev_by_sub.get(sid, 0)
        if not qs:
            status = "unsearched"
        elif ev >= need:
            status = "covered"
        else:
            status = "thin"
        rows.append({"subq_id": sid, "queries": [q.get("id") for q in qs],
                     "n_queries": len(qs), "returned": returned, "kept": kept,
                     "evidence_records": ev, "evidence_required": need, "status": status})
    return {"per_subquestion": rows,
            "unsearched": [r["subq_id"] for r in rows if r["status"] == "unsearched"],
            "thin": [r["subq_id"] for r in rows if r["status"] == "thin"],
            "note": "空白只能建立在 unsearched/thin 的如实记录上；'没检索到'不等于'不存在'"}


def validate_gaps(gaps: list[dict], cov: dict, conflict_ids: set[str] | None = None) -> dict:
    by_sub = {r["subq_id"]: r for r in cov.get("per_subquestion") or []}
    problems, rows = [], []
    for g in gaps:
        gid = str(g.get("id"))
        gt = str(g.get("type") or "")
        sid = str(g.get("subq_id") or "")
        qids = [str(x) for x in (g.get("query_ids") or [])]
        spec = bool(g.get("speculation"))
        if not (g.get("statement") or "").strip():
            problems.append({"gap": gid, "problem": "empty statement"})
        if gt not in VALID_TYPES:
            problems.append({"gap": gid, "problem": f"type must be one of {sorted(VALID_TYPES)}"})
            continue
        row = by_sub.get(sid)
        if gt in ("searched_no_evidence", "searched_insufficient"):
            if not qids:
                problems.append({"gap": gid,
                                 "problem": f"{gt} gap without query_ids; 空白主张必须回指"
                                            "实际执行过的检索式"})
            elif row is not None:
                known = set(row["queries"])
                unknown = [q for q in qids if q not in known]
                if unknown:
                    problems.append({"gap": gid,
                                     "problem": f"query_ids not executed for {sid}: {unknown} "
                                                "(不得引用未运行的检索)"})
            if spec:
                problems.append({"gap": gid,
                                 "problem": "searched_* gap must not be marked speculation"})
            if gt == "searched_no_evidence" and row is not None and row["kept"] > 0 \
                    and row["evidence_records"] > 0:
                problems.append({"gap": gid,
                                 "problem": f"{sid} actually kept {row['kept']} records with "
                                            "evidence; 'no evidence' 与检索记录矛盾"})
        elif gt == "conflict_unresolved":
            cid = str(g.get("conflict_id") or "")
            if conflict_ids is not None and cid not in conflict_ids:
                problems.append({"gap": gid,
                                 "problem": f"conflict_id '{cid}' not in evidence matrix"})
        elif gt == "scope_exclusion":
            if not spec:
                problems.append({"gap": gid,
                                 "problem": "未检索范围的空白必须标记 speculation:true，"
                                            "不得伪装成基于证据的发现"})
        rows.append({"gap": gid, "subq_id": sid, "type": gt, "grounded": not any(
            p["gap"] == gid for p in problems)})
    return {"ok": not problems, "gaps": len(rows), "problems": problems, "per_gap": rows,
            "note": "套话式空白（'有待进一步研究'而无检索依据）会被拒绝"}


def _demo() -> int:
    plan = {"subquestions": [{"id": "Q1", "evidence_required": 1},
                             {"id": "Q2", "evidence_required": 2},
                             {"id": "Q3", "evidence_required": 1}]}
    queries = [{"id": "q1", "subq_id": "Q1", "string": "x AND y", "returned": 20, "kept": 4},
               {"id": "q2", "subq_id": "Q2", "string": "x AND z", "returned": 3, "kept": 1},
               {"id": "q3", "subq_id": "Q3", "string": "x AND w", "returned": 0, "kept": 0}]
    evidence = [{"subq_id": "Q1", "record_ids": ["R1", "R2"], "quotes": ["..."]},
                {"subq_id": "Q2", "record_ids": ["R3"], "quotes": ["..."]}]
    cov = coverage_map(plan, queries, evidence)
    assert cov["unsearched"] == [] and cov["thin"] == ["Q2", "Q3"]
    gaps = [{"id": "G1", "subq_id": "Q3", "statement": "X 与 W 的关系无任何研究",
             "type": "searched_no_evidence", "query_ids": ["q3"]},
            {"id": "G2", "subq_id": "Q2", "statement": "剂量-效应关系证据不足",
             "type": "searched_insufficient", "query_ids": ["q2"]},
            {"id": "G3", "subq_id": "Q1", "statement": "儿童人群完全未涉及",
             "type": "scope_exclusion", "speculation": True}]
    rep = validate_gaps(gaps, cov)
    assert rep["ok"], rep["problems"]
    # negative: evidence-based gap claiming a query that never ran
    bad = [{"id": "G9", "subq_id": "Q1", "statement": "x",
            "type": "searched_no_evidence", "query_ids": ["q99"]}]
    assert not validate_gaps(bad, cov)["ok"]
    # negative: 'no evidence' where evidence exists
    bad2 = [{"id": "G8", "subq_id": "Q1", "statement": "x",
             "type": "searched_no_evidence", "query_ids": ["q1"]}]
    assert not validate_gaps(bad2, cov)["ok"]
    # negative: unsearched gap disguised as finding
    bad3 = [{"id": "G7", "subq_id": "Q1", "statement": "x",
             "type": "scope_exclusion", "speculation": False}]
    assert not validate_gaps(bad3, cov)["ok"]
    print(json.dumps({"demo": "gaps", "coverage": {r["subq_id"]: r["status"]
                      for r in cov["per_subquestion"]},
                      "gaps_ok": f"{rep['gaps']}/3",
                      "ungrounded_gap_rejected": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "map":
        plan = json.load(open(sys.argv[2], encoding="utf-8"))
        qs = json.load(open(sys.argv[3], encoding="utf-8"))
        ev = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else []
        rep = coverage_map(plan, qs.get("queries", qs), ev.get("evidence", ev) if isinstance(ev, dict) else ev)
        out = sys.argv[5] if len(sys.argv) > 5 else None
    elif cmd == "validate":
        gaps = json.load(open(sys.argv[2], encoding="utf-8"))
        cov = json.load(open(sys.argv[3], encoding="utf-8"))
        cids = set(json.load(open(sys.argv[5], encoding="utf-8"))) if len(sys.argv) > 5 else None
        rep = validate_gaps(gaps.get("gaps", gaps), cov, cids)
        out = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        print("usage: gaps.py map plan.json queries.json [evidence.json] [out.json]\n"
              "       gaps.py validate gaps.json coverage.json [out.json] [conflict_ids.json]")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False)[:600])
