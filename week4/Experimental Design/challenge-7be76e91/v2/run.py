#!/usr/bin/env python3
"""实验方案设计赛道 Skill 统一入口。

用法（在任意目录）：
  python <skill>/run.py probe --case /input/case.json --input /input --out /app/work
  python <skill>/run.py extract --work /app/work
  python <skill>/run.py review --work /app/work --source <方案文本>
      （确定性预扫描：planparse 结构抽取 + 初始化 12 项六面 checklist + 空风险台账；
        只产候选与空表，判断由 Agent 完成并逐项带定位与证据落盘）
  python <skill>/run.py <edkit模块> ...   （planparse/checklist/resources/plandiff/riskreg/verdict 透传）
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


def cmd_review(a):
    """Deterministic pre-scan over one plan text: structure candidates +
    default six-facet checklist (all unchecked) + empty risk register.
    The engine emits CANDIDATES and EMPTY ledgers only — no judgement."""
    from edkit import planparse, checklist, riskreg
    work = a.work
    os.makedirs(work, exist_ok=True)
    text = open(a.source, encoding="utf-8").read()
    struct = planparse.parse_text(text, os.path.abspath(a.source))
    hk_result.dump_json(os.path.join(work, "plan_candidates.json"), struct)
    cl = checklist.default_checklist()
    checklist.save(cl, os.path.join(work, "checklist.json"))
    reg = riskreg.new_register(os.path.abspath(a.source))
    hk_result.dump_json(os.path.join(work, "risk_register.json"), reg)
    print(f"plan_candidates -> {work}/plan_candidates.json "
          f"(sections={len(struct['sections'])}, params={len(struct['candidates']['parameters'])}, "
          f"steps={len(struct['candidates']['steps'])}, resource_lines={len(struct['candidates']['resources'])}); "
          f"checklist.json ({len(cl['items'])} items, ALL unchecked) + empty risk_register.json. "
          f"Agent must confirm each item with evidence+locator; unchecked stays unchecked.")
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
    if argv and argv[0] not in ("probe", "extract", "review", "emit", "-h", "--help"):
        mod = __import__(f"edkit.{argv[0]}", fromlist=["x"])
        if hasattr(mod, "_demo") and "--demo" in argv[1:]:
            return mod._demo()
        if hasattr(mod, "main"):
            return mod.main(argv[1:])
        import runpy
        runpy.run_module(f"edkit.{argv[0]}", run_name="__main__")
        return 0
    ap = argparse.ArgumentParser(prog="edkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("--case", default="/input/case.json")
    p.add_argument("--input", default="/input"); p.add_argument("--out", default="work")
    p.set_defaults(func=cmd_probe)
    p = sub.add_parser("extract"); p.add_argument("--work", default="work")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("review"); p.add_argument("--work", default="work")
    p.add_argument("--source", required=True)
    p.set_defaults(func=cmd_review)
    p = sub.add_parser("emit"); p.add_argument("--work", default="work")
    p.add_argument("--out", default="/app/output"); p.add_argument("--status", default="partial")
    p.add_argument("--artifact", action="append"); p.add_argument("--summary-json", default="")
    p.set_defaults(func=cmd_emit)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
