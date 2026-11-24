#!/usr/bin/env python3
"""shared: defensive case.json inspector for all weekly-skill challenges.

Prints case_id, task fields, output_contract keys, materials list, top-level
keys and anomalies. Never raises. Usage:
  python inspect_case.py /input/case.json
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 2:
        print("usage: inspect_case.py /input/case.json"); return 2
    path = sys.argv[1]
    report = {"path": path, "exists": os.path.exists(path), "anomalies": []}
    if not report["exists"]:
        report["anomalies"].append("case.json not found at given path")
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    try:
        case = json.load(open(path, encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        report["anomalies"].append("invalid JSON: %s" % e)
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    if not isinstance(case, dict):
        report["anomalies"].append("top level is %s" % type(case).__name__)
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    report["top_level_keys"] = sorted(case.keys())
    for k in ("case_id", "output_contract", "materials", "task", "artifacts", "environment"):
        v = case.get(k)
        if isinstance(v, dict):
            report[k] = {"keys": sorted(v.keys())}
        elif isinstance(v, list):
            report[k] = {"len": len(v), "sample": [str(x)[:100] for x in v[:6]]}
        elif v is not None:
            report[k] = str(v)[:200]
    # walk for materials-like lists anywhere
    def walk(o, trail=""):
        hits = []
        if isinstance(o, dict):
            for k, vv in o.items():
                t = "%s.%s" % (trail, k) if trail else k
                if k.lower() in {"materials", "files", "artifacts", "resources"} and isinstance(vv, list):
                    hits.append((t, [str(x)[:90] for x in vv[:8]]))
                hits.extend(walk(vv, t))
        elif isinstance(o, list):
            for i, vv in enumerate(o[:30]):
                hits.extend(walk(vv, "%s[%d]" % (trail, i)))
        return hits
    report["material_trails"] = walk(case)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
