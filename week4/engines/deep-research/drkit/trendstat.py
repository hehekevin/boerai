"""Trend statistics for research-frontier / trend analysis (challenge-073af7d3).

Deterministic bookkeeping over a frozen record set:
  - yearly output distribution (with explicit missing-year records listed,
    never silently dropped)
  - per-topic per-year counts so 主题出现/合并/衰退 can be read from numbers
  - change-point *signals*: a year whose count >= factor x the mean of the
    previous window; flagged as signal, the agent must still argue the cause
  - trend-claim audit: every trend/evolution claim must reference computed
    stat rows (years or topics that actually exist in the stats) -- a claim
    about a year with zero records is rejected

Records: [{"id": "R1", "year": 2019, "topics": ["crispr", "screen"], ...}]
Claims:  [{"id": "T1", "text": "...", "kind": "trend|evolution|representative|gap",
           "stat_refs": {"years": [2020, 2021], "topics": ["crispr"]}}]
"""
from __future__ import annotations

import json
import sys

VALID_KINDS = {"trend", "evolution", "representative", "gap"}


def yearly_distribution(records: list[dict], year_field: str = "year") -> dict:
    counts: dict[int, int] = {}
    missing = []
    for r in records:
        y = r.get(year_field)
        try:
            y = int(y)
        except (TypeError, ValueError):
            missing.append(r.get("id"))
            continue
        counts[y] = counts.get(y, 0) + 1
    years = sorted(counts)
    series = [{"year": y, "count": counts[y]} for y in years]
    return {"n_records": len(records), "with_year": sum(counts.values()),
            "missing_year_ids": missing, "span": [years[0], years[-1]] if years else None,
            "series": series,
            "denominator_note": "分母=冻结记录集；年份口径(在线发表/见刊/预印本)须在报告注明"}


def topic_yearly(records: list[dict], topic_field: str = "topics",
                 year_field: str = "year") -> dict:
    per: dict[str, dict[int, int]] = {}
    for r in records:
        try:
            y = int(r.get(year_field))
        except (TypeError, ValueError):
            continue
        for t in r.get(topic_field) or []:
            t = str(t).strip()
            if not t:
                continue
            per.setdefault(t, {})
            per[t][y] = per[t].get(y, 0) + 1
    topics = {t: {"total": sum(ys.values()),
                  "first_year": min(ys), "last_year": max(ys),
                  "series": [{"year": y, "count": ys[y]} for y in sorted(ys)]}
              for t, ys in sorted(per.items(), key=lambda kv: -sum(kv[1].values()))}
    return {"n_topics": len(topics), "topics": topics,
            "note": "主题归并/术语漂移映射由 Agent 提供 synonyms 表后重跑；引擎不做语义归并"}


def change_point_signals(yearly: dict, window: int = 3, factor: float = 2.0) -> dict:
    series = yearly.get("series") or []
    signals = []
    for i in range(len(series)):
        prev = [s["count"] for s in series[max(0, i - window):i]]
        if len(prev) < window:
            continue
        mean_prev = sum(prev) / len(prev)
        if mean_prev > 0 and series[i]["count"] >= factor * mean_prev:
            signals.append({"year": series[i]["year"], "count": series[i]["count"],
                            "prev_mean": round(mean_prev, 2), "factor": factor,
                            "status": "signal_not_proof",
                            "note": "统计信号；是否真实拐点须由 Agent 结合文献内容论证"})
    return {"window": window, "factor": factor, "signals": signals,
            "note": "离散波动与真实拐点的区分是语义判断，引擎只给可复算的信号"}


