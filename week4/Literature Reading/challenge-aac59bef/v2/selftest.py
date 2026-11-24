#!/usr/bin/env python3
"""lrkit 冒烟测试：全部模块 --demo + 一次端到端合成案例
（probe → extract → blocks → 赛道命令(qa 校验) → emit → result.json）。"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lrkit import MODULES  # noqa: E402


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"lrkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:10s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"{m:10s} ERROR {e}")
            failed.append(m)
    # ---------------- end-to-end with a synthetic case ----------------
    tmp = tempfile.mkdtemp(prefix="lrkit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    json.dump({"case_id": "demo-reading-case",
               "task": "read the synthetic paper and answer Q1 with evidence",
               "output_contract": {"report": "md", "result_json": "json"}},
              open(f"{inp}/case.json", "w", encoding="utf-8"))
    open(f"{inp}/paper.md", "w", encoding="utf-8").write(
        "Synthetic demo paper.\n\nThe alloy reaches 520 MPa yield strength at 25 C.\n\n"
        "Fatigue life was not measured in this synthetic study.\n")
    r1 = subprocess.run([sys.executable, f"{HERE}/run.py", "probe", "--case",
                         f"{inp}/case.json", "--input", inp, "--out", f"{tmp}/work"],
                        capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, f"{HERE}/run.py", "extract", "--work", f"{tmp}/work"],
                        capture_output=True, text=True)
    r2b = subprocess.run([sys.executable, f"{HERE}/run.py", "blocks", "--work", f"{tmp}/work"],
                         capture_output=True, text=True)
    # track command: 构造一条问答并用 lrkit.qa 校验
    blocks = json.load(open(f"{tmp}/work/blocks.json"))["blocks"]
    from lrkit import qa
    ans = [qa.build_answer_item(
        "Q1", "屈服强度 520 MPa（25 C）。", "answered",
        claims=[{"claim_id": "Q1-c1", "text": "yield strength = 520 MPa",
                 "kind": "reported",
                 "evidence": [{"source": "S1", "loc": "block.2",
                               "quote": "reaches 520 MPa yield strength"}]}],
        conditions=["25 C"])]
    qa_rep = qa.validate_answers(["Q1"], ans, blocks)
    json.dump({"answers": ans, "qa_validation": qa_rep},
              open(f"{tmp}/work/answers.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"questions": 1, "answered": 1, "qa_ok": qa_rep["ok"]},
              open(f"{tmp}/work/summary.json", "w", encoding="utf-8"))
    r3 = subprocess.run([sys.executable, f"{HERE}/run.py", "emit", "--work", f"{tmp}/work",
                         "--out", f"{tmp}/out", "--status", "success",
                         "--artifact", f"report={tmp}/work/answers.json"],
                        capture_output=True, text=True)
    ok = all(r.returncode == 0 for r in (r1, r2, r2b, r3)) and qa_rep["ok"]
    if ok:
        res = json.load(open(f"{tmp}/out/result.json"))
        ok = (res["case_id"] == "demo-reading-case" and res["status"] == "success"
              and "report" in res["output_contract"])
    if not ok:
        for name, r in (("probe", r1), ("extract", r2), ("blocks", r2b), ("emit", r3)):
            if r.returncode != 0:
                print(f"--- {name} stderr ---\n{r.stderr[-800:]}")
    print(f"{'e2e':10s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
