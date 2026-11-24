#!/usr/bin/env python3
"""arkit 冒烟测试：全部模块 --demo + 一次端到端
（合成案例 → probe → extract → audit 预扫描 → 验证台账 → 报告 → emit → result.json）。

演示数据均为合成；包含两种诚实结局：有一条真实问题的稿件，与一份零问题
（no defect found）的干净稿件。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["locate", "findings", "checklist", "stats", "crosscheck", "claims",
           "consistency", "quality", "respond", "norms", "report"]

SYNTH_PAPER = """# Abstract

We studied 42 adults; sleep training improved recall by 18.5%.

# Introduction

Prior work showed that caffeine improves alertness [3]. We hypothesize that sleep
training improves memory consolidation.

# Methods

We recruited n = 42 adults from one campus. The protocol was approved by the
institutional ethics committee (approval no. 2021-034); all participants gave
informed consent.

# Results

After exclusions, n = 40 remained. Recall improved by 18.5% (p = 0.032).

# Discussion

Our results demonstrate that sleep training improves memory consolidation.
The authors declare no conflict of interest.
"""


def run(*args):
    return subprocess.run([sys.executable] + list(args), capture_output=True, text=True)


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"arkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"{m:12s} ERROR {e}")
            failed.append(m)
    # ---- end-to-end synthetic case ----
    tmp = tempfile.mkdtemp(prefix="arkit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    with open(f"{inp}/case.json", "w", encoding="utf-8") as fh:
        json.dump({"case_id": "demo-review-case",
                   "task": "对给定稿件做质量审查，输出带定位与严重度的问题清单",
                   "output_contract": {"report": "md", "result_json": "json",
                                       "ledger": "json"}}, fh)
    with open(f"{inp}/paper.md", "w", encoding="utf-8") as fh:
        fh.write(SYNTH_PAPER)
    work, out = f"{tmp}/work", f"{tmp}/out"
    r1 = run(f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json", "--input", inp,
             "--out", work)
    r2 = run(f"{HERE}/run.py", "extract", "--work", work)
    r3 = run(f"{HERE}/run.py", "audit", "--work", work, "--source", f"{inp}/paper.md")
    ok = all(r.returncode == 0 for r in (r1, r2, r3))
    if not ok:
        print("e2e step failed:", r1.stderr[-400:], r2.stderr[-400:], r3.stderr[-400:])
    # agent-side judgment (deterministic here): enter one real finding + one fake
    from arkit import findings, checklist as clmod, report
    led = findings.load(f"{work}/ledger.json")
    findings.add(led, type="stats", kind="insufficient_evidence", severity="minor",
                 quote="Recall improved by 18.5% (p = 0.032).",
                 locator="§Results ¶2 s1",
                 justification="p 值无置信区间/效应量伴随",
                 suggestion="为 18.5% 的改善补报 95% CI",
                 severity_basis="minor: 不影响主结论的报告完整性缺口")
    findings.add(led, type="fact", kind="error", severity="critical",
                 quote="The placebo arm was completely unblinded.",
                 locator="§Methods ¶1 s9", justification="故意伪造，测试验证器")
    vrep = findings.validate(led, open(f"{inp}/paper.md", encoding="utf-8").read())
    findings.save(led, f"{work}/ledger.json")
    cl = clmod.load(f"{work}/checklist.json")
    clmod.set_status(cl, "stat-report", "issue", finding_ids=["F001"],
                     evidence=[{"quote": "Recall improved by 18.5% (p = 0.032).",
                                "locator": "§Results ¶2 s1"}])
    for it in cl["items"]:
        if it["status"] == "unchecked":
            clmod.set_status(cl, it["id"], "pass", evidence=[],
                             note="demo: 合成稿件上逐项确认无异常")
    clmod.save(cl, f"{work}/checklist.json")
    rep = report.build(led, cl, title="合成示例", case_id="demo-review-case")
    json.dump(rep, open(f"{work}/report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(f"{work}/report.md", "w", encoding="utf-8").write(report.to_markdown(rep))
    ok = ok and vrep["accepted"] == 1 and vrep["rejected"] == 1
    # honest clean-audit path: zero findings must still emit a valid result
    clean_led = findings.new_ledger("clean.md")
    clean = report.build(clean_led, cl, case_id="demo-review-case")
    ok = ok and clean["outcome"] == "no_findings" and clean["status_suggestion"] == "success"
    with open(f"{work}/summary.json", "w", encoding="utf-8") as fh:
        json.dump({"outcome": rep["outcome"], "n_findings": rep["n_findings"],
                   "n_rejected": rep["n_rejected"],
                   "clean_audit_supported": clean["outcome"] == "no_findings"}, fh)
    r4 = run(f"{HERE}/run.py", "emit", "--work", work, "--out", out, "--status",
             rep["status_suggestion"], "--artifact", f"report={work}/report.md",
             "--artifact", f"ledger={work}/ledger.json",
             "--artifact", f"result={work}/report.json")
    ok = ok and r4.returncode == 0
    if ok:
        res = json.load(open(f"{out}/result.json"))
        ok = (res["case_id"] == "demo-review-case" and res["status"] == "success"
              and "report" in res["output_contract"] and "ledger" in res["output_contract"])
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
