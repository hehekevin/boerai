#!/usr/bin/env python3
"""drkit 冒烟测试：全部模块 --demo + 一次端到端（合成案例 probe → extract →
drkit 模块命令 → emit → result.json）。所有数据为合成演示数据，非正式案例结果。"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["identity", "qplan", "iterloop", "screen",
           "evidence", "synthesis", "gaps", "trendstat"]


def e2e():
    tmp = tempfile.mkdtemp(prefix="drkit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    work = os.path.join(tmp, "work")
    json.dump({"case_id": "demo-dr-case",
               "task": "围绕 X 对 Y 的作用写一份带回链证据的小型综述",
               "output_contract": {"report": "md", "evidence_matrix": "json",
                                   "result_json": "json"}},
              open(f"{inp}/case.json", "w"))
    open(f"{inp}/paperA.txt", "w").write(
        "Paper A. p.3 table 2: X increased Y by 40% (p<0.01) in vivo, n=120.\n")
    open(f"{inp}/paperB.txt", "w").write(
        "Paper B. p.5: no effect of X on Y was observed in vitro at low dose.\n")

    def run(*argv):
        return subprocess.run([sys.executable, f"{HERE}/run.py", *argv],
                              capture_output=True, text=True)

    r1 = run("probe", "--case", f"{inp}/case.json", "--input", inp, "--out", work)
    r2 = run("extract", "--work", work)
    # 模块命令：拆解校验 → 证据矩阵校验 → 综合审计
    plan = {"question": "X 对 Y 的作用？",
            "subquestions": [{"id": "Q1", "text": "X 是否影响 Y",
                              "searchable_terms": ["X", "Y"], "depends_on": [],
                              "evidence_required": 1},
                             {"id": "Q2", "text": "剂量条件", "searchable_terms": ["X dose"],
                              "depends_on": ["Q1"], "evidence_required": 1}]}
    json.dump(plan, open(f"{work}/plan.json", "w"))
    matrix = {"sources": [{"id": "S1", "title": "Paper A"}, {"id": "S2", "title": "Paper B"}],
              "claims": [{"id": "C1", "text": "X 在体内显著提高 Y", "subq_id": "Q1",
                          "supports": [{"source_id": "S1",
                                        "quote": "X increased Y by 40% (p<0.01)",
                                        "locator": "paperA.txt p.3 table 2"}]},
                         {"id": "C2", "text": "低剂量体外未观察到效应", "subq_id": "Q2",
                          "supports": [{"source_id": "S2",
                                        "quote": "no effect of X on Y was observed",
                                        "locator": "paperB.txt p.5"}]}],
              "conflicts": [{"id": "K1", "claim_a": "C1", "claim_b": "C2", "topic": "X->Y",
                             "adjudication": {"comparison": "体内 n=120 与体外低剂量体系不同，"
                                              "结论各自有界",
                                              "resolution": "both_bounded",
                                              "basis": "模型与剂量不同"}}]}
    json.dump(matrix, open(f"{work}/matrix.json", "w"))
    syn = {"conclusions": [
        {"id": "N1", "sentence": "X 在体内模型中显著提高 Y。", "class": "fact",
         "subq_id": "Q1", "claim_ids": ["C1"]},
        {"id": "N2", "sentence": "X 的效应可能依赖模型与剂量。", "class": "inference",
         "subq_id": "Q2", "claim_ids": ["C1", "C2"],
         "basis": "两项研究模型与剂量不同且结论相反，提示效应有条件"},
        {"id": "N3", "sentence": "人群中是否成立无法确定。", "class": "undetermined",
         "subq_id": "Q1", "claim_ids": [],
         "basis": "材料中无人群研究记录"}],
        "gaps": []}
    json.dump(syn, open(f"{work}/synthesis.json", "w"))
    r3 = run("qplan", "validate", f"{work}/plan.json", f"{work}/plan_check.json")
    r4 = run("evidence", "validate", f"{work}/matrix.json", f"{work}/matrix_check.json")
    r5 = run("evidence", "conflicts", f"{work}/matrix.json", f"{work}/conflict_check.json")
    r6 = run("synthesis", "audit", f"{work}/synthesis.json", f"{work}/matrix.json",
             f"{work}/synthesis_audit.json", f"{work}/plan.json")
    json.dump({"subquestions": 2, "claims": 2, "conclusions": 3, "conflicts_adjudicated": 1},
              open(f"{work}/summary.json", "w"))
    json.dump(["人群层面证据缺失，如实标注为无法确定"], open(f"{work}/uncertainty.json", "w"))
    open(f"{work}/report.md", "w").write("# 演示综述（合成数据）\nX 在体内提高 Y [C1]；体外低剂量无效 [C2]。\n")
    r7 = run("emit", "--work", work, "--out", f"{tmp}/out", "--status", "success",
             "--artifact", f"report={work}/report.md",
             "--artifact", f"evidence_matrix={work}/matrix.json")
    steps = [r1, r2, r3, r4, r5, r6, r7]
    if any(r.returncode != 0 for r in steps):
        for i, r in enumerate(steps):
            if r.returncode != 0:
                print(f"step {i} failed:\n{r.stdout}\n{r.stderr}")
        return False
    checks = []
    checks.append(json.load(open(f"{work}/plan_check.json"))["ok"])
    checks.append(json.load(open(f"{work}/matrix_check.json"))["ok"])
    checks.append(json.load(open(f"{work}/conflict_check.json"))["ok"])
    aud = json.load(open(f"{work}/synthesis_audit.json"))
    checks.append(aud["ok"] and aud["coverage"]["complete"])
    res = json.load(open(f"{tmp}/out/result.json"))
    checks.append(res["case_id"] == "demo-dr-case" and res["status"] == "success"
                  and "evidence_matrix" in res["output_contract"]
                  and "report" in res["output_contract"])
    return all(checks)


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"drkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"{m:12s} ERROR {e}")
            failed.append(m)
    ok = e2e()
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
