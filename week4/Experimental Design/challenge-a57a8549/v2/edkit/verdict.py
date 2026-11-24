"""Feasibility verdict builder: the conclusion is computed, not narrated.

Rules (all deterministic):
- ANY unchecked checklist item  -> verdict = incomplete (无法完整判定):
  the unchecked items are enumerated by id; nothing unwritten is defaulted
  to satisfied, and no feasibility claim is issued on partial coverage.
- ANY failed check, unavailable resource, broken budget, infeasible booking
  or un-mitigated HIGH risk -> infeasible (不可行), blocking facts enumerated
  with both operands/locators.
- Otherwise, if any conditional check / purchase_needed / outsource /
  needs_review item exists -> conditional (有条件可行) and EVERY condition is
  enumerated as an executable string; a bare "建议进一步确认" is not allowed.
- Only full coverage + zero failures + zero conditions -> feasible (可行).
"""
from __future__ import annotations

import json
import sys

VERDICTS = ("feasible", "conditional", "infeasible", "incomplete")
LABELS = {"feasible": "可行", "conditional": "有条件可行",
          "infeasible": "不可行", "incomplete": "无法完整判定（存在未检查项）"}


def build_verdict(checklist: dict, materials: dict | None = None,
                  budget: dict | None = None, schedule: dict | None = None,
                  bookings: list | None = None, bounds: dict | None = None,
                  risk_validation: dict | None = None) -> dict:
    items = checklist["items"]
    unchecked = [{"id": i["id"], "facet": i["facet"], "question": i["question"]}
                 for i in items if i["status"] == "unchecked"]
    failed = [{"id": i["id"], "facet": i["facet"], "evidence": i.get("evidence", []),
               "note": i.get("note", "")} for i in items if i["status"] == "fail"]
    conditions, blocking = [], []

    for i in items:
        if i["status"] == "conditional":
            conditions.append({"source": f"checklist/{i['id']}", "facet": i["facet"],
                               "condition": i["condition"],
                               "evidence": i.get("evidence", [])})
        if i["status"] == "needs_review":
            conditions.append({"source": f"checklist/{i['id']}", "facet": i["facet"],
                               "condition": f"待复核项须确认后方可执行：{i.get('note') or i['question']}",
                               "evidence": i.get("evidence", [])})

    for m in (materials or {}).get("items", []):
        st, name = m["status"], m["name"]
        if st == "unavailable":
            blocking.append({"source": f"resources/{m['id']}", "fact": f"{name} 缺 {m['shortfall']['qty']} {m['shortfall']['unit']} 且无采购/外协途径",
                             "required": m["required"], "available": m.get("available")})
        elif st == "purchase_needed":
            p = m["purchase"]
            conditions.append({"source": f"resources/{m['id']}",
                               "condition": f"采购 {name} {p['qty']} {p['unit']}（{p['total_price']} {p['currency']}，货期 {p['lead_days']} 天）须在启动前到货",
                               "evidence": [{"quote": p["formula"], "locator": p["locator"]}]})
        elif st == "outsource":
            conditions.append({"source": f"resources/{m['id']}",
                               "condition": f"{name} 缺口 {m['shortfall']['qty']} {m['shortfall']['unit']} 须落实外协渠道",
                               "evidence": []})
        elif st == "unit_mismatch":
            blocking.append({"source": f"resources/{m['id']}", "fact": m.get("problem", "unit mismatch")})

    if budget and not budget.get("within", True):
        blocking.append({"source": "budget",
                         "fact": f"总费用 {budget['total']} {budget['currency']} 超出预算 {budget['budget']} {budget['currency']}（缺口 {budget['remaining']}）",
                         "operands": budget.get("operands")})
    if schedule and not schedule.get("feasible", True):
        fact = f"总时长 {schedule['total_hours']} h 超出可用窗口 {schedule['available_hours']} h" if not schedule.get("steps_without_duration") \
            else f"存在无时长依据的步骤 {schedule['steps_without_duration']}，总周期不可判定"
        blocking.append({"source": "schedule", "fact": fact, "operands": schedule.get("operands")})
    for bk in bookings or []:
        if not bk.get("feasible", True):
            blocking.append({"source": "booking",
                             "fact": f"最早机时 {bk['earliest_slot']} 晚于需求截止 {bk['needed_by']}（差 {bk['slack_days']} 天）",
                             "operands": bk.get("operands")})
    for b in (bounds or {}).get("items", []):
        if b["status"] == "out_of_domain":
            blocking.append({"source": f"bounds/{b['name']}",
                             "fact": f"参数 {b['name']}={b['value']}{b['unit']} 超出可行域 [{b['domain']['lo']}, {b['domain']['hi']}]{b['domain']['unit']}（越界 {b['overflow']}）",
                             "operands": {"value": b["value"], "lo": b["domain"]["lo"], "hi": b["domain"]["hi"]}})
        elif b["status"] in ("no_domain", "unit_mismatch"):
            blocking.append({"source": f"bounds/{b['name']}", "fact": f"参数 {b['name']} {b['status']}：无法验证，不得默认在域内"})
    if risk_validation:
        for p in risk_validation.get("problems", []):
            if "HIGH risk" in p:
                blocking.append({"source": "riskreg", "fact": p})

    if unchecked:
        verdict = "incomplete"
    elif failed or blocking:
        verdict = "infeasible"
        blocking = [{"source": f"checklist/{f['id']}", "fact": f"检查项不满足：{f['note']}",
                     "evidence": f["evidence"]} for f in failed] + blocking
    elif conditions:
        verdict = "conditional"
    else:
        verdict = "feasible"
    return {"verdict": verdict, "verdict_label": LABELS[verdict],
            "conditions": conditions, "blocking": blocking,
            "unchecked_items": unchecked,
            "counts": {"conditions": len(conditions), "blocking": len(blocking),
                       "unchecked": len(unchecked)},
            "rule_note": "有条件可行必须逐条列出可执行条件；存在未检查项时不下可行性结论；"
                         "方案没写的内容一律不默认满足"}


