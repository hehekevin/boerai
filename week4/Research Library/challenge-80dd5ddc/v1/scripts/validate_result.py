#!/usr/bin/env python3
"""shared: generic result.json delivery validator.

Checks: case_id present (+ matches case.json when available), output_contract
fields merged, honest-status block (status/gaps/anomalies), coverage keywords
per category present in the manuscript OR declared in result.coverage.
Usage:
  python validate_result.py --case /input/case.json --result /app/output/result.json \
      --manuscript /app/output/manuscript.md --require "类别1关键词正则|类别2正则|..." --names "名1,名2,..."
--require/--names are parallel lists (| separates keywords per category).
Exit 0 PASS / 1 FAIL.
"""
import argparse
import json
import os
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case"); ap.add_argument("--result", required=True)
    ap.add_argument("--manuscript"); ap.add_argument("--require")
    ap.add_argument("--names")
    a = ap.parse_args()
    problems, warnings = [], []

    case = {}
    if a.case and os.path.exists(a.case):
        try:
            case = json.load(open(a.case, encoding="utf-8", errors="replace"))
            if not isinstance(case, dict): case = {}
        except json.JSONDecodeError as e:
            warnings.append("case.json unreadable (%s)" % e)
    else:
        warnings.append("case.json missing; contract merge unverified")

    if not os.path.exists(a.result):
        print("FAIL: result.json not found at %s" % a.result); return 1
    try:
        res = json.load(open(a.result, encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        print("FAIL: result.json invalid JSON: %s" % e); return 1
    if not isinstance(res, dict):
        print("FAIL: result.json top level must be an object"); return 1

    cid = case.get("case_id") if isinstance(case, dict) else None
    if not res.get("case_id"):
        problems.append("MISSING case_id")
    elif cid and res.get("case_id") != cid:
        problems.append("case_id mismatch: %r vs %r" % (res.get("case_id"), cid))

    contract = case.get("output_contract") if isinstance(case, dict) else None
    if isinstance(contract, dict):
        for f in contract.keys():
            if f not in res:
                problems.append("MISSING output_contract field: %s" % f)
    elif isinstance(contract, list):
        for f in contract:
            name = f if isinstance(f, str) else (f.get("name") if isinstance(f, dict) else None)
            if name and name not in res:
                problems.append("MISSING output_contract field: %s" % name)
    else:
        warnings.append("case.json declares no output_contract; standard field set assumed")

    for f in ("status", "gaps", "anomalies"):
        if f not in res:
            problems.append("MISSING honest-status field: %s" % f)

    ms_text = ""
    if a.manuscript and os.path.exists(a.manuscript):
        ms_text = open(a.manuscript, encoding="utf-8", errors="replace").read()
    elif isinstance(res.get("manuscript"), str):
        ms_text = res["manuscript"]
    if not ms_text and (a.require):
        warnings.append("no manuscript text; coverage check skipped")

    if a.require:
        names = a.names.split(",") if a.names else ["cat%d" % i for i in range(len(a.require.split("|")))]
        cats = a.require.split("|")
        cov = res.get("coverage") if isinstance(res.get("coverage"), dict) else {}
        for name, cat in zip(names, cats):
            kws = [k for k in cat.split(",") if k]
            hit = any(re.search(k, ms_text, re.I) for k in kws if k)
            declared = str(cov.get(name, "")).lower()
            declared_gap = re.search(r"gap|not_applicable|n/?a|missing|缺|未|不适用", declared)
            if not hit and not declared_gap:
                problems.append("COVERAGE: category '%s' not found in manuscript (declare result.coverage.%s='gap(reason)' if truly missing)" % (name, name))

    if warnings:
        print("WARN (%d):" % len(warnings))
        for w in warnings: print("  - %s" % w)
    if problems:
        print("FAIL (%d):" % len(problems))
        for p in problems: print("  - %s" % p)
        return 1
    print("PASS: delivery contract satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
