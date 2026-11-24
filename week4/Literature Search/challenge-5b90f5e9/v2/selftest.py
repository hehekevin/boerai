#!/usr/bin/env python3
"""lskit 冒烟测试：全部模块 --demo + 一次端到端（probe/extract/emit 用合成案例）。"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["identity", "coverage", "screen", "graph", "iterloop", "increment",
           "filesearch", "patents", "crosslang", "qplan"]

def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"lskit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc: failed.append(m)
        except Exception as e:
            print(f"{m:12s} ERROR {e}"); failed.append(m)
    # end-to-end with a synthetic case
    tmp = tempfile.mkdtemp(prefix="lskit-e2e-")
    inp = os.path.join(tmp, "input"); os.makedirs(inp)
    json.dump({"case_id": "demo-search-case", "task": "find papers on CRISPR T cell screens",
               "output_contract": {"report": "md", "result_json": "json"}}, open(f"{inp}/case.json", "w"))
    open(f"{inp}/seed.txt", "w").write("CRISPR screens in T cells identify regulators of activation.\n\nWe screened 500 genes across donors.")
    env = dict(os.environ)
    r1 = subprocess.run([sys.executable, f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json",
                         "--input", inp, "--out", f"{tmp}/work"], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, f"{HERE}/run.py", "extract", "--work", f"{tmp}/work"],
                        capture_output=True, text=True)
    json.dump({"candidates": 2, "screened": 2}, open(f"{tmp}/work/summary.json", "w"))
    r3 = subprocess.run([sys.executable, f"{HERE}/run.py", "emit", "--work", f"{tmp}/work",
                         "--out", f"{tmp}/out", "--status", "success",
                         "--artifact", f"report={inp}/seed.txt"], capture_output=True, text=True)
    ok = r1.returncode == 0 and r2.returncode == 0 and r3.returncode == 0
    if ok:
        res = json.load(open(f"{tmp}/out/result.json"))
        ok = res["case_id"] == "demo-search-case" and res["status"] == "success" and "report" in res["output_contract"]
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok: failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass" +
          (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
