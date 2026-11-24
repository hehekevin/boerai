"""Data cleaning & standardization with rule-level traceability.

规则库（rules.json）：[{rule_id, kind, priority, ...}]
  kind=rename   {from, to}                       字段映射
  kind=unit     {field, from_unit, to_unit, factor, offset?}  单位换算
  kind=range    {field, min, max}                越界判定（只标不改）
  kind=required {field}                          缺失判定（保持空缺，不编造）
  kind=synonym  {field, from, to}                同义名归一

输入表（rows.json）：[{row_id, source: {file, loc?}, fields: {...}}]

输出：cleaned rows + 行级变更记录 changelog[]（每个被改动的值可沿
rule_id 回到输入行与原始来源）+ review[]（工具不敢确认、须人工的项）。
规则按 priority 升序执行；冲突（同字段两条 unit/ rename 规则命中）进 review。
"""
from __future__ import annotations

import json
import re
import sys


def _convert(v, factor, offset=0.0):
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return x * factor + offset


def apply_rules(rows: list[dict], rules: list[dict]) -> dict:
    rules = sorted(rules, key=lambda r: r.get("priority", 100))
    changelog, review = [], []
    out_rows = []
    for row in rows:
        r = dict(row)
        fields = dict(r.get("fields") or {})
        rid = r.get("row_id", "?")
        src = r.get("source", {})
        # 1) rename
        for rule in [x for x in rules if x["kind"] == "rename"]:
            frm, to = rule["from"], rule["to"]
            if frm in fields:
                if to in fields and fields[to] != fields[frm]:
                    review.append({"row_id": rid, "rule_id": rule["rule_id"],
                                   "issue": f"rename 冲突：{frm} 与 {to} 同存且值不同",
                                   "kept": to})
                    continue
                fields[to] = fields.pop(frm)
                changelog.append({"row_id": rid, "rule_id": rule["rule_id"],
                                  "action": "rename", "from": frm, "to": to,
                                  "source": src})
        # 2) synonym
        for rule in [x for x in rules if x["kind"] == "synonym"]:
            f, frm, to = rule["field"], rule["from"], rule["to"]
            if str(fields.get(f, "")).strip().lower() == str(frm).lower():
                old = fields[f]
                fields[f] = to
                changelog.append({"row_id": rid, "rule_id": rule["rule_id"],
                                  "action": "synonym", "field": f,
                                  "old": old, "new": to, "source": src})
        # 3) unit
        for rule in [x for x in rules if x["kind"] == "unit"]:
            f = rule["field"]
            if f not in fields:
                continue
            cur = fields.get(f + "__unit", rule.get("assume_unit"))
            if cur == rule["from_unit"]:
                new = _convert(fields[f], rule.get("factor", 1), rule.get("offset", 0))
                if new is None:
                    review.append({"row_id": rid, "rule_id": rule["rule_id"],
                                   "issue": f"字段 {f} 值不可数值化：{fields[f]!r}"})
                    continue
                changelog.append({"row_id": rid, "rule_id": rule["rule_id"],
                                  "action": "unit", "field": f,
                                  "old": fields[f], "old_unit": cur,
                                  "new": round(new, 10), "new_unit": rule["to_unit"],
                                  "formula": f"new = old * {rule.get('factor', 1)} + {rule.get('offset', 0)}",
                                  "source": src})
                fields[f] = round(new, 10)
                fields[f + "__unit"] = rule["to_unit"]
            elif cur and cur != rule["to_unit"]:
                review.append({"row_id": rid, "rule_id": rule["rule_id"],
                               "issue": f"字段 {f} 单位 {cur} 无换算规则", "kept": fields[f]})
        # 4) range / required (只标记，不改值)
        for rule in [x for x in rules if x["kind"] == "range"]:
            f = rule["field"]
            if f in fields and fields[f] is not None:
                try:
                    v = float(str(fields[f]).replace(",", ""))
                    if not (rule.get("min", -1e308) <= v <= rule.get("max", 1e308)):
                        review.append({"row_id": rid, "rule_id": rule["rule_id"],
                                       "issue": f"字段 {f}={v} 越界 "
                                                f"[{rule.get('min')}, {rule.get('max')}]",
                                       "kept": v})
                except (TypeError, ValueError):
                    review.append({"row_id": rid, "rule_id": rule["rule_id"],
                                   "issue": f"字段 {f} 非数值，无法判定越界"})
        for rule in [x for x in rules if x["kind"] == "required"]:
            f = rule["field"]
            if fields.get(f) in (None, ""):
                changelog.append({"row_id": rid, "rule_id": rule["rule_id"],
                                  "action": "missing_kept_empty", "field": f,
                                  "source": src})
        r["fields"] = fields
        out_rows.append(r)
    return {"rows": out_rows, "changelog": changelog, "review": review,
            "ok": True,
            "rule": "每个改动值可沿 rule_id 回到输入行与来源；不确定项进 review，不静默处理"}


