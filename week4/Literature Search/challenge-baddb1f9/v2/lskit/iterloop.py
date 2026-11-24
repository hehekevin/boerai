"""Iteration ledger for search agents: every round logged, every decision
tied to a signal, rollback to any round, explicit stop criteria.

Ledger: {"rounds": [{"n", "action": query|screen|merge|supplement,
          "params": {...}, "returned": int, "new_items": int, "kept": int,
          "signal": "why continue/switch/stop", "decision": "continue|switch|stop|handoff"}]}
The engine computes the stop signals; the agent decides and records why.
A round with no recorded signal is a protocol violation and is flagged.
"""
from __future__ import annotations

import json
import sys


def signals(ledger: dict, target_refs: int | None = None, budget: int | None = None) -> dict:
    rounds = ledger.get("rounds", [])
    out = {"rounds": len(rounds), "violations": [], "marginal_gains": [],
           "coverage": None, "budget_used": None}
    total_new = 0
    for i, r in enumerate(rounds):
        if not r.get("signal"):
            out["violations"].append({"round": r.get("n", i + 1),
                                      "problem": "round without recorded signal"})
        if r.get("decision") not in ("continue", "switch", "stop", "handoff"):
            out["violations"].append({"round": r.get("n", i + 1),
                                      "problem": f"invalid decision '{r.get('decision')}'"})
        total_new += int(r.get("new_items") or 0)
        out["marginal_gains"].append(int(r.get("new_items") or 0))
    if target_refs:
        covered = ledger.get("covered_ref_ids") or []
        out["coverage"] = round(len(covered) / target_refs, 4)
    if budget:
        out["budget_used"] = round(len(rounds) / budget, 4)
    return out


def should_stop(ledger: dict, k: int = 2, min_gain: int = 1, budget: int | None = None) -> dict:
    rounds = ledger.get("rounds", [])
    reasons = []
    recent = [int(r.get("new_items") or 0) for r in rounds[-k:]]
    if len(recent) == k and all(g < min_gain for g in recent):
        reasons.append(f"marginal_gain_below_{min_gain}_for_{k}_rounds")
    if budget and len(rounds) >= budget:
        reasons.append("budget_exhausted")
    if ledger.get("target_refs") and set(ledger.get("covered_ref_ids") or []) >= set(ledger.get("target_ref_ids") or []):
        reasons.append("target_coverage_complete")
    return {"stop": bool(reasons), "reasons": reasons,
            "note": "stop must be recorded as a round with decision='stop' and the triggering signal"}


def rollback(ledger: dict, to_round: int) -> dict:
    rounds = ledger.get("rounds", [])
    if to_round < 1 or to_round > len(rounds):
        return {"ok": False, "error": f"round {to_round} out of range 1..{len(rounds)}"}
    kept = rounds[:to_round]
    return {"ok": True, "restored_rounds": len(kept),
            "dropped": [r.get("n") for r in rounds[to_round:]],
            "state": {"rounds": kept,
                      "covered_ref_ids": ledger.get("covered_ref_ids", [])},
            "note": "rollback drops later rounds but keeps their records in history; re-run must reference this rollback"}


def _demo() -> int:
    led = {"rounds": [
        {"n": 1, "action": "query", "params": {"q": "crispr t cell"}, "returned": 40, "new_items": 40,
         "kept": 40, "signal": "initial query, broad", "decision": "continue"},
        {"n": 2, "action": "query", "params": {"q": "crispr AND 'T cell' AND screen"}, "returned": 12,
         "new_items": 5, "kept": 45, "signal": "narrowed; +5 new", "decision": "continue"},
        {"n": 3, "action": "query", "params": {"q": "synonyms"}, "returned": 9, "new_items": 0,
         "kept": 45, "signal": "no new items; saturation suspected", "decision": "continue"},
        {"n": 4, "action": "query", "params": {"q": "another variant"}, "returned": 6, "new_items": 0,
         "kept": 45, "signal": "second zero-gain round -> stop", "decision": "stop"}],
        "target_refs": 10, "covered_ref_ids": ["R1", "R2", "R3"]}
    sig = signals(led, target_refs=10, budget=20)
    assert not sig["violations"] and sig["coverage"] == 0.3
    st = should_stop(led, k=2, min_gain=1)
    assert st["stop"] and "marginal_gain_below_1_for_2_rounds" in st["reasons"]
    rb = rollback(led, 2)
    assert rb["ok"] and rb["restored_rounds"] == 2 and rb["dropped"] == [3, 4]
    print(json.dumps({"demo": "iterloop", "violations": len(sig["violations"]),
                      "coverage": sig["coverage"], "stop_reasons": st["reasons"],
                      "rollback_to_2": rb["restored_rounds"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd, path = sys.argv[1], sys.argv[2]
    led = json.load(open(path, encoding="utf-8"))
    if cmd == "signals":
        rep = signals(led)
    elif cmd == "stop":
        rep = should_stop(led)
    elif cmd == "rollback":
        rep = rollback(led, int(sys.argv[4]))
    else:
        print("usage: iterloop.py [signals|stop|rollback] ledger.json [out.json] [to_round]")
        sys.exit(2)
    if len(sys.argv) > 3 and cmd != "rollback":
        json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False)[:400])
