"""Evidence matrix: every conclusion sentence links to specific source passages.

The agent writes claims and picks supporting quotes; the engine guarantees:
  - every claim has >=1 support with a verbatim quote AND a locator
    (file path + page/paragraph/line) AND a source_id registered in sources
  - quotes are non-trivial (min length), so "见文献" style empty citations fail
  - conflict pairs reference real claims and every adjudication compares the
    two sides' evidence -- a bare "尚存争议" without comparison is rejected

Matrix file:
{"sources": [{"id": "S1", "title": "...", "path": "materials/xxx.txt"}],
 "claims": [{"id": "C1", "text": "...", "subq_id": "Q2",
             "supports": [{"source_id": "S1", "quote": "...", "locator": "p.3 ¶2"}]}],
 "conflicts": [{"id": "K1", "claim_a": "C1", "claim_b": "C4", "topic": "...",
                "adjudication": {"comparison": "...", "resolution":
                  "a_stronger|b_stronger|both_bounded|genuinely_unresolved",
                  "basis": "..."}}]}
"""
from __future__ import annotations

import json
import sys

MIN_QUOTE = 8  # characters; shorter strings cannot pin a passage

# deterministic cue words that *suggest* two claims on the same subquestion
# may conflict; the agent must confirm -- the engine only surfaces candidates
_POS_CUES = ("提高", "改善", "显著", "有效", "支持", "促进", "increase", "improve",
             "significant", "effective", "supports", "outperform")
_NEG_CUES = ("降低", "无效", "不显著", "未观察到", "反对", "恶化", "decrease",
             "no effect", "not significant", "failed", "worse", "contradict")


def _has_cue(text: str, cues) -> bool:
    t = (text or "").lower()
    return any(c in t for c in cues)


def validate_matrix(matrix: dict) -> dict:
    sources = {str(s.get("id")) for s in matrix.get("sources") or []}
    claims = matrix.get("claims") or []
    problems, rows = [], []
    seen = set()
    for c in claims:
        cid = str(c.get("id"))
        if cid in seen:
            problems.append({"claim": cid, "problem": "duplicate claim id"})
        seen.add(cid)
        if not (c.get("text") or "").strip():
            problems.append({"claim": cid, "problem": "empty claim text"})
        supports = c.get("supports") or []
        if not supports:
            problems.append({"claim": cid, "problem": "claim without any support "
                             "(结论句必须回链到具体文献段落)"})
            rows.append({"claim": cid, "supports": 0, "ok": False})
            continue
        ok = True
        for j, s in enumerate(supports):
            sid = str(s.get("source_id") or "")
            q = (s.get("quote") or "").strip()
            loc = (s.get("locator") or "").strip()
            if sid not in sources:
                problems.append({"claim": cid, "support": j,
                                 "problem": f"unknown source_id '{sid}'"})
                ok = False
            if len(q) < MIN_QUOTE:
                problems.append({"claim": cid, "support": j,
                                 "problem": f"quote too short ({len(q)}<{MIN_QUOTE} chars); "
                                            "必须摘录原文片段"})
                ok = False
            if not loc:
                problems.append({"claim": cid, "support": j,
                                 "problem": "missing locator (页码/段落/行号)"})
                ok = False
        rows.append({"claim": cid, "supports": len(supports), "ok": ok})
    return {"ok": not problems, "claims": len(claims),
            "supported": sum(1 for r in rows if r["ok"]),
            "problems": problems, "per_claim": rows,
            "note": "引擎只校验结构；quote 是否真在原文中由 Agent 对照 extract 落盘文本逐条核对并记录"}


def suggest_conflict_pairs(matrix: dict) -> list[dict]:
    """Candidates: same subq_id, opposite polarity cues. Agent must confirm."""
    by_sub: dict[str, list[dict]] = {}
    for c in matrix.get("claims") or []:
        by_sub.setdefault(str(c.get("subq_id") or ""), []).append(c)
    out = []
    for sub, cs in by_sub.items():
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                a, b = cs[i], cs[j]
                ta, tb = a.get("text") or "", b.get("text") or ""
                if (_has_cue(ta, _POS_CUES) and _has_cue(tb, _NEG_CUES)) or \
                   (_has_cue(ta, _NEG_CUES) and _has_cue(tb, _POS_CUES)):
                    out.append({"claim_a": a.get("id"), "claim_b": b.get("id"),
                                "subq_id": sub, "reason": "opposite polarity cues on same subquestion",
                                "status": "candidate_needs_agent_confirmation"})
    return out


VALID_RESOLUTIONS = {"a_stronger", "b_stronger", "both_bounded", "genuinely_unresolved"}


