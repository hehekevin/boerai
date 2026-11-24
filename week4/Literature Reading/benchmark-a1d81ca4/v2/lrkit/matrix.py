"""Multi-document comparison matrix: 对得齐、填得准、说得清、查得回。

字段字典（fielddict.json）：[{name, definition, unit?, comparability:
  direct|subset|not_comparable, note?}]

比较表（matrix.json）：{papers: [paper_id], cells: [{paper_id, field,
  value, unit?, evidence: {loc, quote}, status}]}

引擎职责：
  - 单元格核验：取值必须带该论文的逐字证据；非抽取值保留状态不编造
  - 对齐判定：两级对齐（字段定义统一 + 条件可比性），判定哪些论文在
    同一条件下可比、哪些只能在可比子集内比较
  - 冲突归因：同一字段不同论文方向矛盾 → 归因候选（样本/方法/条件/指标），
    Agent 确认，冲突双方原话保留
"""
from __future__ import annotations

import json
import sys

from . import locate

ATTRITION_CLASSES = ["sample", "method", "condition", "metric", "population", "unresolved"]


def validate_cells(fielddict: list[dict], cells: list[dict],
                   blocks_by_paper: dict[str, list[dict]]) -> dict:
    fnames = {f["name"] for f in fielddict}
    problems, out = [], []
    for c in cells:
        pid, f = c.get("paper_id", "?"), c.get("field", "?")
        cp = []
        if f not in fnames:
            cp.append(f"field '{f}' not in field dictionary")
        if c.get("status", "extracted") == "extracted":
            ev = c.get("evidence") or {}
            blocks = blocks_by_paper.get(pid)
            if blocks is None:
                cp.append(f"paper '{pid}' has no extracted blocks")
            else:
                r = locate.verify_quote(blocks, str(ev.get("loc", "")), ev.get("quote", ""))
                if not r["verified"]:
                    cp.append(f"evidence unverified: {r['reason']}")
            fdef = next((x for x in fielddict if x["name"] == f), {})
            if fdef.get("unit") and c.get("unit") != fdef.get("unit"):
                cp.append(f"unit '{c.get('unit')}' != field dictionary unit "
                          f"'{fdef.get('unit')}'（口径随值记录，不一致须先换算）")
        out.append({"paper_id": pid, "field": f, "ok": not cp, "problems": cp})
        problems += [f"{pid}.{f}: {p}" for p in cp]
    return {"per_cell": out, "problems": problems, "ok": not problems,
            "rule": "每个单元格取值来自它标注的那篇论文；单位与口径随值记录"}


def comparability(fielddict: list[dict], field: str,
                  conditions: dict) -> dict:
    """conditions: {paper_id: {condition_key: value}}
    两级对齐：字段定义统一（fielddict）+ 条件可比性（conditions 关键键一致）。"""
    fdef = next((f for f in fielddict if f["name"] == field), None)
    if not fdef:
        return {"field": field, "ok": False, "error": "field not in dictionary"}
    base = fdef.get("comparability", "direct")
    if base == "not_comparable":
        return {"field": field, "verdict": "not_comparable",
                "reason": fdef.get("note", "字段定义声明不可直接比较"), "ok": True}
    cond_keys = {}
    for pid, cond in conditions.items():
        for k, v in (cond or {}).items():
            cond_keys.setdefault(k, {})[pid] = str(v)
    varying = {k: v for k, v in cond_keys.items() if len(set(v.values())) > 1}
    if not varying:
        return {"field": field, "verdict": "direct", "varying_conditions": {},
                "ok": True}
    subsets = {}
    # 以第一个变化条件为轴划分子集
    axis = sorted(varying)[0]
    for pid, v in varying[axis].items():
        subsets.setdefault(v, []).append(pid)
    return {"field": field, "verdict": "subset", "varying_conditions": varying,
            "subset_axis": axis, "subsets": subsets,
            "reason": f"条件 {axis} 不一致，只能在可比子集内比较", "ok": True}


