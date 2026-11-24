#!/usr/bin/env python3
"""iterative-search-agent-forge: iteration ledger, stop-condition eval, rollback points.

Deterministic subcommands (0 model requests):
  --ledger QUERIES_TSV   build iteration ledger from executed-query log
                         (tsv: round<TAB>query<TAB>db<TAB>hits<TAB>cost_minutes)
  --stop LEDGER_JSON     evaluate 4 stop criteria (coverage/marginal-gain/budget/human)
  --rollback LEDGER_JSON mark rollback points where evidence is preserved
Stdlib only.
"""
import argparse, json, sys

def load_rows(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        while len(parts) < 5:
            parts.append("")
        rows.append({"round": int(parts[0] or 0), "query": parts[1], "db": parts[2],
                     "hits": int(parts[3] or 0), "cost": float(parts[4] or 0)})
    return rows

def build_ledger(rows, target_coverage=90.0, gain_threshold=0.05, budget_minutes=60.0):
    ledger = {"schema": "agent-loop/ledger@1", "rounds": [], "cumulative_unique": 0, "total_cost": 0.0}
    seen_sets = []
    cum = 0
    for r in rows:
        rd = int(r["round"])
        prev = [s for rr, s in seen_sets if rr < rd]
        prior_titles = set().union(*prev) if prev else set()
        new_hits = max(0, r["hits"] - 0)  # hits are raw; uniqueness approximated at round level
        cum += r["hits"] if rd == 1 or not prev else max(0, r["hits"] - len(prior_titles) if r["hits"] > len(prior_titles) else 0)
        ledger["total_cost"] += r["cost"]
        entry = {"round": rd, "query": r["query"], "db": r["db"], "hits_raw": r["hits"],
                 "cost_min": r["cost"], "cum_unique_est": cum}
        ledger["rounds"].append(entry)
    ledger["cumulative_unique"] = cum
    # marginal gain per round (new hits / cost), first round = baseline
    for i, e in enumerate(ledger["rounds"]):
        if i == 0:
            e["marginal_gain"] = None
        else:
            prev_e = ledger["rounds"][i-1]
            denom = e["cost_min"] or 0.01
            e["marginal_gain"] = round(max(0, e["hits_raw"] - prev_e["hits_raw"]) / denom, 3)
    return ledger

def eval_stop(ledger, cfg):
    rounds = ledger.get("rounds", [])
    last = rounds[-1] if rounds else {}
    total_cost = sum(r.get("cost_min", 0) for r in rounds)
    reasons = []
    gains = [r.get("marginal_gain") for r in rounds[1:] if r.get("marginal_gain") is not None]
    if gains and gains[-1] < cfg["gain_threshold"]:
        reasons.append({"type": "marginal_gain", "detail": f"最后轮边际收益 {gains[-1]} < 阈值 {cfg['gain_threshold']}，补检收益趋零"})
    if total_cost >= cfg["budget_minutes"]:
        reasons.append({"type": "budget", "detail": f"累计耗时 {total_cost} 分钟 >= 预算 {cfg['budget_minutes']}"})
    cov_est = min(100.0, ledger.get("cumulative_unique", 0) / max(1, cfg["expected_corpus"]) * 100)
    if cov_est >= cfg["target_coverage"]:
        reasons.append({"type": "coverage", "detail": f"估算覆盖 {cov_est:.1f}% >= 目标 {cfg['target_coverage']}%"})
    if len(rounds) >= cfg["max_rounds"]:
        reasons.append({"type": "max_rounds", "detail": f"已达最大轮次 {cfg['max_rounds']}"})
    human_points = [r for r in rounds if r.get("query", "").startswith("HUMAN:")]
    if human_points:
        reasons.append({"type": "human", "detail": f"台账含 {len(human_points)} 个人工介入点，需回写判断后继续"})
    return {"schema": "agent-loop/stop@1", "should_stop": bool(reasons and not human_points) or bool(reasons),
            "stop_reasons": reasons, "human_intervention_points": len(human_points),
            "total_cost_min": total_cost, "cum_unique_est": ledger.get("cumulative_unique", 0)}

def mark_rollback(ledger):
    """Rollback point = last round before 2 consecutive zero-gain rounds."""
    rounds = ledger.get("rounds", [])
    points = []
    for i in range(2, len(rounds)):
        g1, g2 = rounds[i-2].get("marginal_gain"), rounds[i-1].get("marginal_gain")
        if g1 is not None and g2 is not None and g1 == 0 and g2 == 0:
            points.append({"rollback_at_round": rounds[i-2]["round"],
                           "reason": "连续两轮边际收益为0",
                           "evidence_kept": f"rounds 1..{rounds[i-2]['round']} 的命中集与查询式全部保留"})
            break
    return {"schema": "agent-loop/rollback@1", "rollback_points": points or [{"rollback_at_round": None, "reason": "未触发回退条件"}]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", help="queries TSV")
    ap.add_argument("--stop", help="ledger JSON")
    ap.add_argument("--rollback", help="ledger JSON")
    ap.add_argument("--target-coverage", type=float, default=90.0)
    ap.add_argument("--gain-threshold", type=float, default=0.5)
    ap.add_argument("--budget-minutes", type=float, default=60.0)
    ap.add_argument("--max-rounds", type=int, default=8)
    ap.add_argument("--expected-corpus", type=int, default=200)
    a = ap.parse_args()
    cfg = {"target_coverage": a.target_coverage, "gain_threshold": a.gain_threshold,
           "budget_minutes": a.budget_minutes, "max_rounds": a.max_rounds,
           "expected_corpus": a.expected_corpus}
    if a.ledger:
        rows = load_rows(a.ledger)
        print(json.dumps(build_ledger(rows), ensure_ascii=False, indent=1))
        return 0
    if a.stop:
        ledger = json.load(open(a.stop, encoding="utf-8"))
        print(json.dumps(eval_stop(ledger, cfg), ensure_ascii=False, indent=1))
        return 0
    if a.rollback:
        ledger = json.load(open(a.rollback, encoding="utf-8"))
        print(json.dumps(mark_rollback(ledger), ensure_ascii=False, indent=1))
        return 0
    ap.error("choose --ledger / --stop / --rollback")

if __name__ == "__main__":
    sys.exit(main())
