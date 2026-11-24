"""评测簿记：评分锚点=可观察现象、0/1/2 逐条评分+理由、双评一致性与报告。

anchors.json（锚点必须写成可观察现象，引擎拒绝空泛锚点）：
  {"version": "v1.0",
   "anchors": [{"id": "A1", "criterion": "事实与引用一致",
                "observable": "随机抽 5 个数字，逐一对照来源文本",
                "levels": {"0": "≥2 处不一致", "1": "1 处不一致",
                           "2": "全部一致"}}]}

ratings.json（每名评分员独立评分，双评；理由与证据必填）：
  [{"case_id": "case1", "anchor_id": "A1", "rater": "R1",
    "score": 2, "rationale": "抽 5 个数字全部在来源中找到",
    "evidence": "claims_report.json"}]

引擎保证：
1. 锚点规范性：observable 必填且 ≥10 字、含可检查动作词；levels 必须
   恰好覆盖 0/1/2 三档——空泛锚点（如“写得好”）直接拒收。
2. 评分合法性：score ∈ {0,1,2}；rationale ≥10 字；evidence 引用必填；
   anchor_id 必须存在；同一 (case,anchor,rater) 不得重复评分。
3. 一致性：逐 (case,anchor) 对齐两名评分员；exact agreement 率、
   分歧 >1 档 → adjudication_required；分歧必须产出裁定记录
   （final score + rationale），且只能修订锚点、不得直接改分
   （anchor_revision 字段记录建议）。
4. 报告：逐 case × anchor 给分数、理由、失败类型、改进建议位；
   汇总到 report.md / report.json，分数全部可从 ratings 复算。

CLI:
  python -m awkit.scorecard lint-anchors ANCHORS OUT
  python -m awkit.scorecard score ANCHORS RATINGS OUT
  python -m awkit.scorecard agree ANCHORS RATINGS OUT_JSON OUT_MD
"""
from __future__ import annotations

import json
import re
import sys

_ACTION = re.compile(r"对照|抽取|检查|核对|计数|比对|定位|复算|检查项|是否|有无|能否|逐条|随机|测量|验证")


def lint_anchors(anchors_doc: dict) -> dict:
    violations = []
    seen = set()
    for a in anchors_doc.get("anchors", []):
        aid = a.get("id")
        if aid in seen:
            violations.append({"anchor": aid, "type": "duplicate_anchor_id"})
        seen.add(aid)
        obs = a.get("observable", "")
        if len(obs) < 10 or not _ACTION.search(obs):
            violations.append({"anchor": aid, "type": "anchor_not_observable",
                               "note": "锚点必须写成可观察现象（含可检查动作，≥10字）",
                               "observable": obs})
        levels = a.get("levels", {})
        if set(str(k) for k in levels) != {"0", "1", "2"}:
            violations.append({"anchor": aid, "type": "levels_not_012"})
        else:
            for lv in ("0", "1", "2"):
                if len(str(levels[lv])) < 4:
                    violations.append({"anchor": aid, "type": "level_desc_too_vague",
                                       "level": lv})
    return {"ok": not violations, "n_anchors": len(seen), "violations": violations,
            "version": anchors_doc.get("version", "")}


def validate_ratings(anchors_doc: dict, ratings: list[dict]) -> dict:
    ids = {a.get("id") for a in anchors_doc.get("anchors", [])}
    violations, seen = [], set()
    for r in ratings:
        key = (r.get("case_id"), r.get("anchor_id"), r.get("rater"))
        if key in seen:
            violations.append({"type": "duplicate_rating", "key": list(map(str, key))})
        seen.add(key)
        if r.get("anchor_id") not in ids:
            violations.append({"type": "unknown_anchor", "anchor_id": r.get("anchor_id")})
        if r.get("score") not in (0, 1, 2):
            violations.append({"type": "score_out_of_range", "key": list(map(str, key)),
                               "score": r.get("score")})
        if len(r.get("rationale", "")) < 10:
            violations.append({"type": "rationale_missing", "key": list(map(str, key))})
        if not r.get("evidence"):
            violations.append({"type": "evidence_ref_missing", "key": list(map(str, key))})
    return {"ok": not violations, "n_ratings": len(ratings), "violations": violations}