def detect_duplicates(rows: list[dict], key_fields: list[str]) -> dict:
    """按可解释判定键分组；同键不同细节（如同物质不同温度）进 review 而非合并。"""
    groups = {}
    for r in rows:
        f = r.get("fields") or {}
        key = tuple(str(f.get(k, "")).strip().lower() for k in key_fields)
        groups.setdefault(key, []).append(r)
    dups, review = [], []
    for key, members in groups.items():
        if len(members) > 1:
            detail = {k: {str((m.get("fields") or {}).get(k, "")) for m in members}
                      for k in members[0].get("fields", {})}
            varying = {k: v for k, v in detail.items() if len(v) > 1 and k not in key_fields}
            entry = {"key": dict(zip(key_fields, key)),
                     "row_ids": [m.get("row_id") for m in members]}
            if varying:
                entry["varying_fields"] = varying
                entry["recommendation"] = "疑似同一物质不同实验条件，须人工确认，不自动合并"
                review.append(entry)
            else:
                entry["recommendation"] = "字段完全一致，可合并保留首条"
                dups.append(entry)
    return {"exact_duplicates": dups, "needs_review": review,
            "rule": "重复记录 ≠ 重复实验；判定键之外有差异的不自动合并"}


def _demo() -> int:
    rows = [
        {"row_id": "r1", "source": {"file": "paperA.csv", "row": 2},
         "fields": {"BET_area": 152, "BET_area__unit": "m2/g", "temp": 500, "temp__unit": "C",
                    "material": "TiO2 (P25)"}},
        {"row_id": "r2", "source": {"file": "paperB.csv", "row": 5},
         "fields": {"surface": 0.0152, "surface__unit": "cm2/g", "temp": 520, "temp__unit": "C",
                    "material": "titanium dioxide"}},
        {"row_id": "r3", "source": {"file": "paperC.csv", "row": 9},
         "fields": {"surface": 152, "surface__unit": "m2/g", "temp": 99999, "temp__unit": "C"}},
    ]
    rules = [
        {"rule_id": "R1", "kind": "rename", "from": "BET_area", "to": "surface", "priority": 1},
        {"rule_id": "R2", "kind": "synonym", "field": "material",
         "from": "titanium dioxide", "to": "TiO2", "priority": 2},
        {"rule_id": "R3", "kind": "unit", "field": "surface", "from_unit": "cm2/g",
         "to_unit": "m2/g", "factor": 0.0001, "priority": 3},
        {"rule_id": "R4", "kind": "range", "field": "temp", "min": 0, "max": 2000, "priority": 4},
        {"rule_id": "R5", "kind": "required", "field": "material", "priority": 5},
        {"rule_id": "R6", "kind": "synonym", "field": "material",
         "from": "TiO2 (P25)", "to": "TiO2", "priority": 2},
    ]
    rep = apply_rules(rows, rules)
    r2 = next(r for r in rep["rows"] if r["row_id"] == "r2")
    assert abs(r2["fields"]["surface"] - 0.0152 * 0.0001) < 1e-12
    assert any(c["rule_id"] == "R3" and c["old"] == 0.0152 for c in rep["changelog"])
    assert any("越界" in x["issue"] for x in rep["review"])  # r3 temp=99999
    assert r2["fields"]["material"] == "TiO2"
    dup = detect_duplicates(rep["rows"], ["material"])
    # r1 与 r2 归一后同为 TiO2，但 temp/surface 不同 → 进 review 而非自动合并
    assert dup["needs_review"] and "temp" in dup["needs_review"][0]["varying_fields"]
    print(json.dumps({"demo": "clean", "changes": len(rep["changelog"]),
                      "review": len(rep["review"]),
                      "converted_r2": r2["fields"]["surface"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "apply":
        rows = json.load(open(sys.argv[2], encoding="utf-8"))
        rules = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = apply_rules(rows.get("rows", rows), rules.get("rules", rules))
        json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"changes={len(rep['changelog'])} review={len(rep['review'])} -> {sys.argv[4]}")
    elif cmd == "dedup":
        rows = json.load(open(sys.argv[2], encoding="utf-8"))
        keys = sys.argv[4].split(",")
        rep = detect_duplicates(rows.get("rows", rows), keys)
        json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"exact={len(rep['exact_duplicates'])} review={len(rep['needs_review'])}")
    else:
        print("usage: clean.py [apply|dedup] ...")
        sys.exit(2)
