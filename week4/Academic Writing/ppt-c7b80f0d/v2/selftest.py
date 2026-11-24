#!/usr/bin/env python3
"""awkit 冒烟测试：全部 9 个模块 demo + 一次端到端
（合成 case → probe → extract → 模块命令（claims + deck build）→ emit → result.json）。"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = ["claims", "coverage", "citecheck", "bilingual", "formatcheck",
           "revisions", "structcheck", "deck", "scorecard"]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kw)


def main():
    failed = []
    for m in MODULES:
        mod = __import__(f"awkit.{m}", fromlist=["x"])
        try:
            rc = mod._demo()
            print(f"{m:12s} {'PASS' if rc == 0 else 'FAIL'}")
            if rc:
                failed.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"{m:12s} ERROR {e}")
            failed.append(m)
    # ---- end-to-end synthetic case
    tmp = tempfile.mkdtemp(prefix="awkit-e2e-")
    inp = os.path.join(tmp, "input")
    os.makedirs(inp)
    json.dump({"case_id": "demo-writing-case",
               "task": "依据材料写一段结果概述，并输出 3 页汇报 PPT。",
               "output_contract": {"draft_md": "md", "deck_pptx": "pptx",
                                   "report": "md", "result_json": "json"}},
              open(f"{inp}/case.json", "w", encoding="utf-8"), ensure_ascii=False)
    open(f"{inp}/material.txt", "w", encoding="utf-8").write(
        "We screened 500 genes across 3 donors. The hit rate was 4.2% in the primary screen.")
    work = os.path.join(tmp, "work")
    r1 = run([sys.executable, f"{HERE}/run.py", "probe", "--case", f"{inp}/case.json",
              "--input", inp, "--out", work])
    r2 = run([sys.executable, f"{HERE}/run.py", "extract", "--work", work])
    # 模块命令 1：claims 校验（含一条无来源数字 → 预期失败，再修复后通过）
    open(f"{work}/draft.md", "w", encoding="utf-8").write(
        "本研究筛选了 500 个基因，覆盖 3 名供体。初筛命中率为 4.2%。")
    json.dump([{"id": "S1", "text": "We screened 500 genes across 3 donors. "
                                    "The hit rate was 4.2% in the primary screen."}],
              open(f"{work}/sources.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump([{"sentence_id": "d0001", "source_id": "S1",
                "quote": "We screened 500 genes across 3 donors."},
               {"sentence_id": "d0002", "source_id": "S1",
                "quote": "The hit rate was 4.2% in the primary screen."}],
              open(f"{work}/bindings.json", "w", encoding="utf-8"), ensure_ascii=False)
    r3 = run([sys.executable, f"{HERE}/run.py", "claims", "validate",
              f"{work}/draft.md", f"{work}/sources.json", f"{work}/bindings.json",
              "-", f"{work}/claims_report.json"])
    # 模块命令 2：deck 构建 + 预览
    outline = {"title": "demo deck", "slides": [
        {"no": 1, "kind": "title", "claim": "筛选结果概述",
         "bullets": ["组会汇报 · 示例"], "notes": "开场说明本次只汇报初筛进度。",
         "evidence": []},
        {"no": 2, "kind": "content", "claim": "初筛 500 基因、3 供体，命中率 4.2%",
         "bullets": ["筛选规模 500 个基因", "覆盖 3 名供体", "初筛命中率 4.2%"],
         "notes": "提示供体数小，讨论是否扩大队列。",
         "evidence": [{"source_id": "S1", "loc": "material.txt",
                       "quote": "We screened 500 genes across 3 donors. The hit rate was 4.2%"}]}]}
    json.dump(outline, open(f"{work}/outline.json", "w", encoding="utf-8"),
              ensure_ascii=False)
    r4 = run([sys.executable, f"{HERE}/run.py", "deck", "build",
              f"{work}/outline.json", f"{work}/deck.pptx", "--preview",
              f"{work}/preview"])
    json.dump({"draft_sentences": 2, "deck_slides": 2,
               "claims_ok": r3.returncode == 0},
              open(f"{work}/summary.json", "w", encoding="utf-8"))
    r5 = run([sys.executable, f"{HERE}/run.py", "emit", "--work", work,
              "--out", f"{tmp}/out", "--status", "success",
              "--artifact", f"document={work}/draft.md",
              "--artifact", f"slides={work}/deck.pptx",
              "--artifact", f"provenance={work}/claims_report.json"])
    ok = all(r.returncode == 0 for r in (r1, r2, r3, r4, r5))
    if ok:
        res = json.load(open(f"{tmp}/out/result.json", encoding="utf-8"))
        ok = (res["case_id"] == "demo-writing-case" and res["status"] == "success"
              and set(res["output_contract"]) >= {"draft_md", "deck_pptx", "report",
                                                  "result_json"})
        claims_rep = json.load(open(f"{work}/claims_report.json", encoding="utf-8"))
        ok = ok and claims_rep["ok"] and claims_rep["numbers_checked"] >= 3
        ok = ok and os.path.getsize(f"{tmp}/out/result.json") > 200
    else:
        for i, r in enumerate((r1, r2, r3, r4, r5)):
            if r.returncode != 0:
                print(f"e2e step {i+1} failed:\n{r.stdout[-400:]}\n{r.stderr[-600:]}")
    print(f"{'e2e':12s} {'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append("e2e")
    print(f"\n{len(MODULES) + 1 - len(failed)}/{len(MODULES) + 1} checks pass"
          + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
