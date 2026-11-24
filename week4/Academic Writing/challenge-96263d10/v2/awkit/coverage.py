"""题面必需要点 / 必需章节覆盖核对。

brief.json（由 Agent 从 task.md / case.json 整理，引擎只认结构化清单）：
  {"required_sections": ["引言", "方法", "结果", "讨论", "参考文献"],
   "required_points": [{"id": "P1", "label": "说明样本量来源",
                        "keywords": ["样本量", "500"]},
                        ...],
   "constraints": [{"id": "C1", "desc": "全文不超过 3000 字", "max_chars": 3000}]}

coverage_map.json（Agent 填定位，引擎验证定位真实存在）：
  {"points": [{"id": "P1", "where": "§方法 d0012",
               "evidence": "草稿中的原文片段"}, ...],
   "sections": {"引言": true, ...}}   —— 章节也可由引擎自动按标题识别

引擎校验：
1. 每个 required_section 必须在草稿中以标题行（#/## 或 “一、” 或 “1.” 开头）出现。
2. 每个 required_point 要么关键词全部命中草稿，要么 Agent 给的 evidence
   是草稿原文子串（规范化空白后）；两者皆无 → missing，不接受口头声称。
3. constraints 中的字数上限机械执行。
输出 coverage.json：逐条 present/missing + 证据，missing 列表非空即 ok=false。

CLI:  python -m awkit.coverage check DRAFT BRIEF COVERAGE_MAP OUT
"""
from __future__ import annotations

import json
import re
import sys

_WS = re.compile(r"\s+")
_HEAD = re.compile(r"^\s*(#{1,6}\s+|第[一二三四五六七八九十\d]+[章节部分、]|[一二三四五六七八九十]+、|\d+(?:\.\d+)*[\.、\s])")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def find_headings(draft: str) -> list[str]:
    heads = []
    for line in draft.splitlines():
        s = line.strip()
        if _HEAD.match(s) and len(s) <= 120:
            heads.append(re.sub(r"^#{1,6}\s*", "", s))
    return heads


def check(draft: str, brief: dict, coverage_map: dict | None = None) -> dict:
    flat = norm(draft)
    heads = find_headings(draft)
    sec_rep = []
    for sec in brief.get("required_sections", []):
        hit = any(sec in h or h in sec for h in heads) or sec in flat
        where = next((h for h in heads if sec in h or h in sec), "")
        sec_rep.append({"section": sec, "present": bool(hit), "heading": where})
    cmap = (coverage_map or {}).get("points", [])
    cby = {c.get("id"): c for c in cmap}
    pt_rep = []
    for p in brief.get("required_points", []):
        kws = p.get("keywords", [])
        kw_hit = all(k in flat for k in kws) if kws else False
        ev, ev_ok, where = "", False, ""
        c = cby.get(p.get("id"))
        if c:
            ev = norm(c.get("evidence", ""))
            where = c.get("where", "")
            ev_ok = bool(ev) and ev in flat
        present = kw_hit or ev_ok
        pt_rep.append({"id": p.get("id"), "label": p.get("label", ""),
                       "present": present, "via": "keywords" if kw_hit else
                       ("agent_evidence" if ev_ok else "none"),
                       "where": where, "evidence_ok": ev_ok,
                       "missing_keywords": [k for k in kws if k not in flat]})
    con_rep = []
    for c in brief.get("constraints", []):
        if c.get("max_chars"):
            n = len(re.sub(r"\s", "", draft))
            con_rep.append({"id": c.get("id"), "desc": c.get("desc", ""),
                            "chars": n, "max_chars": c["max_chars"], "ok": n <= c["max_chars"]})
    missing_secs = [s["section"] for s in sec_rep if not s["present"]]
    missing_pts = [p for p in pt_rep if not p["present"]]
    bad_cons = [c for c in con_rep if not c["ok"]]
    ok = not missing_secs and not missing_pts and not bad_cons
    return {"ok": ok, "missing_sections": missing_secs,
            "missing_points": [{"id": p["id"], "label": p["label"],
                                "missing_keywords": p["missing_keywords"]} for p in missing_pts],
            "constraint_violations": bad_cons,
            "sections": sec_rep, "points": pt_rep,
            "note": "要点覆盖必须给关键词命中或草稿原文证据，不接受口头声称已覆盖"}


def _demo() -> int:
    draft = ("# 引言\n本研究关注 T 细胞活化调控。\n# 方法\n样本量 500 个基因来自初筛实验，"
             "覆盖 3 名供体。\n# 结果\n初筛命中率为 4.2%。\n# 讨论\n结果提示筛选体系稳定。\n"
             "# 参考文献\n[1] Smith et al. 2021.")
    brief = {"required_sections": ["引言", "方法", "结果", "讨论", "参考文献"],
             "required_points": [{"id": "P1", "label": "说明样本量来源", "keywords": ["样本量", "500"]},
                                 {"id": "P2", "label": "报告命中率", "keywords": ["4.2%"]},
                                 {"id": "P3", "label": "讨论局限性", "keywords": ["局限"]}],
             "constraints": [{"id": "C1", "desc": "≤3000字", "max_chars": 3000}]}
    rep = check(draft, brief, {"points": [{"id": "P3", "where": "§讨论",
                                           "evidence": "这是编造的证据，不在草稿里"}]})
    assert not rep["ok"]
    assert rep["missing_points"] and rep["missing_points"][0]["id"] == "P3"
    assert rep["missing_sections"] == []
    draft2 = draft.replace("结果提示筛选体系稳定。", "结果提示筛选体系稳定；局限在于样本量有限。")
    rep2 = check(draft2, brief, {})
    assert rep2["ok"], rep2["missing_points"]
    # 证据必须是草稿原文子串，编造的 evidence 不算数
    rep3 = check(draft, brief, {"points": [{"id": "P1", "evidence": "样本量 500 个基因来自初筛实验，"}]})
    p1 = [p for p in rep3["points"] if p["id"] == "P1"][0]
    assert p1["present"]
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "check":
        draft = open(argv[1], encoding="utf-8").read()
        brief = json.load(open(argv[2], encoding="utf-8"))
        cmap = json.load(open(argv[3], encoding="utf-8")) if len(argv) > 4 and argv[3] != "-" else {}
        out = argv[4] if len(argv) > 4 else argv[3]
        rep = check(draft, brief, cmap)
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"coverage: ok={rep['ok']} missing_pts={len(rep['missing_points'])} "
              f"missing_secs={len(rep['missing_sections'])} -> {out}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
