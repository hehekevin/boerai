"""Resource cross-check: plan requirements vs case-provided inventories,
price catalogs and booking contracts — exact arithmetic only.

Rules:
- Numbers are int or decimal/fraction strings parsed into Fraction. float is
  rejected at the door: no rounding, ever. Shortfalls and prices are exact.
- Every comparison carries BOTH operands, the unit, and source locators.
- Unit mismatch or missing inventory/catalog entry is reported explicitly;
  nothing is assumed available because the plan did not mention it.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from fractions import Fraction

STATUSES = ("available", "outsource", "purchase_needed", "unavailable", "unit_mismatch")


def num(x) -> Fraction:
    """Parse int / '12' / '12.50' / '1/3' exactly; reject float."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, bool):
        raise TypeError("boolean is not a quantity")
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, float):
        raise TypeError(f"float {x!r} rejected: pass an int or a decimal string for exact arithmetic")
    s = str(x).strip().replace(",", "")
    if "/" in s:
        a, b = s.split("/", 1)
        return Fraction(a.strip()) / Fraction(b.strip())
    return Fraction(s)


def f2s(f: Fraction) -> str:
    """Exact string: integer, terminating decimal (denominator = 2^a*5^b), or
    'num/den' — never a rounded float."""
    if f.denominator == 1:
        return str(f.numerator)
    d = f.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d == 1:  # terminating decimal, render exactly
        n, denom = f.numerator, f.denominator
        digits = 0
        while denom > 1:
            denom //= 10 if denom % 10 == 0 else 2 if denom % 2 == 0 else 5
            digits += 1
        scaled = abs(n) * 10 ** digits // f.denominator
        s = str(scaled).rjust(digits + 1, "0")
        body = s[:-digits] + "." + s[-digits:]
        return ("-" if n < 0 else "") + body
    return f"{f.numerator}/{f.denominator}"


def _side(qty: Fraction, unit: str, locator: str) -> dict:
    return {"qty": f2s(qty), "unit": unit, "locator": locator}


def check_materials(requirements: list[dict], inventory: list[dict],
                    catalog: dict | None = None, outsource: list | None = None) -> dict:
    """Per requirement: required vs available with shortfall, exact purchase
    cost for shortfall, or an explicit unavailable/unit_mismatch state.
    status 四态对齐题面：已具备/可外协/需采购/不具备（+unit_mismatch 显式异常）。"""
    catalog = catalog or {}
    outsource = set(outsource or [])
    inv_by_name = {i["name"]: i for i in inventory}
    items, problems = [], []
    for req in requirements:
        name, unit = req["name"], req.get("unit", "")
        need = num(req["qty"])
        rec = {"id": req.get("id", name), "name": name,
               "required": _side(need, unit, req.get("locator", ""))}
        inv = inv_by_name.get(name)
        if inv is None:
            avail = None
            rec["available"] = None
            problems.append(f"{name}: no inventory entry — treated as 0 available, explicitly")
            have = Fraction(0)
        else:
            have = num(inv["qty"])
            rec["available"] = _side(have, inv.get("unit", unit), inv.get("locator", ""))
            if inv.get("unit", unit) != unit:
                rec["status"] = "unit_mismatch"
                rec["problem"] = f"unit mismatch: required '{unit}' vs inventory '{inv.get('unit')}'"
                problems.append(f"{name}: unit mismatch, comparison refused until resolved")
                items.append(rec)
                continue
        shortfall = need - have
        rec["shortfall"] = _side(shortfall if shortfall > 0 else Fraction(0), unit,
                                 "computed = required - available")
        if shortfall <= 0:
            rec["status"] = "available"
        elif name in outsource:
            rec["status"] = "outsource"
        elif name in catalog:
            cat = catalog[name]
            price = num(cat["price"])
            total = shortfall * price
            rec["status"] = "purchase_needed"
            rec["purchase"] = {"qty": f2s(shortfall), "unit": unit,
                               "unit_price": f2s(price), "currency": cat.get("currency", "CNY"),
                               "total_price": f2s(total), "lead_days": cat.get("lead_days"),
                               "locator": cat.get("locator", ""),
                               "formula": f"{f2s(shortfall)} {unit} * {f2s(price)} = {f2s(total)}"}
        else:
            rec["status"] = "unavailable"
            problems.append(f"{name}: shortfall {f2s(shortfall)} {unit} and no purchase/outsource path")
        items.append(rec)
    return {"items": items, "problems": problems,
            "note": "both operands + unit + locator on every comparison; float rejected"}