def conflict_attribution(field: str, entries: list[dict]) -> dict:
    """entries: [{paper_id, value, quote, conditions: {...}}]
    方向判定与归因候选由引擎给出机械提示，Agent 确认。"""
    if len(entries) < 2:
        return {"field": field, "conflict": False, "note": "少于两条取值，无冲突可判"}
    vals = {str(e.get("value")) for e in entries}
    if len(vals) <= 1:
        return {"field": field, "conflict": False, "note": "取值一致"}
    # 归因候选：条件差异最多的键
    cond_keys = {}
    for e in entries:
        for k, v in (e.get("conditions") or {}).items():
            cond_keys.setdefault(k, set()).add(str(v))
    candidates = [k for k, vs in sorted(cond_keys.items()) if len(vs) > 1]
    return {"field": field, "conflict": True,
            "sides": [{"paper_id": e.get("paper_id"), "value": e.get("value"),
                       "quote": e.get("quote")} for e in entries],
            "candidate_attributions": candidates or ["unresolved"],
            "note": "候选归因由条件差异机械给出；Agent 须回原文确认并写理由；"
                    "冲突双方原话并列保留"}


def _demo() -> int:
    fielddict = [
        {"name": "band_gap_ev", "definition": "UV-Vis Tauc 法带隙", "unit": "eV",
         "comparability": "direct"},
        {"name": "degradation_pct", "definition": "60 min 可见光降解率", "unit": "%",
         "comparability": "subset", "note": "光源功率须一致"}]
    blocks = {"P1": [{"loc": "T1", "text": "Band gap 1.62 eV; degradation 92% at 300 W."}],
              "P2": [{"loc": "T2", "text": "Band gap 1.70 eV; degradation 88% at 150 W."}]}
    cells = [
        {"paper_id": "P1", "field": "band_gap_ev", "value": 1.62, "unit": "eV",
         "evidence": {"loc": "T1", "quote": "Band gap 1.62 eV"}},
        {"paper_id": "P2", "field": "band_gap_ev", "value": 1.70, "unit": "eV",
         "evidence": {"loc": "T2", "quote": "Band gap 1.70 eV"}},
        {"paper_id": "P1", "field": "degradation_pct", "value": 92, "unit": "%",
         "evidence": {"loc": "T1", "quote": "degradation 92%"}},
    ]
    vc = validate_cells(fielddict, cells, blocks)
    assert vc["ok"], vc
    comp = comparability(fielddict, "degradation_pct",
                         {"P1": {"lamp_w": "300"}, "P2": {"lamp_w": "150"}})
    assert comp["verdict"] == "subset" and comp["subset_axis"] == "lamp_w"
    conf = conflict_attribution("degradation_pct", [
        {"paper_id": "P1", "value": 92, "quote": "degradation 92%",
         "conditions": {"lamp_w": "300"}},
        {"paper_id": "P2", "value": 88, "quote": "degradation 88%",
         "conditions": {"lamp_w": "150"}}])
    assert conf["conflict"] and "lamp_w" in conf["candidate_attributions"]
    bad = [{"paper_id": "P1", "field": "band_gap_ev", "value": 1.62, "unit": "nm",
            "evidence": {"loc": "T1", "quote": "Band gap 1.62 eV"}}]
    assert not validate_cells(fielddict, bad, blocks)["ok"]  # 单位口径不符被抓
    print(json.dumps({"demo": "matrix", "cells_ok": vc["ok"],
                      "comparability": comp["verdict"],
                      "conflict_attr": conf["candidate_attributions"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        fd = json.load(open(sys.argv[2], encoding="utf-8"))
        cells = json.load(open(sys.argv[3], encoding="utf-8"))
        blocks = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = validate_cells(fd.get("fields", fd), cells.get("cells", cells),
                             blocks.get("papers", blocks))
        out = sys.argv[5] if len(sys.argv) > 5 else None
    elif cmd == "comparability":
        fd = json.load(open(sys.argv[2], encoding="utf-8"))
        cond = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = comparability(fd.get("fields", fd), sys.argv[3],
                            cond.get("conditions", cond))
        out = sys.argv[5] if len(sys.argv) > 5 else None
    elif cmd == "conflict":
        entries = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = conflict_attribution(sys.argv[2], entries.get("entries", entries))
        out = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        print("usage: matrix.py [validate|comparability|conflict] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"-> {out}")
    print(f"ok={rep.get('ok', True)}")
    sys.exit(0 if rep.get("ok", True) else 1)
