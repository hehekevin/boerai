"""Question decomposition & search planning with dependency tracking
(challenge: 科研问题驱动检索).

The agent writes the decomposition; the engine validates structure, tracks
per-subquestion evidence sufficiency, and computes whether the plan is
complete enough to stop.
"""
from __future__ import annotations

import json
import sys


def validate_plan(plan: dict) -> dict:
    """plan: {question, subquestions: [{id, text, searchable_terms, depends_on:[ids],
    evidence_required}]}"""
    subs = plan.get("subquestions") or []
    ids = [s.get("id") for s in subs]
    problems = []
    if len(ids) != len(set(ids)):
        problems.append("duplicate subquestion ids")
    for s in subs:
        if not s.get("text"):
            problems.append(f"{s.get('id')}: empty text")
        if not s.get("searchable_terms"):
            problems.append(f"{s.get('id')}: no searchable terms (not independently retrievable)")
        for dep in s.get("depends_on") or []:
            if dep not in ids:
                problems.append(f"{s.get('id')}: depends on unknown '{dep}'")
            if dep == s.get("id"):
                problems.append(f"{s.get('id')}: self dependency")
    # cycle check
    deps = {s.get("id"): set(s.get("depends_on") or []) for s in subs}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in ids}
    cyc = []

    def visit(u, stack):
        color[u] = GRAY
        for v in deps.get(u, ()):
            if color.get(v) == GRAY:
                cyc.append(stack + [v])
            elif color.get(v) == WHITE:
                visit(v, stack + [v])
        color[u] = BLACK

    for i in ids:
        if color[i] == WHITE:
            visit(i, [i])
    if cyc:
        problems.append(f"dependency cycle: {cyc[0]}")
    order = [s["id"] for s in sorted(subs, key=lambda s: len(s.get("depends_on") or []))]
    return {"ok": not problems, "problems": problems, "subquestions": len(subs),
            "suggested_order": order,
            "note": "每个子问题必须可独立检索（searchable_terms 非空），依赖不得成环"}


def sufficiency(plan: dict, evidence: list[dict]) -> dict:
    """evidence: [{subq_id, record_ids:[...], quotes:[...]}]"""
    by_sub = {}
    for e in evidence:
        by_sub.setdefault(str(e.get("subq_id")), []).append(e)
    rows, done = [], 0
    for s in plan.get("subquestions") or []:
        sid = str(s.get("id"))
        ev = by_sub.get(sid, [])
        need = int(s.get("evidence_required") or 1)
        n_rec = len({r for e in ev for r in (e.get("record_ids") or [])})
        enough = n_rec >= need and any(e.get("quotes") for e in ev)
        done += 1 if enough else 0
        rows.append({"subq_id": sid, "evidence_items": n_rec, "required": need,
                     "has_quotes": any(e.get("quotes") for e in ev),
                     "sufficient": enough,
                     "action": "none" if enough else "retrieve_more_or_mark_gap"})
    return {"subquestions": len(rows), "sufficient": done,
            "complete": done == len(rows) and len(rows) > 0, "per_subquestion": rows,
            "note": "停止条件：全部子问题证据充分，或缺口已显式标注；不得以轮数代替充分性"}


def _demo() -> int:
    plan = {"question": "Does X improve Y in Z?",
            "subquestions": [
                {"id": "S1", "text": "What is X?", "searchable_terms": ["X definition"], "depends_on": []},
                {"id": "S2", "text": "Effect of X on Y", "searchable_terms": ["X", "Y", "effect"],
                 "depends_on": ["S1"], "evidence_required": 2},
                {"id": "S3", "text": "Context Z", "searchable_terms": ["Z"], "depends_on": []}]}
    v = validate_plan(plan)
    assert v["ok"] and v["subquestions"] == 3
    bad = dict(plan)
    bad["subquestions"] = plan["subquestions"] + [{"id": "S1", "text": "dup", "searchable_terms": []}]
    assert not validate_plan(bad)["ok"]
    ev = [{"subq_id": "S1", "record_ids": ["R1"], "quotes": ["X is ..."]},
          {"subq_id": "S2", "record_ids": ["R2", "R3"], "quotes": ["X increased Y"]}]
    suf = sufficiency(plan, ev)
    assert not suf["complete"] and suf["sufficient"] == 2
    print(json.dumps({"demo": "qplan", "plan_ok": v["ok"], "sufficient": f"{suf['sufficient']}/{suf['subquestions']}",
                      "next": [r["subq_id"] for r in suf["per_subquestion"] if not r["sufficient"]]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    plan = json.load(open(sys.argv[2], encoding="utf-8"))
    if cmd == "validate":
        rep = validate_plan(plan)
    elif cmd == "sufficiency":
        ev = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = sufficiency(plan, ev.get("evidence", ev))
    else:
        print("usage: qplan.py [validate|sufficiency] plan.json out.json [evidence.json]")
        sys.exit(2)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": rep.get("ok", rep.get("complete")), "->": sys.argv[3]}))
