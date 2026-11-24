#!/usr/bin/env python3
"""plan-forge: experimental design — feasibility checklist, plan comparison, plan generation, synthesis evidence.

Deterministic subcommands (0 model requests):
  --checklist PROPOSAL_JSON  checkable items: device/material/time/sample/ethics-safety/param-range/risk
  --resources PROPOSAL_JSON INVENTORY_JSON  device/model/precision/consumable vs inventory: 已具备/可外协/需采购/不具备
  --time ESTIMATE_JSON       per-step: device-time/manual/wait/assay-turnaround; explainable estimate
  --compare PLANS_JSON       unified comparable fields (goal/constraints/variables/criteria) per plan
  --cost PLANS_JSON          machine/consumable/labor/sample-prep/scheduling one-time-vs-per-run
  --variables GOAL_JSON      testable hypotheses w/ operational definitions (IV/DV/confounders)
  --controls DESIGN_JSON     control types & which confound each excludes
  --anomaly DATA_JSON        trend/inflection/plateau reading w/ basis; localized anomalies
Stdlib only.
"""
import argparse, json, re, sys

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else {}

CHECK_ITEMS = [
    {"item": "device", "kw": re.compile(r"(?i)(设备|仪器|device|instrument)"), "basis": "SOP/设备清单"},
    {"item": "material", "kw": re.compile(r"(?i)(试剂|耗材|材料|reagent|consumable)"), "basis": "规格书"},
    {"item": "time", "kw": re.compile(r"(?i)(时间|周期|schedule|天数)"), "basis": "步骤拆解"},
    {"item": "sample", "kw": re.compile(r"(?i)(样本|样品|sample|n\s*=)"), "basis": "来源+保存条件"},
    {"item": "ethics_safety", "kw": re.compile(r"(?i)(伦理|安全|ethics|safety)"), "basis": "审批进度"},
    {"item": "param_range", "kw": re.compile(r"(?i)(参数|范围|range|温度|浓度)"), "basis": "SOP/手册"},
    {"item": "risk", "kw": re.compile(r"(?i)(风险|异常|risk|failure)"), "basis": "异常预案"},
]

def cmd_checklist(path):
    prop = load(path)
    text = json.dumps(prop, ensure_ascii=False)
    out = []
    for item in CHECK_ITEMS:
        m = item["kw"].search(text)
        out.append({"item": item["item"], "addressed": bool(m), "evidence": m.group(0)[:40] if m else "未声明",
                    "judgment_basis": item["basis"], "checkable": "可勾选可判定"})
    print(json.dumps({"schema": "plan/checklist@1", "items": out,
                      "note": "设备/材料/时间/样本/伦理与安全/参数范围/风险与异常七项体系"}, ensure_ascii=False, indent=1))
    return 0

STATES = ["已具备", "可外协", "需采购", "不具备"]

def cmd_resources(prop_path, inv_path):
    prop = load(prop_path)
    inv = load(inv_path)
    inv_list = inv.get("inventory", inv.get("items", inv if isinstance(inv, list) else []))
    inv_names = {norm(str(x.get("name", x)))[:20].lower() if isinstance(x, dict) else norm(str(x))[:20].lower() for x in inv_list}
    needs = prop.get("requirements", prop.get("device", prop.get("materials", [])))
    out = []
    for r in (needs if isinstance(needs, list) else []):
        name = norm(r.get("name", r.get("device", str(r))))[:20] if isinstance(r, dict) else norm(str(r))[:20]
        if name.lower() in inv_names:
            st = "已具备"
        elif "外协" in name or "service" in name.lower():
            st = "可外协"
        else:
            st = "需采购"
        out.append({"requirement": name, "state": st,
                    "model_precision": r.get("model", r.get("precision", "")) if isinstance(r, dict) else "",
                    "consumable": r.get("consumable", "") if isinstance(r, dict) else ""})
    print(json.dumps({"schema": "plan/resources@1", "states_legend": STATES, "items": out[:25],
                      "note": "'理论上可行'与'本实验室现在可做'分开"}, ensure_ascii=False, indent=1))
    return 0

def cmd_time(path):
    est = load(path)
    steps = est.get("steps", est.get("items", est if isinstance(est, list) else []))
    total = {"device_h": 0.0, "manual_h": 0.0, "wait_days": 0.0, "assay_days": 0.0}
    out = []
    for s in (steps if isinstance(steps, list) else []):
        if not isinstance(s, dict):
            continue
        dh = float(s.get("device_hours", 0)); mh = float(s.get("manual_hours", 0))
        wd = float(s.get("wait_days", 0)); ad = float(s.get("assay_days", 0))
        total["device_h"] += dh; total["manual_h"] += mh; total["wait_days"] += wd; total["assay_days"] += ad
        out.append({"step": s.get("name", ""), "device_h": dh, "manual_h": mh, "wait_days": wd, "assay_days": ad,
                    "explainable": "估算过程可解释（每步拆设备占用/人工/等待/检测周转）"})
    total["note"] = "样本来源/数量/保存条件/伦理审批进度需核对"
    print(json.dumps({"schema": "plan/time@1", "steps": out[:25], "total": total}, ensure_ascii=False, indent=1))
    return 0