def validate_conflicts(matrix: dict) -> dict:
    claims = {str(c.get("id")) for c in matrix.get("claims") or []}
    problems, rows = [], []
    for k in matrix.get("conflicts") or []:
        kid = str(k.get("id"))
        a, b = str(k.get("claim_a")), str(k.get("claim_b"))
        if a not in claims or b not in claims:
            problems.append({"conflict": kid, "problem": f"unknown claim(s) {a},{b}"})
            continue
        if a == b:
            problems.append({"conflict": kid, "problem": "self-conflict"})
        adj = k.get("adjudication") or {}
        comp = (adj.get("comparison") or "").strip()
        res = str(adj.get("resolution") or "")
        basis = (adj.get("basis") or "").strip()
        # the cop-out detector: unresolved is allowed ONLY with a real comparison
        if len(comp) < 20:
            problems.append({"conflict": kid,
                             "problem": "adjudication.comparison missing or too thin; "
                                        "必须逐条比较双方证据（样本/方法/条件），不得只写'尚存争议'"})
        if res not in VALID_RESOLUTIONS:
            problems.append({"conflict": kid,
                             "problem": f"resolution must be one of {sorted(VALID_RESOLUTIONS)}"})
        if res == "genuinely_unresolved" and len(basis) < 20:
            problems.append({"conflict": kid,
                             "problem": "genuinely_unresolved requires basis explaining why "
                                        "the evidence comparison cannot decide"})
        rows.append({"conflict": kid, "claims": [a, b], "resolution": res,
                     "comparison_chars": len(comp)})
    return {"ok": not problems, "conflicts": len(rows), "problems": problems, "per_conflict": rows}


def coverage_by_subq(matrix: dict, plan: dict) -> dict:
    by_sub: dict[str, int] = {}
    for c in matrix.get("claims") or []:
        by_sub[str(c.get("subq_id") or "")] = by_sub.get(str(c.get("subq_id") or ""), 0) + 1
    rows = [{"subq_id": str(s.get("id")), "claims": by_sub.get(str(s.get("id")), 0),
             "covered": by_sub.get(str(s.get("id")), 0) > 0}
            for s in plan.get("subquestions") or []]
    return {"per_subquestion": rows,
            "uncovered": [r["subq_id"] for r in rows if not r["covered"]]}


def _demo() -> int:
    matrix = {
        "sources": [{"id": "S1", "title": "Paper A"}, {"id": "S2", "title": "Paper B"}],
        "claims": [
            {"id": "C1", "text": "X 显著提高 Y", "subq_id": "Q1",
             "supports": [{"source_id": "S1", "quote": "X increased Y by 40% (p<0.01)",
                           "locator": "p.3 table 2"}]},
            {"id": "C2", "text": "X 对 Y 无效", "subq_id": "Q1",
             "supports": [{"source_id": "S2", "quote": "no effect of X on Y was observed",
                           "locator": "p.5 ¶1"}]}],
        "conflicts": [{"id": "K1", "claim_a": "C1", "claim_b": "C2", "topic": "X->Y",
                       "adjudication": {"comparison": "S1 用体内模型 n=120；S2 为体外细胞系，"
                                        "剂量低一个数量级，结论适用范围不同",
                                        "resolution": "both_bounded",
                                        "basis": "模型体系不同"}}]}
    v = validate_matrix(matrix)
    assert v["ok"] and v["supported"] == 2
    sug = suggest_conflict_pairs(matrix)
    assert len(sug) == 1 and sug[0]["claim_a"] == "C1"
    cf = validate_conflicts(matrix)
    assert cf["ok"]
    # negative: unsupported claim must be rejected
    bad = {"sources": matrix["sources"],
           "claims": [{"id": "C9", "text": "无来源断言", "supports": []}]}
    assert not validate_matrix(bad)["ok"]
    # negative: cop-out adjudication must be rejected
    cop = {"sources": matrix["sources"], "claims": matrix["claims"],
           "conflicts": [{"id": "K2", "claim_a": "C1", "claim_b": "C2",
                          "adjudication": {"comparison": "尚存争议",
                                           "resolution": "genuinely_unresolved", "basis": ""}}]}
    assert not validate_conflicts(cop)["ok"]
    plan = {"subquestions": [{"id": "Q1"}, {"id": "Q2"}]}
    cov = coverage_by_subq(matrix, plan)
    assert cov["uncovered"] == ["Q2"]
    print(json.dumps({"demo": "evidence", "claims_ok": f"{v['supported']}/{v['claims']}",
                      "conflict_candidates": len(sug), "copout_rejected": True,
                      "uncovered_subq": cov["uncovered"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    matrix = json.load(open(sys.argv[2], encoding="utf-8"))
    if cmd == "validate":
        rep = validate_matrix(matrix)
    elif cmd == "conflicts":
        rep = validate_conflicts(matrix)
    elif cmd == "suggest":
        rep = {"candidates": suggest_conflict_pairs(matrix)}
    elif cmd == "coverage":
        plan = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = coverage_by_subq(matrix, plan)
    else:
        print("usage: evidence.py [validate|conflicts|suggest|coverage] matrix.json out.json [plan.json]")
        sys.exit(2)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": rep.get("ok", True), "->": sys.argv[3]}, ensure_ascii=False))