def _demo() -> int:
    from . import checklist as cl_mod
    from . import resources as res

    # Path 1 (the forbidden failure): untouched checklist -> NOT feasible.
    cl = cl_mod.default_checklist()
    v = build_verdict(cl)
    assert v["verdict"] == "incomplete" and len(v["unchecked_items"]) == 12, v

    # Path 2: full coverage, one conditional + one purchase -> 有条件可行 with exact conditions.
    cl = cl_mod.default_checklist()
    for it in cl["items"]:
        cl_mod.set_status(cl, it["id"], "pass", evidence=[{"quote": "ok", "locator": "plan.md L1"}])
    cl_mod.set_status(cl, "eq-booking", "conditional",
                      condition="盐雾箱改约至 2026-03-01 前的机时档",
                      evidence=[{"quote": "earliest=2026-03-10 > needed_by=2026-03-05", "locator": "booking.json L7"}])
    mats = res.check_materials([{"id": "M1", "name": "培养液", "qty": "1500", "unit": "mL", "locator": "plan.md L18"}],
                               [{"name": "培养液", "qty": "1000", "unit": "mL", "locator": "inventory.csv L4"}],
                               {"培养液": {"price": "0.35", "lead_days": 7, "locator": "catalog.csv L2"}})
    v = build_verdict(cl, materials=mats,
                      budget=res.check_budget([{"id": "M1", "total_price": "175"}],
                                              {"amount": "600", "currency": "CNY"}))
    assert v["verdict"] == "conditional" and v["counts"]["conditions"] == 2, v
    assert any("采购 培养液 500 mL（175 CNY" in c["condition"] for c in v["conditions"]), v["conditions"]

    # Path 3: a fail + out-of-domain parameter -> 不可行 with blocking operands.
    cl_mod.set_status(cl, "sample-size", "fail", note="无样本量依据",
                      evidence=[{"quote": "方案未给出功效估算", "locator": "plan.md L12"}])
    bd = res.check_bounds([{"name": "温度", "value": "85", "unit": "℃", "locator": "plan.md L8"}],
                          {"温度": {"lo": "20", "hi": "80", "unit": "℃", "locator": "manual L3"}})
    v = build_verdict(cl, materials=mats, bounds=bd)
    assert v["verdict"] == "infeasible" and len(v["blocking"]) >= 2, v
    assert any(b.get("operands", {}).get("hi") == "80" for b in v["blocking"])
    print(json.dumps({"demo": "verdict", "incomplete_guard": True,
                      "conditional_conditions": 2, "infeasible_blocking": len(v["blocking"])},
                     ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "build":
        cl = json.load(open(argv[1], encoding="utf-8"))
        kw = {}
        if argv[2] != "-":
            pack = json.load(open(argv[2], encoding="utf-8"))
            kw = {k: pack.get(k) for k in ("materials", "budget", "schedule", "bookings",
                                           "bounds", "risk_validation") if pack.get(k) is not None}
        rep = build_verdict(cl, **kw)
        out = argv[3] if len(argv) > 3 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"verdict": rep["verdict"], "label": rep["verdict_label"],
                          "counts": rep["counts"]}, ensure_ascii=False))
        return 0 if rep["verdict"] != "infeasible" else 1
    print("usage: verdict build <checklist.json> <evidence_pack.json|-> [out.json]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
