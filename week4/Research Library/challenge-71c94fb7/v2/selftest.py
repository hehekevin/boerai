#!/usr/bin/env python3
"""rlkit 冒烟测试：全部模块 --demo + 一次端到端（合成案例 probe → extract →
模块命令 → emit → result.json）。所有数据为接口演示而构造，非正式案例结果。"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["identity", "normalize", "metarepair", "tags", "versions", "filelib", "htmlsnap",
           "sqlite_ops", "ledger", "soffice_ops", "kb"]


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"rlkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:
            print(f"{m:12s} ERROR {e}")
            failed.append(m)

    # end-to-end with a synthetic case
    tmp = tempfile.mkdtemp(prefix="rlkit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    json.dump({"case_id": "demo-library-case",
               "task": "dedupe two bibliographic records and report the merge audit",
               "output_contract": {"report": "md", "result_json": "json"}},
              open(f"{inp}/case.json", "w"))
    recs = {"records": [
        {"title": "Deep Learning for Proteins", "authors": ["Smith, John"], "year": 2021,
         "doi": "10.1000/xyz.1", "source_db": "ris"},
        {"title": "Deep learning for proteins.", "authors": "J Smith", "year": 2021,
         "doi": "https://doi.org/10.1000/xyz.1", "source_db": "crossref"}]}
    json.dump(recs, open(f"{inp}/records.json", "w"))
    open(f"{inp}/notes.txt", "w").write("Protein function prediction with deep learning.\n\n"
                                        "Two records describe the same paper.")

    env = dict(os.environ)
    steps = [
        [sys.executable, f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json",
         "--input", inp, "--out", f"{tmp}/work"],
        [sys.executable, f"{HERE}/run.py", "extract", "--work", f"{tmp}/work"],
        [sys.executable, "-m", "rlkit.identity", f"{inp}/records.json", f"{tmp}/work/dedupe.json"],
    ]
    ok = True
    for cmd in steps:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, env=env)
        if r.returncode != 0:
            ok = False
            print("E2E step failed:", cmd, r.stdout[-400:], r.stderr[-400:])
            break
    if ok:
        dd = json.load(open(f"{tmp}/work/dedupe.json"))
        ok = dd["audit"]["output"] == 1 and dd["audit"]["merges"][0]["rule"] == "doi_exact"
    if ok:
        json.dump({"deduped": dd["audit"]["output"], "merges": len(dd["audit"]["merges"])},
                  open(f"{tmp}/work/summary.json", "w"))
        r = subprocess.run([sys.executable, f"{HERE}/run.py", "emit", "--work", f"{tmp}/work",
                            "--out", f"{tmp}/out", "--status", "success",
                            "--artifact", f"data={tmp}/work/dedupe.json"],
                           capture_output=True, text=True)
        ok = r.returncode == 0
    if ok:
        res = json.load(open(f"{tmp}/out/result.json"))
        ok = (res["case_id"] == "demo-library-case" and res["status"] == "success"
              and "report" in res["output_contract"] and res["sources"])
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
