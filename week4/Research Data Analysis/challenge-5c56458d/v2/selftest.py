#!/usr/bin/env python3
"""dakit 冒烟测试：7 个模块 demo（含教科书数值断言）+ 一次端到端。

e2e：合成 CSV（带缺失/异常/重复）→ probe → extract → tables → profile →
clean（规则文件）→ stats（Welch t + 假设检查）→ charts → report 回填 → emit →
result.json。全部合成数据，非正式案例结果。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["profile", "align", "clean", "stats", "charts", "dbrun", "report"]


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def e2e() -> bool:
    tmp = tempfile.mkdtemp(prefix="dakit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    # —— 合成案例：两组测量值，含 1 缺失、1 异常值、1 重复记录 ——
    json.dump({"case_id": "demo-data-case",
               "task": "比较 A/B 两组的测量值是否有差异，出报告",
               "output_contract": {"report": "md", "stats_json": "json",
                                   "cleaned_csv": "csv", "result_json": "json"}},
              open(f"{inp}/case.json", "w", encoding="utf-8"), ensure_ascii=False)
    rows = ["id,group,value (mg)"]
    vals_a = [10.1, 9.8, 10.5, 10.2, 9.9, 10.3, 10.0, 10.4]
    vals_b = [11.2, 11.5, 11.0, 11.8, 11.3, 11.6, 11.1, 55.0]  # 55.0 = 注入异常
    for i, v in enumerate(vals_a):
        rows.append(f"A{i},A,{v}")
    for i, v in enumerate(vals_b):
        rows.append(f"B{i},B,{v if v is not None else ''}")
    rows.append("A3,A,10.2")   # 重复记录（与 A3 同 id）
    rows.append("B8,B,")       # 缺失（新 id，不与既有记录冲突）
    open(f"{inp}/measurements.csv", "w", encoding="utf-8").write("\n".join(rows) + "\n")
    work, out = f"{tmp}/work", f"{tmp}/out"

    r = _run([sys.executable, f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json",
              "--input", inp, "--out", work])
    assert r.returncode == 0, r.stderr
    r = _run([sys.executable, f"{HERE}/run.py", "extract", "--work", work])
    assert r.returncode == 0, r.stderr
    r = _run([sys.executable, f"{HERE}/run.py", "tables", "--work", work])
    assert r.returncode == 0, r.stderr

    tables = json.load(open(f"{work}/tables.json", encoding="utf-8"))
    assert len(tables) == 1 and tables[0]["units_hint"] == {"value (mg)": "mg"}

    from dakit import profile, clean, stats, charts, report
    # profile
    prof = profile.profile_table(tables[0]["name"], tables[0]["header"], tables[0]["rows"])
    assert prof["columns"]["value (mg)"]["type"] == "float"  # 空串已被 extract 归一为 None
    assert prof["columns"]["value (mg)"]["n_missing"] == 1
    json.dump({"profiles": [prof]}, open(f"{work}/profile.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # clean：规则文件是数据
    rules = {"rules": [
        {"id": "dup1", "type": "duplicate", "keys": ["id"], "keep": "first"},
        {"id": "mis1", "type": "missing", "column": "value (mg)", "strategy": "drop_rows"},
        {"id": "out1", "type": "outlier", "column": "value (mg)", "method": "iqr",
         "strategy": "drop"},
    ]}
    json.dump(rules, open(f"{work}/rules.json", "w", encoding="utf-8"), ensure_ascii=False)
    rep = clean.run_rules(tables[0]["rows"], rules["rules"])
    assert rep["ledger"][0]["after_n"] == 17  # 18 - 1 dup
    assert rep["ledger"][1]["after_n"] == 16  # -1 missing
    assert rep["ledger"][2]["after_n"] == 15  # -1 outlier (55.0)
    assert rep["ledger"][2]["affected_row_ids"] == [15]  # B7=55.0 的 _row_id
    json.dump({"ledger": rep["ledger"]}, open(f"{work}/clean_ledger.json", "w",
                                              encoding="utf-8"), ensure_ascii=False, indent=1)
    import csv as _csv
    with open(f"{work}/cleaned.csv", "w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=["id", "group", "value (mg)"])
        w.writeheader()
        for row in rep["rows"]:
            w.writerow({k: row[k] for k in ("id", "group", "value (mg)")})
    # stats
    ga = [float(r["value (mg)"]) for r in rep["rows"] if r["group"] == "A"]
    gb = [float(r["value (mg)"]) for r in rep["rows"] if r["group"] == "B"]
    assert len(ga) == 8 and len(gb) == 7
    spec = {"tests": [{"kind": "welch_t", "x": ga, "y": gb},
                      {"kind": "describe", "values": ga, "label": "A"},
                      {"kind": "describe", "values": gb, "label": "B"}],
            "assumptions": {"groups": {"A": ga, "B": gb}, "n_tests_planned": 1}}
    json.dump(spec, open(f"{work}/stats_spec.json", "w", encoding="utf-8"))
    r = _run([sys.executable, "-m", "dakit.stats", f"{work}/stats_spec.json",
              f"{work}/stats.json"], cwd=HERE)
    assert r.returncode == 0, r.stderr
    st = json.load(open(f"{work}/stats.json", encoding="utf-8"))
    w = st["results"][0]
    assert w["test"] == "welch_two_sample_t" and w["n1"] == 8 and w["n2"] == 7
    assert w["p_two_sided"] < 0.001  # 两组相差 ~1.2mg，远大于组内噪声
    assert "assumptions" in st and st["assumptions"]["variance"]["test"] == "levene_brown_forsythe"
    # charts
    sel = charts.select_chart({"intent": "comparison", "x_type": "categorical",
                               "y_type": "numeric", "n_categories": 2})
    assert sel["chart"] == "bar"
    json.dump(sel, open(f"{work}/chart_spec.json", "w", encoding="utf-8"), ensure_ascii=False)
    # report 回填（数字只能来自 stats.json）
    tpl = ("# 合成示例报告\nA 组 n={{results[1].n}}，均值 {{results[1].mean|round:3}} mg；"
           "B 组 n={{results[2].n}}，均值 {{results[2].mean|round:3}} mg。\n"
           "Welch t={{results[0].t|round:3}}，df={{results[0].df|round:1}}，"
           "p={{results[0].p_two_sided}}。清洗：18 行 → 15 行（见 clean_ledger.json）。\n")
    open(f"{work}/report.tpl.md", "w", encoding="utf-8").write(tpl)
    r = _run([sys.executable, "-m", "dakit.report", f"{work}/report.tpl.md",
              f"{work}/stats.json", f"{work}/report.md", f"{work}/report_mapping.json"],
             cwd=HERE)
    assert r.returncode == 0, r.stderr
    mapping = json.load(open(f"{work}/report_mapping.json", encoding="utf-8"))
    assert mapping["validation"]["ok"]
    # emit
    json.dump({"n_raw": 18, "n_clean": 15, "welch_p": w["p_two_sided"],
               "pipeline": "probe->extract->tables->profile->clean->stats->charts->report->emit"},
              open(f"{work}/summary.json", "w", encoding="utf-8"), ensure_ascii=False)
    r = _run([sys.executable, f"{HERE}/run.py", "emit", "--work", work, "--out", out,
              "--status", "success",
              "--artifact", f"report={work}/report.md",
              "--artifact", f"stats_json={work}/stats.json",
              "--artifact", f"cleaned_csv={work}/cleaned.csv",
              "--artifact", f"data={work}/clean_ledger.json"])
    assert r.returncode == 0, r.stderr
    res = json.load(open(f"{out}/result.json", encoding="utf-8"))
    ok = (res["case_id"] == "demo-data-case" and res["status"] == "success"
          and set(res["output_contract"]) == {"report", "stats_json", "cleaned_csv", "result_json"})
    if ok:
        print(f"  e2e detail: 18→15 rows, Welch t={w['t']}, p={w['p_two_sided']}, "
              f"report backfilled {len(mapping['mapping'])} values")
    return ok


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"dakit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:10s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:
            print(f"{m:10s} ERROR {e}")
            failed.append(m)
    try:
        ok = e2e()
        print(f"{'e2e':10s} {'PASS' if ok else 'FAIL'}")
        if not ok:
            failed.append("e2e")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"{'e2e':10s} ERROR {e}")
        failed.append("e2e")
    total = len(MODULES) + 1
    print(f"\n{total - len(failed)}/{total} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