def audit_trend_claims(claims: list[dict], yearly: dict, topics: dict) -> dict:
    years_with_data = {s["year"] for s in yearly.get("series") or []}
    known_topics = set((topics.get("topics") or {}).keys())
    problems, rows = [], []
    for c in claims:
        cid = str(c.get("id"))
        kind = str(c.get("kind") or "")
        refs = c.get("stat_refs") or {}
        ry = [int(y) for y in (refs.get("years") or [])]
        rt = [str(t) for t in (refs.get("topics") or [])]
        if kind not in VALID_KINDS:
            problems.append({"claim": cid, "problem": f"kind must be one of {sorted(VALID_KINDS)}"})
        if kind in ("trend", "evolution") and not (ry or rt):
            problems.append({"claim": cid,
                             "problem": "trend/evolution claim without stat_refs; 趋势判断必须"
                                        "回指可核对的年度/主题统计行"})
        phantom_years = [y for y in ry if y not in years_with_data]
        if phantom_years:
            problems.append({"claim": cid,
                             "problem": f"years with zero records in the frozen set: "
                                        f"{phantom_years}; 不得对无记录年份作趋势断言"})
        phantom_topics = [t for t in rt if t not in known_topics]
        if phantom_topics:
            problems.append({"claim": cid,
                             "problem": f"topics absent from stats: {phantom_topics}"})
        rows.append({"claim": cid, "kind": kind, "years": ry, "topics": rt,
                     "ok": not any(p["claim"] == cid for p in problems)})
    return {"ok": not problems, "claims": len(rows), "problems": problems, "per_claim": rows}


def _demo() -> int:
    recs = [{"id": f"R{i}", "year": y, "topics": t} for i, (y, t) in enumerate([
        (2018, ["a"]), (2018, ["a"]), (2019, ["a"]), (2019, ["b"]),
        (2020, ["a", "b"]), (2020, ["b"]), (2020, ["b"]), (2020, ["b"]),
        (2020, ["a"]), (2020, ["b"]), (2021, ["b"]), (None, ["a"])])]
    yd = yearly_distribution(recs)
    assert yd["n_records"] == 12 and yd["with_year"] == 11 and yd["missing_year_ids"] == ["R11"]
    assert yd["span"] == [2018, 2021]
    ty = topic_yearly(recs)
    assert ty["topics"]["b"]["total"] == 7 and ty["topics"]["b"]["first_year"] == 2019
    sig = change_point_signals(yd, window=2, factor=2.0)
    assert any(s["year"] == 2020 for s in sig["signals"])
    claims = [{"id": "T1", "text": "2020 年产出抬升", "kind": "trend",
               "stat_refs": {"years": [2019, 2020]}},
              {"id": "T2", "text": "主题 b 2019 年出现后扩张", "kind": "evolution",
               "stat_refs": {"topics": ["b"]}}]
    rep = audit_trend_claims(claims, yd, ty)
    assert rep["ok"], rep["problems"]
    # negative: trend claim on a phantom year must be rejected
    bad = [{"id": "T9", "text": "2025 年爆发", "kind": "trend", "stat_refs": {"years": [2025]}}]
    assert not audit_trend_claims(bad, yd, ty)["ok"]
    # negative: trend claim with no stat refs at all
    bad2 = [{"id": "T8", "text": "持续增长", "kind": "trend", "stat_refs": {}}]
    assert not audit_trend_claims(bad2, yd, ty)["ok"]
    print(json.dumps({"demo": "trendstat", "span": yd["span"], "topics": ty["n_topics"],
                      "signals": [s["year"] for s in sig["signals"]],
                      "phantom_year_rejected": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "yearly":
        recs = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = yearly_distribution(recs.get("records", recs))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd == "topics":
        recs = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = topic_yearly(recs.get("records", recs))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd == "signals":
        yd = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = change_point_signals(yd)
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd == "audit":
        claims = json.load(open(sys.argv[2], encoding="utf-8"))
        yd = json.load(open(sys.argv[3], encoding="utf-8"))
        ty = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = audit_trend_claims(claims.get("claims", claims), yd, ty)
        out = sys.argv[5] if len(sys.argv) > 5 else None
    else:
        print("usage: trendstat.py [yearly|topics|signals|audit] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False)[:500])
