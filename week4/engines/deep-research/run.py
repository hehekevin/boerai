#!/usr/bin/env python3
"""深度研究与文献综述赛道 Skill 统一入口。

用法（在任意目录）：
  python <skill>/run.py probe --case /input/case.json --input /input --out /app/work
  python <skill>/run.py extract --work /app/work
  python <skill>/run.py <drkit 模块名> ...   （透传到 python -m drkit.<模块>，见 SKILL.md）
  python <skill>/run.py emit --work /app/work --out /app/output --status success \
      --artifact key=path [--artifact ...] --summary-json work/summary.json
"""
import os
import subprocess
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
    here = os.path.dirname(os.path.abspath(__file__))
    # drkit module commands bypass argparse's fixed subparser choices
    if argv and argv[0] not in ("probe", "extract", "emit", "-h", "--help"):
        mod = os.path.join(here, "drkit", f"{argv[0]}.py")
        if os.path.exists(mod):
            return subprocess.run([sys.executable, mod] + argv[1:],
                                  env={**os.environ, "PYTHONPATH": here}).returncode
        print(f"unknown command '{argv[0]}'; drkit modules: evidence synthesis gaps "
              f"trendstat qplan iterloop identity screen")
        return 2
    ap = argparse.ArgumentParser(prog="drkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("--case", default="/input/case.json")
    p.add_argument("--input", default="/input"); p.add_argument("--out", default="work")
    p.set_defaults(func=cmd_probe)
    p = sub.add_parser("extract"); p.add_argument("--work", default="work")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("emit"); p.add_argument("--work", default="work")
    p.add_argument("--out", default="/app/output"); p.add_argument("--status", default="partial")
    p.add_argument("--artifact", action="append"); p.add_argument("--summary-json", default="")
    p.set_defaults(func=cmd_emit)
    args, rest = ap.parse_known_args(argv)
    if args.cmd in ("probe", "extract", "emit"):
        return args.func(args)
    # fall through to drkit module CLIs: run.py evidence validate m.json out.json
    here = os.path.dirname(os.path.abspath(__file__))
    mod = os.path.join(here, "drkit", f"{args.cmd}.py")
    if not os.path.exists(mod):
        print(f"unknown command '{args.cmd}'; drkit modules: evidence synthesis gaps "
              f"trendstat qplan iterloop identity screen")
        return 2
    return subprocess.run([sys.executable, mod] + rest,
                          env={**os.environ, "PYTHONPATH": here}).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
