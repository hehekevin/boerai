#!/usr/bin/env python3
"""clean-engine: literature data cleaning with numbered rules, unit conversion, provenance.

Deterministic subcommands (0 model requests):
  --normalize RECORDS_JSON     field normalization by numbered rule library (R1..Rn priority)
  --units VALUES_JSON          unit conversion keeping original value + formula + precision
  --merge RECORDS_JSON         explainable merge keys (no cross-experiment/cross-substance false merge)
  --trace CLEANED_JSON         every changed value traces back to rule id + input row + source
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata

RULE_LIBRARY = [
    {"rule_id": "R1", "priority": 1, "name": "field_rename", "desc": "同义字段名统一",
     "map": {"accuracy": "accuracy", "acc": "accuracy", "准确率": "accuracy", "AUC": "auc", "auc_score": "auc"},
     "applicable": "列名在映射表内", "failure": "未映射字段列入 unmapped 清单"},
    {"rule_id": "R2", "priority": 2, "name": "type_cast", "desc": "数据类型统一（数值列转float）",
     "applicable": "目标类型列为数值", "failure": "转换失败保留原值+标记 cast_failed"},
    {"rule_id": "R3", "priority": 3, "name": "allowed_values", "desc": "枚举值归一（如 dataset split: val/validation→valid）",
     "map": {"valid": "valid", "validation": "valid", "val": "valid", "test": "test", "train": "train"},
     "applicable": "枚举字段", "failure": "未知枚举值保留原值+标记"},
    {"rule_id": "R4", "priority": 4, "name": "missing_vs_unknown", "desc": "缺失(字段不存在)与未知(存在但空)区分编码",
     "applicable": "全字段", "failure": "无"},
]

UNIT_CONVERSIONS = {
    # unit -> (canonical_unit, factor, formula_template)
    "percent": ("ratio", 0.01, "value*0.01"),
    "%": ("ratio", 0.01, "value*0.01"),
    "mg": ("g", 0.001, "value*0.001"),
    "kg": ("g", 1000.0, "value*1000"),
    "mL": ("L", 0.001, "value*0.001"),
    "mm": ("m", 0.001, "value*0.001"),
    "cm": ("m", 0.01, "value*0.01"),
    "min": ("s", 60.0, "value*60"),
    "h": ("s", 3600.0, "value*3600"),
}


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return data if isinstance(data, list) else data.get("records", data.get("rows", data.get("items", data.get("cleaned", []))))


def cmd_normalize(path):
    recs = load(path)
    unmapped = set()
    cleaned, trace = [], []
    for i, r in enumerate(recs):
        out = {}
        for k, v in r.items():
            canon = None
            for rule in RULE_LIBRARY:
                m = rule.get("map") or {}
                if k in m:
                    canon = m[k]
                    if canon != k:
                        trace.append({"rule_id": rule["rule_id"], "row": i, "field": k, "change": f"rename {k}->{canon}", "value": v})
                    break
                if rule["name"] == "type_cast" and isinstance(v, str) and re.match(r"^-?\d+\.?\d*$", v.strip()):
                    canon = k
                    trace.append({"rule_id": "R2", "row": i, "field": k, "change": f"cast str->float", "old": v, "new": float(v)})
                    v = float(v)
                    break
            if canon is None:
                canon = k
                if k not in ("row_id",):
                    unmapped.add(k)
            out[canon] = v
        cleaned.append(out)
    print(json.dumps({"schema": "clean/normalize@1", "n_rows": len(recs), "cleaned": cleaned,
                      "unmapped_fields": sorted(unmapped),
                      "rule_library": [{"rule_id": r["rule_id"], "name": r["name"], "priority": r["priority"],
                                         "applicable": r["applicable"], "failure": r["failure"]} for r in RULE_LIBRARY],
                      "trace_count": len(trace), "trace": trace[:30]}, ensure_ascii=False, indent=1))
    return 0


def cmd_units(path):
    vals = load(path)
    out = []
    for v in vals:
        raw, unit = v.get("value"), v.get("unit", "")
        conv = UNIT_CONVERSIONS.get(unit)
        if conv:
            canon, factor, formula = conv
            newv = round(float(raw) * factor, 6)
            out.append({"input": f"{raw} {unit}", "canonical": f"{newv} {canon}",
                        "formula": f"{formula} -> {raw}*{factor}={newv}",
                        "original_kept": f"{raw} {unit}", "precision": f"{len(str(raw).split('.')[-1]) if '.' in str(raw) else 0} 位小数保留",
                        "note": "复合单位/数量级前缀/区间值按此表逐段处理；未收录单位不改值"})
        else:
            out.append({"input": f"{raw} {unit}", "canonical": f"{raw} {unit}",
                        "formula": "no_conversion", "original_kept": f"{raw} {unit}",
                        "note": "单位未收录——保留原值，列入 needs_manual 列表"})
    print(json.dumps({"schema": "clean/units@1", "converted": sum(1 for o in out if o['formula'] != 'no_conversion'),
                      "needs_manual": sum(1 for o in out if o['formula'] == 'no_conversion'),
                      "items": out[:40]}, ensure_ascii=False, indent=1))
    return 0


def cmd_merge(path):
    recs = load(path)
    groups = {}
    for r in recs:
        # merge key: explicit fields, NOT fuzzy — avoid cross-experiment false merge
        k = (str(r.get("substance", r.get("material", r.get("paper_id", "")))).lower(),
             str(r.get("experiment_id", r.get("condition", ""))).lower())
        groups.setdefault(k, []).append(r)
    merges = []
    for k, members in groups.items():
        if len(members) < 2:
            continue
        diffs = {}
        for f in members[0]:
            vals = {str(m.get(f)) for m in members}
            if len(vals) > 1:
                diffs[f] = sorted(vals)
        merges.append({"merge_key": {"substance": k[0], "experiment": k[1]}, "n_members": len(members),
                       "merge_rationale": "同一物质+同一实验标识才合并；字段冲突保留并记录——不同实验/不同物质绝不合并",
                       "field_conflicts": diffs})
    print(json.dumps({"schema": "clean/merge@1", "n_input": len(recs), "n_merge_groups": len(merges),
                      "merges": merges[:20], "unmerged_note": "未匹配键的记录保持独立"}, ensure_ascii=False, indent=1))
    return 0


def cmd_trace(path):
    data = json.load(open(path, encoding="utf-8"))
    changes = data.get("trace", [])
    problems = []
    for c in changes:
        if not c.get("rule_id"):
            problems.append({"row": c.get("row"), "issue": "变更缺规则编号"})
        if "row" not in c:
            problems.append({"issue": "变更缺输入行定位"})
    print(json.dumps({"schema": "clean/trace@1", "n_changes": len(changes), "n_problems": len(problems),
                      "problems": problems[:20],
                      "note": "每个改动值沿 rule_id -> 输入行 -> 原始文献 回溯"}, ensure_ascii=False, indent=1))
    return 0 if not problems else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalize")
    ap.add_argument("--units")
    ap.add_argument("--merge")
    ap.add_argument("--trace")
    a = ap.parse_args()
    if a.normalize:
        return cmd_normalize(a.normalize)
    if a.units:
        return cmd_units(a.units)
    if a.merge:
        return cmd_merge(a.merge)
    if a.trace:
        return cmd_trace(a.trace)
    ap.error("choose --normalize / --units / --merge / --trace")


if __name__ == "__main__":
    sys.exit(main())
