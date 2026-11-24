#!/usr/bin/env python3
"""edkit 冒烟测试：6 个模块 demo + 一次端到端（合成案例：
probe → extract → review 预扫描 → 未检查项守卫 → Agent 填表 → 资源精确核对 →
verdict 构建 → emit → result.json）。所有数据为接口演示构造，非正式案例结果。"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["planparse", "checklist", "resources", "plandiff", "riskreg", "verdict"]

PLAN = """# 实验方案 v1（合成示例）
## 1 研究目标
验证纳米涂层对镁合金腐蚀的抑制效果。
## 2 参数
温度: 37 ℃
时长: 48 h
样本量: 12 例
## 3 步骤
1. 准备样品并按涂层/未涂层分组。
2. 若样本不足 12 例则启动补采并通知 PI。
3. 盐雾箱恒温恒湿运行并记录数据。
## 4 资源
设备：盐雾试验箱（型号 SY-9），需预约排期。
耗材：培养液 1500 mL，离心管 200 支。
"""

INVENTORY = {"inventory": [
    {"name": "培养液", "qty": "1000", "unit": "mL", "locator": "inventory.json#1"},
    {"name": "离心管", "qty": "250", "unit": "支", "locator": "inventory.json#2"}]}

CATALOG = {"catalog": {"培养液": {"price": "0.35", "currency": "CNY", "lead_days": 7,
                                    "locator": "catalog.json#1"}},
           "outsource": ["离心管"]}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"edkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"{m:12s} ERROR {e}")
            failed.append(m)

    # ---------------- end-to-end with a synthetic case ----------------
    tmp = tempfile.mkdtemp(prefix="edkit-e2e-")
    inp = os.path.join(tmp, "input"); os.makedirs(inp)
    work = os.path.join(tmp, "work"); out = os.path.join(tmp, "out")
    json.dump({"case_id": "demo-feas-case",
               "task": "审查方案可行性并给出结论",
               "output_contract": {"review_report": "md", "checklist": "json", "verdict": "json"}},
              open(f"{inp}/case.json", "w"))
    open(f"{inp}/plan.md", "w", encoding="utf-8").write(PLAN)
    json.dump(INVENTORY, open(f"{inp}/inventory.json", "w"))
    json.dump(CATALOG, open(f"{inp}/catalog.json", "w"))

    ok = True
    for cmd in ([sys.executable, f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json",
                 "--input", inp, "--out", work],
                [sys.executable, f"{HERE}/run.py", "extract", "--work", work],
                [sys.executable, f"{HERE}/run.py", "review", "--work", work, "--source", f"{inp}/plan.md"]):
        r = run(cmd)
        if r.returncode != 0:
            ok = False
            print("E2E step failed:", cmd[2], r.stderr[-400:])

    # guard: verdict on the untouched checklist must be incomplete (forbidden-failure path)
    r = run([sys.executable, f"{HERE}/run.py", "verdict", "build", f"{work}/checklist.json", "-",
             f"{work}/verdict_guard.json"])
    guard = json.load(open(f"{work}/verdict_guard.json"))
    if not (guard["verdict"] == "incomplete" and len(guard["unchecked_items"]) == 12):
        ok = False
        print("E2E guard failed: untouched checklist did not yield incomplete")

    # simulate the agent: evidence-backed checklist fill + risk register + resource check
    from edkit import checklist as cl_mod, riskreg, resources
    cl = cl_mod.load(f"{work}/checklist.json")
    ev = lambda q, l: [{"quote": q, "locator": l}]
    for iid, st, kw in [
        ("eq-presence", "pass", {"evidence": ev("盐雾试验箱 SY-9 在册", "inventory.json#9 / plan.md L14")}),
        ("eq-booking", "conditional", {"condition": "盐雾箱改约至 2026-03-01 前机时档",
                                       "evidence": ev("earliest=2026-03-10 > needed_by=2026-03-05", "booking#1")}),
        ("mat-quantity", "conditional", {"condition": "培养液补足 500 mL（采购 175 CNY，货期 7 天）",
                                         "evidence": ev("需求1500 vs 库存1000 mL", "inventory.json#1 / plan.md L15")}),
        ("mat-procurement", "pass", {"evidence": ev("175 CNY ≤ 预算 600", "catalog.json#1")}),
        ("time-estimate", "pass", {"evidence": ev("逐步时长 2.5h+1/3h…", "plan.md L9-L11")}),
        ("time-window", "pass", {"evidence": ev("总时长 48h ≤ 窗口 72h", "plan.md L7")}),
        ("sample-source", "pass", {"evidence": ev("来源/数量/保存三要素齐", "plan.md L8")}),
        ("sample-size", "pass", {"evidence": ev("12 例依据预实验功效估算", "plan.md L8")}),
        ("ethics-approval", "not_applicable", {"note": "不涉及动物/人体/个人数据"}),
        ("ethics-consent", "not_applicable", {"note": "同上"}),
        ("safety-hazard", "pass", {"evidence": ev("盐雾箱高温防护见 SOP-3", "sop.md L3")}),
        ("safety-waste", "pass", {"evidence": ev("废液按 SOP-7 回收", "sop.md L7")}),
    ]:
        cl_mod.set_status(cl, iid, st, **kw)
    cl_mod.save(cl, f"{work}/checklist.json")

    reg = riskreg.new_register("plan.md")
    riskreg.add_risk(reg, risk_id="K1", title="样本量不足",
                     failure_mode="样本采集量低于功效所需 12 例",
                     likelihood="medium", impact="high",
                     mitigation="预筛 20 例候选，入组前复核纳入标准",
                     contingency="降级为探索性研究并改写判读标准；转 PI 确认",
                     locator="plan.md L10", addresses_step="ST2")
    json.dump(reg, open(f"{work}/risk_register.json", "w"), ensure_ascii=False, indent=1)
    struct = json.load(open(f"{work}/plan_candidates.json"))
    rv = riskreg.validate_register(reg, struct["candidates"]["steps"])
    json.dump(rv, open(f"{work}/risk_validation.json", "w"), ensure_ascii=False, indent=1)

    req = {"requirements": [{"id": "M1", "name": "培养液", "qty": "1500", "unit": "mL", "locator": "plan.md L15"},
                            {"id": "M2", "name": "离心管", "qty": "200", "unit": "支", "locator": "plan.md L15"}]}
    json.dump(req, open(f"{work}/requirements.json", "w"), ensure_ascii=False, indent=1)
    r = run([sys.executable, f"{HERE}/run.py", "resources", "materials",
             f"{work}/requirements.json", f"{inp}/inventory.json", f"{inp}/catalog.json",
             f"{work}/materials_check.json"])
    mats = json.load(open(f"{work}/materials_check.json"))
    m1 = next(i for i in mats["items"] if i["id"] == "M1")
    if not (m1["status"] == "purchase_needed" and m1["purchase"]["total_price"] == "175"):
        ok = False
        print("E2E materials check wrong:", m1)

    pack = {"materials": mats,
            "budget": resources.check_budget([{"id": "M1", "total_price": "175"}],
                                             {"amount": "600", "currency": "CNY", "locator": "case.json#budget"}),
            "risk_validation": rv}
    json.dump(pack, open(f"{work}/evidence_pack.json", "w"), ensure_ascii=False, indent=1)
    r = run([sys.executable, f"{HERE}/run.py", "verdict", "build",
             f"{work}/checklist.json", f"{work}/evidence_pack.json", f"{work}/verdict.json"])
    verdict = json.load(open(f"{work}/verdict.json"))
    if not (verdict["verdict"] == "conditional" and verdict["counts"]["conditions"] >= 3):
        ok = False
        print("E2E verdict wrong:", json.dumps(verdict, ensure_ascii=False)[:400])

    report = ("# 可行性审查报告（合成示例）\n\n结论：%s\n\n## 条件\n%s\n"
              % (verdict["verdict_label"],
                 "\n".join(f"- {c['condition']}" for c in verdict["conditions"])))
    open(f"{work}/review_report.md", "w", encoding="utf-8").write(report)
    json.dump({"verdict": verdict["verdict"], "conditions": verdict["counts"]["conditions"],
               "unchecked": 0}, open(f"{work}/summary.json", "w"))

    r = run([sys.executable, f"{HERE}/run.py", "emit", "--work", work, "--out", out,
             "--status", "success",
             "--artifact", f"report={work}/review_report.md",
             "--artifact", f"data={work}/checklist.json",
             "--artifact", f"result={work}/verdict.json"])
    if r.returncode != 0:
        ok = False
        print("E2E emit failed:", r.stderr[-400:])
    else:
        res = json.load(open(f"{out}/result.json"))
        ok = ok and res["case_id"] == "demo-feas-case" and res["status"] == "success"
        for key in ("review_report", "checklist", "verdict"):
            if key not in res["output_contract"]:
                ok = False
                print("E2E result.json missing contract key:", key)
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass" +
          (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
