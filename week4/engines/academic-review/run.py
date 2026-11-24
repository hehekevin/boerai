#!/usr/bin/env python3
"""学术审查赛道 Skill 统一入口。

用法（在任意目录）：
  python <skill>/run.py probe --case /input/case.json --input /input --out /app/work
  python <skill>/run.py extract --work /app/work
  python <skill>/run.py audit --work /app/work --source <text> [--checklist cl.json]
      （确定性预扫描：locate/stats/consistency/norms 观察 + 初始化 checklist 与空台账）
  python <skill>/run.py <模块子命令> ...   （python -m arkit.<模块> 透传，见各模块 usage）
  python <skill>/run.py emit --work /app/work --out /app/output --status success \
      --artifact key=path [--artifact ...] --summary-json work/summary.json
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hk import probe as hk_probe, extract as hk_extract, result as hk_result  # noqa: E402


def cmd_probe(a):
    os.makedirs(a.out, exist_ok=True)
    info = hk_probe.probe(a.case, a.input)
    hk_result.dump_json(os.path.join(a.out, "inputs.json"), info)
    print(hk_probe.brief(info))
    return 0


def cmd_extract(a):
    work = a.work
    inputs = hk_result.load_json(os.path.join(work, "inputs.json"), {})
    files, seen = [], set()
    for f in inputs.get("files") or []:
        if f["path"] in seen:
            continue
        seen.add(f["path"])
        files.append(f)
    rep = hk_extract.extract_all(files, work)
    hk_result.dump_json(os.path.join(work, "materials.json"), rep["summary"])
    hk_result.dump_json(os.path.join(work, "materials_full.json"),
                        {"materials": [{k: v for k, v in m.items() if k != "data"}
                                       for m in rep["materials"]]})
    print(f"extracted {rep['summary']['n_files']} files -> {rep['text_dir']}")
    return 0


def cmd_audit(a):
    """Deterministic pre-scan over one manuscript text: observations + empty ledger
    + default checklist. The agent then judges; nothing here is a verdict."""
    from arkit import stats, consistency, norms, findings, checklist
    work = a.work
    os.makedirs(work, exist_ok=True)
    text = open(a.source, encoding="utf-8").read()
    pre = {"source": os.path.abspath(a.source),
           "stats": stats.detect(text),
           "consistency": consistency.observe(text),
           "norms": norms.scan(text)}
    hk_result.dump_json(os.path.join(work, "prescan.json"),
                        {"source": pre["source"],
                         "n_claim_sentences": pre["stats"]["n_claim_sentences"],
                         "stats_observations": len(pre["stats"]["observations"]),
                         "quantity_conflicts": len(pre["consistency"]["quantity_conflicts"]),
                         "missing_declarations": pre["norms"]["missing_declarations"]})
    hk_result.dump_json(os.path.join(work, "prescan_full.json"), pre)
    led = findings.new_ledger(os.path.abspath(a.source))
    findings.save(led, os.path.join(work, "ledger.json"))
    cl = checklist.default_checklist()
    if a.checklist and os.path.exists(a.checklist):
        cl = checklist.load(a.checklist)
    checklist.save(cl, os.path.join(work, "checklist.json"))
    print(f"prescan -> {work}/prescan_full.json; empty ledger + checklist initialized "
          f"({len(cl['items'])} items). Engine emitted OBSERVATIONS only; "
          f"agent must confirm each finding with quote+locator+justification.")
    return 0


def cmd_emit(a):
    work, outdir = a.work, a.out
    os.makedirs(outdir, exist_ok=True)
    inputs = hk_result.load_json(os.path.join(work, "inputs.json"), {})
    case_id = str(inputs.get("case_id") or "")
    contract = inputs.get("output_contract") or {}
    artifacts = {}
    for kv in a.artifact or []:
        if "=" in kv:
            k, p = kv.split("=", 1)
            artifacts[k] = {"path": p, "bytes": os.path.getsize(p) if os.path.exists(p) else None}
    summary = hk_result.load_json(a.summary_json or os.path.join(work, "summary.json"), {}) or {}
    unc = hk_result.load_json(os.path.join(work, "uncertainty.json"), []) or []
    changes = hk_result.load_json(os.path.join(work, "changes.json"), []) or []
    sources = [{"id": f"S{i}", "path": f["path"], "sha256": f.get("sha256")}
               for i, f in enumerate(inputs.get("files") or [], start=1)
               if not f["path"].endswith("case.json")]
    import sys as _s
    result = hk_result.build_result(case_id, a.status, artifacts, contract, summary,
                                    sources, unc, changes,
                                    {"python": _s.version.split()[0], "cwd": os.getcwd()})
    rp = os.path.join(outdir, "result.json")
    hk_result.write_result(rp, result)
    print(f"result.json -> {rp} (status={a.status}, artifacts={len(artifacts)})")
    return 0


def main(argv):
    import argparse
    # module passthrough: run.py <arkit-module> ... -> python -m arkit.<module>
    if argv and argv[0] not in ("probe", "extract", "audit", "emit", "-h", "--help"):
        mod = __import__(f"arkit.{argv[0]}", fromlist=["x"])
        sys.argv = [f"arkit.{argv[0]}"] + argv[1:]
        if hasattr(mod, "_demo") and "--demo" in argv[1:]:
            return mod._demo()
        if hasattr(mod, "main"):
            return mod.main(argv[1:])
        import runpy
        runpy.run_module(f"arkit.{argv[0]}", run_name="__main__")
        return 0
    ap = argparse.ArgumentParser(prog="arkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("--case", default="/input/case.json")
    p.add_argument("--input", default="/input"); p.add_argument("--out", default="work")
    p.set_defaults(func=cmd_probe)
    p = sub.add_parser("extract"); p.add_argument("--work", default="work")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("audit"); p.add_argument("--work", default="work")
    p.add_argument("--source", required=True); p.add_argument("--checklist", default="")
    p.set_defaults(func=cmd_audit)
    p = sub.add_parser("emit"); p.add_argument("--work", default="work")
    p.add_argument("--out", default="/app/output"); p.add_argument("--status", default="partial")
    p.add_argument("--artifact", action="append"); p.add_argument("--summary-json", default="")
    p.set_defaults(func=cmd_emit)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