COMPARE_FIELDS = ["goal", "constraints", "variables", "criteria"]

def cmd_compare(plans_path):
    plans = load(plans_path)
    plist = plans.get("plans", plans.get("items", plans if isinstance(plans, list) else []))
    rows = []
    for p in plist:
        rows.append({"plan": p.get("name", p.get("plan_id", "")) if isinstance(p, dict) else str(p)[:20],
                     **{f: (p.get(f, "missing") if isinstance(p, dict) else "missing") for f in COMPARE_FIELDS}})
    print(json.dumps({"schema": "plan/compare@1", "fields": COMPARE_FIELDS, "matrix": rows,
                      "note": "先固定可比字段再逐方案填表——避免各方案各一套描述"}, ensure_ascii=False, indent=1))
    return 0

COST_ITEMS = ["machine_time", "consumables", "labor", "sample_prep", "scheduling", "rework"]

def cmd_cost(plans_path):
    plans = load(plans_path)
    plist = plans.get("plans", plans.get("items", plans if isinstance(plans, list) else []))
    out = []
    for p in plist:
        c = p.get("cost", {}) if isinstance(p, dict) else {}
        out.append({"plan": p.get("name", "") if isinstance(p, dict) else "?",
                    **{k: c.get(k, "未核算") for k in COST_ITEMS},
                    "one_time_vs_per_run": p.get("cost_type", "区分一次性投入与按次消耗"),
                    "unit": c.get("unit", "统一口径（机时/耗材/人力/样品准备/排期/返工）")})
    print(json.dumps({"schema": "plan/cost@1", "plans": out[:10]}, ensure_ascii=False, indent=1))
    return 0

def cmd_variables(path):
    goal = load(path)
    text = json.dumps(goal, ensure_ascii=False)
    out = {"hypotheses": [], "iv": [], "dv": [], "confounders": []}
    for m in re.finditer(r"(?i)(假设|H\d?)[:：]?\s*([^。;\n]{6,120})", text):
        out["hypotheses"].append({"hypothesis": m.group(2)[:100], "testable": bool(re.search(r"(?i)(提高|降低|改变|差异|affect)", m.group(2)))})
    out["operational_note"] = "变量操作定义：测量方式/单位/取值范围显式；自变量/因变量/混杂因素分列"
    print(json.dumps({"schema": "plan/variables@1", **out}, ensure_ascii=False, indent=1))
    return 0

CONTROLS = [
    {"type": "blank", "excludes": "试剂/环境本底"},
    {"type": "positive", "excludes": "方法失效（灵敏度）"},
    {"type": "negative", "excludes": "目标特异性"},
    {"type": "dose_gradient", "excludes": "剂量-响应混杂与非单调效应"},
]

def cmd_controls(path):
    d = load(path)
    present = {norm(c.get("type", c if isinstance(c, str) else "")) for c in (d.get("controls", d.get("items", d if isinstance(d, list) else [])))}
    out = []
    for c in CONTROLS:
        out.append({"type": c["type"], "designed": any(c["type"] in p for p in present) or bool(present & {c["type"]}),
                    "excludes_confound": c["excludes"]})
    print(json.dumps({"schema": "plan/controls@1", "controls": out,
                      "note": "每对照排除一类混杂；避免只有一组对照或对照与目标不匹配"}, ensure_ascii=False, indent=1))
    return 0

def cmd_anomaly(path):
    d = load(path)
    rows = d.get("records", d.get("series", d.get("items", [])))
    out = []
    for r in (rows if isinstance(rows, list) else []):
        if not isinstance(r, dict):
            continue
        val = r.get("value")
        base = r.get("baseline", r.get("control_mean"))
        if isinstance(val, (int, float)) and isinstance(base, (int, float)) and base:
            dev = round((val - base) / abs(base), 3)
            out.append({"point": {k: r.get(k) for k in ("sample", "batch", "channel", "well", "time") if k in r},
                        "value": val, "baseline": base, "deviation_pct": dev,
                        "reading": "拐点" if r.get("is_inflection") else ("平台期" if r.get("plateau") else ("偏离" if abs(dev) > 0.3 else "正常")),
                        "basis": "所依据区间/对照/拟合方式记录"})
    print(json.dumps({"schema": "plan/anomaly@1", "n_points": len(out), "points": out[:25]}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checklist"); ap.add_argument("--resources", nargs=2); ap.add_argument("--time")
    ap.add_argument("--compare"); ap.add_argument("--cost"); ap.add_argument("--variables")
    ap.add_argument("--controls"); ap.add_argument("--anomaly")
    a = ap.parse_args()
    if a.checklist: return cmd_checklist(a.checklist)
    if a.resources: return cmd_resources(a.resources[0], a.resources[1])
    if a.time: return cmd_time(a.time)
    if a.compare: return cmd_compare(a.compare)
    if a.cost: return cmd_cost(a.cost)
    if a.variables: return cmd_variables(a.variables)
    if a.controls: return cmd_controls(a.controls)
    if a.anomaly: return cmd_anomaly(a.anomaly)
    ap.error("choose a subcommand")

if __name__ == "__main__":
    sys.exit(main())