def check_budget(line_items: list[dict], budget: dict) -> dict:
    """Sum purchase/other line items exactly and compare with the budget."""
    total = Fraction(0)
    for li in line_items:
        total += num(li["total_price"])
    cap = num(budget["amount"])
    remaining = cap - total
    return {"total": f2s(total), "budget": f2s(cap), "currency": budget.get("currency", "CNY"),
            "remaining": f2s(remaining), "within": remaining >= 0,
            "budget_locator": budget.get("locator", ""),
            "operands": {"total": f2s(total), "budget": f2s(cap)},
            "note": "exact Fraction sum; no rounding"}


def check_schedule(steps: list[dict], window: dict) -> dict:
    """Sum per-step durations (hours, exact) and compare with the available
    window. Steps without a duration are listed explicitly, never assumed 0."""
    total = Fraction(0)
    missing = []
    for st in steps:
        if st.get("duration_hours") in (None, ""):
            missing.append(st.get("id", "?"))
            continue
        total += num(st["duration_hours"])
    avail = num(window["available_hours"])
    slack = avail - total
    return {"total_hours": f2s(total), "available_hours": f2s(avail),
            "slack_hours": f2s(slack), "feasible": slack >= 0 and not missing,
            "steps_without_duration": missing,
            "operands": {"total_hours": f2s(total), "available_hours": f2s(avail)},
            "window_locator": window.get("locator", ""),
            "note": "steps without duration make the schedule infeasible-to-judge, not 0-cost"}


def check_booking(requirement: dict, contract: dict) -> dict:
    """Booking-window arithmetic on ISO dates (exact ints) plus exact session
    cost. Carries both dates and the computed slack in days."""
    needed_by = _dt.date.fromisoformat(requirement["needed_by"])
    earliest = _dt.date.fromisoformat(contract["earliest_slot"])
    sessions = num(requirement["sessions"])
    hours_per = num(contract["session_hours"])
    price = num(contract["price_per_session"])
    total_hours = sessions * hours_per
    total_cost = sessions * price
    slack_days = (needed_by - earliest).days
    return {"feasible": slack_days >= 0,
            "needed_by": str(needed_by), "earliest_slot": str(earliest),
            "slack_days": slack_days,
            "total_hours": f2s(total_hours), "total_cost": f2s(total_cost),
            "currency": contract.get("currency", "CNY"),
            "operands": {"needed_by": str(needed_by), "earliest_slot": str(earliest),
                         "sessions": f2s(sessions), "session_hours": f2s(hours_per)},
            "locators": {"requirement": requirement.get("locator", ""),
                         "contract": contract.get("locator", "")},
            "note": "infeasible booking is a blocking fact with both dates shown, not a suggestion"}


def check_bounds(params: list[dict], domains: dict) -> dict:
    """Finite parameter domains: value vs [lo, hi], exact margins both sides.
    A parameter without a declared domain is reported, never assumed in-range."""
    items, problems = [], []
    for p in params:
        name = p["name"]
        val = num(p["value"])
        dom = domains.get(name)
        rec = {"name": name, "value": f2s(val), "unit": p.get("unit", ""),
               "value_locator": p.get("locator", "")}
        if dom is None:
            rec["status"] = "no_domain"
            problems.append(f"{name}: no declared domain — cannot validate, reported explicitly")
            items.append(rec)
            continue
        lo, hi = num(dom["lo"]), num(dom["hi"])
        if dom.get("unit", p.get("unit", "")) != p.get("unit", ""):
            rec["status"] = "unit_mismatch"
            problems.append(f"{name}: domain unit '{dom.get('unit')}' != value unit '{p.get('unit')}'")
        else:
            rec["status"] = "in_domain" if lo <= val <= hi else "out_of_domain"
        rec["domain"] = {"lo": f2s(lo), "hi": f2s(hi), "unit": dom.get("unit", ""),
                         "locator": dom.get("locator", "")}
        rec["margins"] = {"above_lo": f2s(val - lo), "below_hi": f2s(hi - val)}
        if rec["status"] == "out_of_domain":
            over = (val - hi) if val > hi else (lo - val)
            rec["overflow"] = f2s(over)
            problems.append(f"{name}: {f2s(val)} outside [{f2s(lo)}, {f2s(hi)}] by {f2s(over)}")
        items.append(rec)
    return {"items": items, "problems": problems,
            "note": "finite domains only; both bounds + locators carried; margins exact"}


