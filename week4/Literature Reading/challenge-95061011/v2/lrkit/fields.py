"""Structured field extraction verification: 字段表驱动的结论与数据提取。

字段表 schema（fields.json）：
  [{name, type: text|number|enum|list, unit?, enum?, required?}]

抽取结果（extracted.json）：
  {paper_id, fields: {name: {value, status: extracted|not_reported|failed,
                             evidence: {loc, quote}, condition?}}}

引擎保证：
  - 每个必填字段都有条目，区分"原文未报告"与"抽取失败"
  - extracted 的值必须带逐字证据（数字值须在引文中出现）
  - 数值不被改写：值与引文中的字面一致（单位随值记录）
  - 结论分层：Agent 在 value 之外可用 layer: stated|limited|speculative 标注
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

VALID_FSTATUS = {"extracted", "not_reported", "failed"}
LAYERS = {"stated", "limited", "speculative"}  # 明确结论/限制条件/推测表述


def validate_fields(schema: list[dict], extracted: dict,
                    blocks: list[dict]) -> dict:
    problems, per_field = [], []
    values = extracted.get("fields") or {}
    for f in schema:
        name = f["name"]
        item = values.get(name)
        if item is None:
            problems.append(f"field '{name}' missing entirely")
            per_field.append({"field": name, "ok": False, "problems": ["missing"]})
            continue
        fp = []
        st = str(item.get("status", ""))
        if st not in VALID_FSTATUS:
            fp.append(f"invalid status '{st}'")
        layer = item.get("layer")
        if layer is not None and layer not in LAYERS:
            fp.append(f"invalid layer '{layer}' (stated|limited|speculative)")
        if st == "extracted":
            ev = item.get("evidence") or {}
            r = locate.verify_quote(blocks, str(ev.get("loc", "")), ev.get("quote", ""))
            if not r["verified"]:
                fp.append(f"evidence unverified: {r['reason']}")
            v = item.get("value")
            if isinstance(v, (int, float)):
                # 数值必须在引文中以同一字面出现（允许 1.62 / 1.62 ）
                num = re.escape(("%g" % v) if isinstance(v, float) else str(v))
                if not re.search(num, ev.get("quote", "")):
                    fp.append(f"numeric value {v} not found verbatim in quote")
            if f.get("unit") and not item.get("unit", f.get("unit")):
                fp.append("unit required by schema but not recorded")
        if st == "not_reported" and f.get("required") and not item.get("note"):
            fp.append("required field marked not_reported without note")
        per_field.append({"field": name, "ok": not fp, "problems": fp})
        problems += [f"field '{name}': {p}" for p in fp]
    counts = {s: sum(1 for it in values.values() if it.get("status") == s)
              for s in VALID_FSTATUS}
    return {"per_field": per_field, "counts": counts, "problems": problems,
            "ok": not problems,
            "rule": "extracted values need verbatim evidence; not_reported != failed; "
                    "numbers must match the quote literally"}


def schema_template(names: list[str]) -> list[dict]:
    """生成字段表骨架，Agent 按题面调整。"""
    return [{"name": n, "type": "text", "required": True} for n in names]


def merge_table_rows(schema: list[dict], per_paper: list[dict]) -> dict:
    """把多篇论文的抽取结果合成对照表（供 matrix 模块使用）。"""
    header = ["paper_id"] + [f["name"] for f in schema]
    rows = []
    for p in per_paper:
        row = {"paper_id": p.get("paper_id", "?")}
        for f in schema:
            it = (p.get("fields") or {}).get(f["name"]) or {}
            row[f["name"]] = it.get("value") if it.get("status") == "extracted" \
                else it.get("status", "missing")
        rows.append(row)
    return {"header": header, "rows": rows,
            "note": "cell values carry their paper_id; non-extracted cells keep status, not invented values"}


def _demo() -> int:
    blocks = [{"loc": "T1", "source": "S1",
               "text": "Table 1: catalyst A, surface area 152 m2/g, calcined at 500 C."},
              {"loc": "P4", "source": "S1",
               "text": "These results suggest the method may generalize to other oxides."}]
    schema = [{"name": "surface_area_m2g", "type": "number", "unit": "m2/g", "required": True},
              {"name": "calcination_temp_c", "type": "number", "unit": "C", "required": True},
              {"name": "cycle_stability", "type": "text", "required": True}]
    extracted = {"paper_id": "P1", "fields": {
        "surface_area_m2g": {"value": 152, "unit": "m2/g", "status": "extracted",
                             "layer": "stated",
                             "evidence": {"loc": "T1", "quote": "surface area 152 m2/g"}},
        "calcination_temp_c": {"value": 500, "unit": "C", "status": "extracted",
                               "layer": "stated",
                               "evidence": {"loc": "T1", "quote": "calcined at 500 C"}},
        "cycle_stability": {"status": "not_reported", "note": "正文与表格均未报告循环稳定性"},
    }}
    rep = validate_fields(schema, extracted, blocks)
    assert rep["ok"] and rep["counts"]["not_reported"] == 1, rep
    bad = {"paper_id": "P1", "fields": {
        "surface_area_m2g": {"value": 215, "unit": "m2/g", "status": "extracted",
                             "evidence": {"loc": "T1", "quote": "surface area 152 m2/g"}},
        "calcination_temp_c": {"status": "failed"},
        "cycle_stability": {"status": "extracted", "evidence": {"loc": "P9", "quote": "x"}}}}
    rep2 = validate_fields(schema, bad, blocks)
    assert not rep2["ok"] and len(rep2["problems"]) >= 2
    tbl = merge_table_rows(schema, [extracted])
    assert tbl["rows"][0]["cycle_stability"] == "not_reported"
    print(json.dumps({"demo": "fields", "ok": rep["ok"], "counts": rep["counts"],
                      "bad_caught": len(rep2["problems"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        schema = json.load(open(sys.argv[2], encoding="utf-8"))
        ext = json.load(open(sys.argv[3], encoding="utf-8"))
        blocks = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = validate_fields(schema.get("fields", schema), ext, blocks.get("blocks", blocks))
        if len(sys.argv) > 5:
            json.dump(rep, open(sys.argv[5], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"ok={rep['ok']} problems={len(rep['problems'])}")
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "merge":
        schema = json.load(open(sys.argv[2], encoding="utf-8"))
        per = [json.load(open(p, encoding="utf-8")) for p in sys.argv[3:-1]]
        rep = merge_table_rows(schema.get("fields", schema), per)
        json.dump(rep, open(sys.argv[-1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"rows={len(rep['rows'])} -> {sys.argv[-1]}")
    else:
        print("usage: fields.py [validate|merge] ...")
        sys.exit(2)