def agreement(anchors_doc: dict, ratings: list[dict],
              adjudications: list[dict] | None = None) -> dict:
    pairs: dict[tuple, dict] = {}
    for r in ratings:
        pairs.setdefault((r.get("case_id"), r.get("anchor_id")), {})[r.get("rater")] = r
    items, agree, disagree_big, pending = [], 0, 0, []
    adj = {(a.get("case_id"), a.get("anchor_id")): a for a in (adjudications or [])}
    for (case, anchor), by_rater in sorted(pairs.items()):
        if len(by_rater) < 2:
            pending.append({"case_id": case, "anchor_id": anchor,
                            "reason": "single_rater_only"})
            continue
        (r1, s1), (r2, s2) = sorted((k, v["score"]) for k, v in by_rater.items())
        gap = abs(s1 - s2)
        item = {"case_id": case, "anchor_id": anchor, "scores": {r1: s1, r2: s2},
                "gap": gap}
        if gap == 0:
            agree += 1
            item["final"] = s1
        else:
            if gap > 1:
                disagree_big += 1
                item["adjudication_required"] = True
            a = adj.get((case, anchor))
            if a and a.get("final") in (0, 1, 2) and len(a.get("rationale", "")) >= 10:
                item["final"] = a["final"]
                item["adjudicated"] = True
                item["anchor_revision"] = a.get("anchor_revision", "")
            else:
                item["final"] = None
                item["adjudication_required"] = True
                pending.append({"case_id": case, "anchor_id": anchor,
                                "reason": "disagreement_without_adjudication"})
        items.append(item)
    n = agree + sum(1 for it in items if it["gap"] > 0)
    rate = round(agree / n, 4) if n else None
    return {"ok": not pending, "pairs": len(items), "exact_agreement": agree,
            "exact_agreement_rate": rate, "large_disagreements": disagree_big,
            "items": items, "pending": pending,
            "rule": "分歧只修订锚点（anchor_revision），不直接改分；裁定须给 final+rationale"}


def build_report(anchors_doc: dict, ratings: list[dict], agree: dict,
                 failure_types: dict | None = None) -> str:
    """逐题报告：分数、理由、失败类型、改进建议。分数全部可复算。"""
    by_case: dict[str, list[dict]] = {}
    for it in agree.get("items", []):
        by_case.setdefault(str(it["case_id"]), []).append(it)
    anchors = {a["id"]: a for a in anchors_doc.get("anchors", [])}
    ft = failure_types or {}
    lines = ["# 评测报告（可复算：所有分数来自 ratings.json 双评 + 裁定记录）", ""]
    lines.append(f"- 锚点版本: {anchors_doc.get('version','?')}；"
                 f"评分对数: {agree['pairs']}；完全一致率: {agree['exact_agreement_rate']}")
    for case, items in sorted(by_case.items()):
        finals = [it["final"] for it in items if it.get("final") is not None]
        total = sum(finals)
        mx = 2 * len(items)
        lines.append(f"\n## {case}  得分 {total}/{mx}"
                     + ("（含未裁定项）" if len(finals) < len(items) else ""))
        for it in items:
            a = anchors.get(it["anchor_id"], {})
            tag = "裁定" if it.get("adjudicated") else "一致"
            lines.append(f"- [{it['anchor_id']}] {a.get('criterion','')}: "
                         f"{it['scores']} → final={it.get('final')}（{tag}）")
            if it["anchor_id"] in ft.get(case, {}):
                lines.append(f"  - 失败类型: {ft[case][it['anchor_id']].get('failure','')};"
                             f" 改进建议: {ft[case][it['anchor_id']].get('improvement','')}")
    lines.append("\n> 分歧处理规则：只修订锚点（anchor_revision），不直接改分；"
                 "差距>1档必须裁定。")
    return "\n".join(lines)