def _demo() -> int:
    reqs = [{"id": "M1", "name": "培养液", "qty": "1500", "unit": "mL", "locator": "plan.md L18"},
            {"id": "M2", "name": "离心管", "qty": "200", "unit": "支", "locator": "plan.md L19"},
            {"id": "M3", "name": "稀有抗体", "qty": "3", "unit": "支", "locator": "plan.md L20"}]
    inv = [{"name": "培养液", "qty": "1000", "unit": "mL", "locator": "inventory.csv L4"},
           {"name": "离心管", "qty": "250", "unit": "支", "locator": "inventory.csv L5"}]
    cat = {"培养液": {"price": "0.35", "currency": "CNY", "lead_days": 7, "locator": "catalog.csv L2"}}
    rep = check_materials(reqs, inv, cat, outsource=["离心管"])
    m1 = rep["items"][0]
    assert m1["shortfall"]["qty"] == "500" and m1["status"] == "purchase_needed", m1
    assert m1["purchase"]["total_price"] == "175", m1["purchase"]  # 500 * 0.35 exact
    m2 = rep["items"][1]
    assert m2["status"] == "available" and m2["available"]["locator"] == "inventory.csv L5"
    m3 = rep["items"][2]
    assert m3["status"] == "unavailable" and m3["shortfall"]["qty"] == "3"
    bud = check_budget([{"id": "M1", "total_price": "175"},
                        {"id": "X", "total_price": "424.97"}],
                       {"amount": "600", "currency": "CNY", "locator": "case.json L9"})
    assert bud["total"] == "599.97" and bud["remaining"] == "0.03" and bud["within"], bud
    sch = check_schedule([{"id": "S1", "duration_hours": "2.5"},
                          {"id": "S2", "duration_hours": "1/3"}, {"id": "S3"}],
                         {"available_hours": "4", "locator": "case.json L11"})
    assert sch["total_hours"] == "17/6" and sch["steps_without_duration"] == ["S3"], sch
    assert not sch["feasible"]  # missing duration -> not judgeable
    bk = check_booking({"needed_by": "2026-03-05", "sessions": "3", "locator": "plan.md L22"},
                       {"earliest_slot": "2026-03-10", "session_hours": "4",
                        "price_per_session": "800", "locator": "booking.json L7"})
    assert bk["slack_days"] == -5 and not bk["feasible"] and bk["total_cost"] == "2400", bk
    bd = check_bounds([{"name": "温度", "value": "85", "unit": "℃", "locator": "plan.md L8"},
                       {"name": "转速", "value": "3000", "unit": "rpm", "locator": "plan.md L9"}],
                      {"温度": {"lo": "20", "hi": "80", "unit": "℃", "locator": "manual L3"}})
    assert bd["items"][0]["status"] == "out_of_domain" and bd["items"][0]["overflow"] == "5"
    assert bd["items"][1]["status"] == "no_domain"
    try:
        num(0.1)
        raise AssertionError("float was accepted")
    except TypeError:
        pass
    print(json.dumps({"demo": "resources", "shortfall_mL": "500", "cost_exact": "175",
                      "budget_remaining": "0.03", "booking_slack_days": -5,
                      "overflow_C": "5", "float_rejected": True}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 5 and argv[0] == "materials":
        reqs = json.load(open(argv[1], encoding="utf-8"))
        inv = json.load(open(argv[2], encoding="utf-8"))
        cat = json.load(open(argv[3], encoding="utf-8")) if argv[3] != "-" else {}
        rep = check_materials(reqs.get("requirements", reqs), inv.get("inventory", inv),
                              cat.get("catalog", cat), cat.get("outsource"))
        json.dump(rep, open(argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"materials: {len(rep['items'])} items, problems={len(rep['problems'])} -> {argv[4]}")
        return 0 if not rep["problems"] else 1
    if len(argv) >= 3 and argv[0] == "bounds":
        params = json.load(open(argv[1], encoding="utf-8"))
        domains = json.load(open(argv[2], encoding="utf-8"))
        rep = check_bounds(params.get("parameters", params), domains.get("domains", domains))
        out = argv[3] if len(argv) > 3 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"items": len(rep["items"]), "problems": rep["problems"]},
                         ensure_ascii=False))
        return 0 if not rep["problems"] else 1
    print("usage: resources materials <req.json> <inv.json> <catalog.json|-> <out.json> | "
          "resources bounds <params.json> <domains.json> [out.json]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
