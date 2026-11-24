"""Screening & ranking with auditable decisions (PRISMA-style counts).

The agent makes the semantic decisions; the engine guarantees:
  - every record gets exactly one decision with reason codes + evidence snippet
  - counts are recomputable (identified -> deduped -> screened -> included)
  - dual-screen conflicts are surfaced, never silently overwritten
  - ranking is stable and every rank position can be explained from the scores

Decisions file: [{record_id, decision: include|exclude|maybe, reasons:[...],
                  evidence: "verbatim snippet", screener: "agent|r1|r2"}]
"""
from __future__ import annotations

import json
import sys

VALID_DECISIONS = {"include", "exclude", "maybe"}


def validate_decisions(records: list[dict], decisions: list[dict]) -> dict:
    by_id = {r.get("id") or str(i): r for i, r in enumerate(records)}
    seen, problems, out = set(), [], []
    for d in decisions:
        rid = str(d.get("record_id"))
        if rid not in by_id:
            problems.append({"record_id": rid, "problem": "decision for unknown record"})
            continue
        if rid in seen:
            problems.append({"record_id": rid, "problem": "duplicate decision"})
            continue
        seen.add(rid)
        dec = str(d.get("decision", "")).lower()
        if dec not in VALID_DECISIONS:
            problems.append({"record_id": rid, "problem": f"invalid decision '{dec}'"})
            continue
        if not d.get("reasons"):
            problems.append({"record_id": rid, "problem": "decision without reason codes"})
        if dec != "include" and not d.get("evidence"):
            problems.append({"record_id": rid, "problem": "exclude/maybe without evidence snippet"})
        out.append({"record_id": rid, "decision": dec, "reasons": d.get("reasons") or [],
                    "evidence": (d.get("evidence") or "")[:400], "screener": d.get("screener", "agent")})
    missing = [rid for rid in by_id if rid not in seen]
    for rid in missing:
        problems.append({"record_id": rid, "problem": "no decision"})
    counts = {"identified": len(records), "decided": len(out),
              "include": sum(1 for d in out if d["decision"] == "include"),
              "exclude": sum(1 for d in out if d["decision"] == "exclude"),
              "maybe": sum(1 for d in out if d["decision"] == "maybe"),
              "undecided": len(missing)}
    return {"decisions": out, "counts": counts, "problems": problems,
            "ok": not problems}


def dual_screen_conflicts(d1: list[dict], d2: list[dict]) -> dict:
    a = {str(d["record_id"]): d for d in d1}
    b = {str(d["record_id"]): d for d in d2}
    conflicts = []
    for rid in sorted(set(a) & set(b)):
        if a[rid].get("decision") != b[rid].get("decision"):
            conflicts.append({"record_id": rid,
                              "screener_a": {"decision": a[rid].get("decision"), "reasons": a[rid].get("reasons")},
                              "screener_b": {"decision": b[rid].get("decision"), "reasons": b[rid].get("reasons")},
                              "resolution": "needs_adjudication"})
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    agree = sum(1 for rid in set(a) & set(b) if a[rid].get("decision") == b[rid].get("decision"))
    total = len(set(a) & set(b))
    return {"conflicts": conflicts, "only_a": only_a, "only_b": only_b,
            "agreement": {"both_decided": total, "agree": agree,
                          "rate": round(agree / total, 4) if total else None}}


def rank(scored: list[dict], rubric: dict | None = None) -> dict:
    """scored: [{record_id, scores:{criterion:0|1|2}, notes}]
    Stable sort by total; every position explained by the criterion scores."""
    for s in scored:
        if not s.get("scores"):
            return {"ok": False, "error": f"record {s.get('record_id')} has no scores"}
    ordered = sorted(scored, key=lambda s: (-sum(s["scores"].values()), str(s["record_id"])))
    ranking = [{"rank": i + 1, "record_id": s["record_id"],
                "total": sum(s["scores"].values()), "scores": s["scores"],
                "notes": s.get("notes", "")} for i, s in enumerate(ordered)]
    return {"ok": True, "rubric": rubric or {}, "ranking": ranking,
            "explain_note": "rank = stable sort by rubric total; ties keep record_id order"}


def _demo() -> int:
    recs = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    dec = [{"record_id": "A", "decision": "include", "reasons": ["PICO:P", "PICO:I"],
            "evidence": "adults received the intervention"},
           {"record_id": "B", "decision": "exclude", "reasons": ["wrong_population"],
            "evidence": "in vitro cell line study only"},
           {"record_id": "C", "decision": "maybe", "reasons": ["unclear_outcome"],
            "evidence": "outcome not clearly reported"}]
    rep = validate_decisions(recs, dec)
    assert rep["ok"] and rep["counts"]["include"] == 1
    dec2 = [dict(d, decision="exclude", reasons=["rater2_excludes"]) if d["record_id"] == "A" else d
            for d in dec]
    conf = dual_screen_conflicts(rep["decisions"], dec2)
    assert len(conf["conflicts"]) == 1 and conf["agreement"]["agree"] == 2
    rk = rank([{"record_id": "A", "scores": {"relevance": 2, "recency": 1}},
               {"record_id": "B", "scores": {"relevance": 2, "recency": 2}}])
    assert rk["ranking"][0]["record_id"] == "B"
    print(json.dumps({"demo": "screen", "counts": rep["counts"], "conflicts": len(conf["conflicts"]),
                      "agreement": conf["agreement"]["rate"], "top1": rk["ranking"][0]["record_id"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        recs = json.load(open(sys.argv[2], encoding="utf-8"))
        dec = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = validate_decisions(recs.get("records", recs), dec.get("decisions", dec))
    elif cmd == "conflicts":
        rep = dual_screen_conflicts(json.load(open(sys.argv[2], encoding="utf-8")),
                                    json.load(open(sys.argv[3], encoding="utf-8")))
    elif cmd == "rank":
        rep = rank(json.load(open(sys.argv[2], encoding="utf-8")))
    else:
        print("usage: screen.py [validate|conflicts|rank] ..."); sys.exit(2)
    out = sys.argv[4] if cmd == "validate" and len(sys.argv) > 4 else (sys.argv[4] if len(sys.argv) > 4 else None)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"ok={rep.get('ok', True)} -> {out}")
    else:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
