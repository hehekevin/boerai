"""Reading-benchmark tooling: 判得动、跑得一致、查得回、改得动。

题卡（itemset.json）：{version, items: [{item_id, qtype, task, materials,
  reference, rubric: {score_points: {0: ..., 1: ..., 2: ...}}, difficulty?}]}
运行输出（runs/<run_id>/）：raw output + run config（工具权限、预算、快照哈希）
评分（scores.json）：[{item_id, run_id, score: 0|1|2, rationale, scorer,
  dispute?}]

引擎职责：
  - 题卡完整性：缺 task/reference/rubric 的题判"判不动"，阻止进入评测
  - 评分校验：分数必须 0/1/2 且带 rationale；争议登记 dispute
  - 汇总：按题型×Agent×题集版本聚合，不只给总分
  - 复跑一致性：同输入同配置的重复运行分数波动必须被记录和解释
  - 失败归因：失败样例归到具体 qtype，可导出为下一版专项题
"""
from __future__ import annotations

import hashlib
import json
import sys

SCORES = (0, 1, 2)


def snapshot_hash(itemset: dict) -> str:
    return hashlib.sha256(json.dumps(itemset, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()[:16]


def validate_itemset(itemset: dict) -> dict:
    problems, unusable = [], []
    items = itemset.get("items") or []
    ids = set()
    for it in items:
        iid = it.get("item_id", "?")
        if iid in ids:
            problems.append(f"duplicate item_id {iid}")
        ids.add(iid)
        miss = [k for k in ("task", "reference", "rubric") if not it.get(k)]
        if miss:
            unusable.append({"item_id": iid, "missing": miss})
        if it.get("rubric") and not (it["rubric"].get("score_points") or {}):
            unusable.append({"item_id": iid, "missing": ["rubric.score_points"]})
    return {"n_items": len(items), "unusable": unusable, "problems": problems,
            "version": itemset.get("version", "?"), "snapshot": snapshot_hash(itemset),
            "ok": not problems and not unusable,
            "rule": "缺 task/reference/rubric 的题判不动，阻止进入评测而不是给同情分"}


def validate_scores(itemset: dict, scores: list[dict]) -> dict:
    ids = {it["item_id"] for it in itemset.get("items", [])}
    problems, out = [], []
    for s in scores:
        iid = s.get("item_id", "?")
        if iid not in ids:
            problems.append(f"{iid}: score for unknown item")
            continue
        if s.get("score") not in SCORES:
            problems.append(f"{iid}: score must be 0/1/2, got {s.get('score')!r}")
        if not (s.get("rationale") or "").strip():
            problems.append(f"{iid}: score without rationale")
        if not s.get("run_id"):
            problems.append(f"{iid}: score without run_id (无法回溯运行配置)")
        out.append(s)
    return {"scores": out, "problems": problems, "ok": not problems,
            "rule": "每个分数带 rationale + run_id，可追到原始输出与运行配置"}


def aggregate(itemset: dict, scores: list[dict]) -> dict:
    qtype = {it["item_id"]: it.get("qtype", "unknown") for it in itemset.get("items", [])}
    by_type, by_run = {}, {}
    for s in scores:
        t = qtype.get(s["item_id"], "unknown")
        by_type.setdefault(t, []).append(s["score"])
        by_run.setdefault(s.get("run_id", "?"), []).append(s["score"])
    def agg(v):
        return {"n": len(v), "total": sum(v), "mean": round(sum(v) / len(v), 4),
                "dist": {str(k): v.count(k) for k in SCORES}} if v else {"n": 0}
    return {"by_qtype": {t: agg(v) for t, v in sorted(by_type.items())},
            "by_run": {r: agg(v) for r, v in sorted(by_run.items())},
            "overall": agg([s["score"] for s in scores]),
            "snapshot": snapshot_hash(itemset),
            "note": "按题型与运行聚合；优势、短板、分布可见，不只是一个总分"}


def consistency_check(runs: list[dict]) -> dict:
    """runs: [{run_id, config_hash, scores: {item_id: score}}]
    同 config_hash 的多次运行分数不一致 → 波动必须登记解释。"""
    by_cfg = {}
    for r in runs:
        by_cfg.setdefault(r.get("config_hash", "?"), []).append(r)
    flucts = []
    for cfg, rs in by_cfg.items():
        if len(rs) < 2:
            continue
        items = set()
        for r in rs:
            items |= set((r.get("scores") or {}).keys())
        for iid in sorted(items):
            vals = {r["run_id"]: (r.get("scores") or {}).get(iid) for r in rs}
            if len({v for v in vals.values() if v is not None}) > 1:
                flucts.append({"item_id": iid, "config_hash": cfg,
                               "scores_by_run": vals,
                               "action": "须人工复核并解释波动，禁止只报平均分"})
    return {"fluctuations": flucts, "ok": not flucts,
            "rule": "重复运行分数波动必须被记录和解释，不得静默平均"}


def failure_attribution(itemset: dict, scores: list[dict],
                        notes: dict | None = None) -> dict:
    """score==0 的题归到 qtype，生成下一版专项题清单。"""
    qtype = {it["item_id"]: it.get("qtype", "unknown") for it in itemset.get("items", [])}
    task = {it["item_id"]: it.get("task", "") for it in itemset.get("items", [])}
    notes = notes or {}
    fails = [{"item_id": s["item_id"], "qtype": qtype.get(s["item_id"], "?"),
              "rationale": s.get("rationale", ""), "note": notes.get(s["item_id"], "")}
             for s in scores if s.get("score") == 0]
    by_type = {}
    for f in fails:
        by_type[f["qtype"]] = by_type.get(f["qtype"], 0) + 1
    next_items = [{"new_item_seed": f"{f['qtype']}-drill-{i + 1}",
                   "from_failure": f["item_id"],
                   "task_hint": (task.get(f["item_id"], "") or "")[:160]}
                  for i, f in enumerate(fails)]
    return {"failures": fails, "by_qtype": by_type,
            "next_version_items": next_items,
            "rule": "失败归到具体题型；只重算受影响题型的分数"}


def _demo() -> int:
    itemset = {"version": "v1", "items": [
        {"item_id": "Q1", "qtype": "extraction", "task": "抽取催化剂比表面积",
         "reference": "152 m2/g", "rubric": {"score_points": {0: "错", 1: "部分", 2: "全对"}}},
        {"item_id": "Q2", "qtype": "extraction", "task": "抽取煅烧温度",
         "reference": "500 C", "rubric": {"score_points": {0: "错", 1: "部分", 2: "全对"}}},
        {"item_id": "Q3", "qtype": "abstain", "task": "循环稳定性如何",
         "reference": "未报告，应拒答", "rubric": {"score_points": {0: "编造", 1: "含糊", 2: "正确拒答"}}},
    ]}
    vi = validate_itemset(itemset)
    assert vi["ok"] and vi["n_items"] == 3
    scores = [{"item_id": "Q1", "run_id": "run1", "score": 2, "rationale": "数值与单位一致"},
              {"item_id": "run1", "run_id": "run1", "score": 2, "rationale": "x"}]
    vs = validate_scores(itemset, scores)
    assert not vs["ok"]  # 未知 item 被抓
    scores = [s for s in scores if s["item_id"] in {"Q1", "Q2", "Q3"}] + [
        {"item_id": "Q2", "run_id": "run1", "score": 1, "rationale": "值对但单位缺失"},
        {"item_id": "Q3", "run_id": "run1", "score": 2, "rationale": "正确拒答并引用证据边界"}]
    ag = aggregate(itemset, scores)
    assert ag["overall"]["total"] == 5 and ag["by_qtype"]["extraction"]["n"] == 2
    runs = [{"run_id": "r1", "config_hash": "cfgA", "scores": {"Q1": 2, "Q2": 1}},
            {"run_id": "r2", "config_hash": "cfgA", "scores": {"Q1": 2, "Q2": 2}}]
    cc = consistency_check(runs)
    assert not cc["ok"] and cc["fluctuations"][0]["item_id"] == "Q2"
    fa = failure_attribution(itemset, scores + [{"item_id": "Q1", "run_id": "r9",
                                                 "score": 0, "rationale": "编造数值"}])
    assert fa["by_qtype"]["extraction"] == 1 and fa["next_version_items"]
    print(json.dumps({"demo": "bench", "itemset_ok": vi["ok"],
                      "overall": ag["overall"], "fluctuations": len(cc["fluctuations"]),
                      "drill_items": len(fa["next_version_items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    itemset = json.load(open(sys.argv[2], encoding="utf-8"))
    if cmd == "validate-itemset":
        rep = validate_itemset(itemset)
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd in ("validate-scores", "aggregate", "failures"):
        scores = json.load(open(sys.argv[3], encoding="utf-8"))
        scores = scores.get("scores", scores)
        rep = {"validate-scores": validate_scores, "aggregate": aggregate,
               "failures": failure_attribution}[cmd](itemset, scores)
        out = sys.argv[4] if len(sys.argv) > 4 else None
    elif cmd == "consistency":
        runs = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = consistency_check(runs.get("runs", runs))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        print("usage: bench.py [validate-itemset|validate-scores|aggregate|consistency|failures] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"-> {out}")
    print(f"ok={rep.get('ok', True)}")
    sys.exit(0 if rep.get("ok", True) else 1)