def _demo() -> int:
    anchors = {"version": "v1.0", "anchors": [
        {"id": "A1", "criterion": "事实与引用一致",
         "observable": "随机抽取 5 个数字，逐一对照来源文本是否字面一致",
         "levels": {"0": "2 处及以上不一致", "1": "恰好 1 处不一致", "2": "全部一致"}},
        {"id": "A2", "criterion": "必需要点覆盖",
         "observable": "对照题面必需要点清单逐项核对是否在稿中出现",
         "levels": {"0": "缺 2 项及以上", "1": "缺 1 项", "2": "全部覆盖"}}]}
    la = lint_anchors(anchors)
    assert la["ok"], la["violations"]
    bad_anchor = lint_anchors({"anchors": [{"id": "X", "criterion": "质量",
                                            "observable": "写得好",
                                            "levels": {"0": "差", "2": "好"}}]})
    assert not bad_anchor["ok"]
    ratings = [
        {"case_id": "c1", "anchor_id": "A1", "rater": "R1", "score": 2,
         "rationale": "抽 5 个数字全部命中来源", "evidence": "claims.json"},
        {"case_id": "c1", "anchor_id": "A1", "rater": "R2", "score": 1,
         "rationale": "5 个数字中 1 个找不到来源", "evidence": "claims.json"},
        {"case_id": "c1", "anchor_id": "A2", "rater": "R1", "score": 2,
         "rationale": "要点清单 6/6 覆盖", "evidence": "coverage.json"},
        {"case_id": "c1", "anchor_id": "A2", "rater": "R2", "score": 2,
         "rationale": "要点清单 6/6 覆盖", "evidence": "coverage.json"},
    ]
    vr = validate_ratings(anchors, ratings)
    assert vr["ok"], vr["violations"]
    ag = agreement(anchors, ratings)
    assert not ag["ok"]  # A1 分歧未裁定
    assert ag["exact_agreement"] == 1
    adj = [{"case_id": "c1", "anchor_id": "A1", "final": 1,
            "rationale": "复核确认 1 个数字取整后不再字面一致，按可观察现象判 1 档",
            "anchor_revision": "A1 锚点补充：取整改写视同不一致"}]
    ag2 = agreement(anchors, ratings, adj)
    assert ag2["ok"], ag2["pending"]
    md = build_report(anchors, ratings, ag2,
                      {"c1": {"A1": {"failure": "数字取整漂移",
                                     "improvement": "强制 claims 数字校验通过后再交稿"}}})
    assert "c1" in md and "3/4" in md and "失败类型" in md
    # 非法评分被拒
    vr2 = validate_ratings(anchors, ratings + [
        {"case_id": "c1", "anchor_id": "A1", "rater": "R3", "score": 5,
         "rationale": "x", "evidence": ""}])
    kinds = {v["type"] for v in vr2["violations"]}
    assert "score_out_of_range" in kinds and "rationale_missing" in kinds
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "lint-anchors":
        rep = lint_anchors(json.load(open(argv[1], encoding="utf-8")))
        json.dump(rep, open(argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"lint-anchors: ok={rep['ok']} n={rep['n_anchors']} -> {argv[2]}")
        return 0 if rep["ok"] else 1
    if argv and argv[0] == "score":
        anchors = json.load(open(argv[1], encoding="utf-8"))
        ratings = json.load(open(argv[2], encoding="utf-8"))
        rep = validate_ratings(anchors, ratings)
        json.dump(rep, open(argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"score validate: ok={rep['ok']} ratings={rep['n_ratings']} -> {argv[3]}")
        return 0 if rep["ok"] else 1
    if argv and argv[0] == "agree":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.scorecard agree")
        ap.add_argument("anchors"); ap.add_argument("ratings")
        ap.add_argument("out_json"); ap.add_argument("out_md")
        ap.add_argument("--adjudications", default="")
        a = ap.parse_args(argv[1:])
        anchors = json.load(open(a.anchors, encoding="utf-8"))
        ratings = json.load(open(a.ratings, encoding="utf-8"))
        adj = json.load(open(a.adjudications, encoding="utf-8")) if a.adjudications else []
        ag = agreement(anchors, ratings, adj)
        json.dump(ag, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        md = build_report(anchors, ratings, ag)
        open(a.out_md, "w", encoding="utf-8").write(md)
        print(f"agree: pairs={ag['pairs']} exact={ag['exact_agreement_rate']} "
              f"pending={len(ag['pending'])} -> {a.out_json}, {a.out_md}")
        return 0 if ag["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
