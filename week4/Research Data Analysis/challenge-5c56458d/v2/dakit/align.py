"""字段对齐：多来源列 → 目标 schema 的映射，带置信度；未解析字段显式列出。

规则（全部确定性，可复算）：
  1.0  exact        列名完全一致
  0.9  normalized   去大小写/空白/单位括号/标点归一化后一致
  0.75 synonym      命中内置同义词表（中英文常用字段名）
  0.5–0.7 fuzzy     difflib 相似度 ≥0.6 —— 标注 needs_review，不自动采用
  <0.6 unresolved   显式列入 unresolved，绝不静默丢弃；目标侧缺口列入 missing_targets

映射只是候选：置信度 <0.9 的一律要求 Agent 按数据字典语义确认后才使用。
"""
from __future__ import annotations

import difflib
import json
import re
import sys

SYNONYMS = {
    # 归一化形式 -> 规范名（可按案例数据字典扩充；规则文件即数据）
    "id": "id", "sampleid": "id", "subjectid": "id", "patientid": "id", "编号": "id",
    "样品编号": "id", "样本编号": "id", "受试者编号": "id",
    "group": "group", "grp": "group", "treatment": "group", "arm": "group",
    "分组": "group", "处理组": "group", "组别": "group",
    "value": "value", "val": "value", "measurement": "value", "result": "value",
    "测量值": "value", "测定值": "value", "数值": "value",
    "date": "date", "time": "date", "timestamp": "date", "measuredon": "date",
    "日期": "date", "时间": "date", "采样日期": "date",
    "batch": "batch", "lot": "batch", "run": "batch", "批次": "batch",
    "conc": "concentration", "concentration": "concentration", "浓度": "concentration",
    "weight": "weight", "wt": "weight", "体重": "weight", "质量": "weight",
    "age": "age", "年龄": "age", "sex": "sex", "gender": "sex", "性别": "sex",
}

CONF_THRESHOLD_AUTO = 0.9   # ≥ 此值才允许不经人工确认直接使用
CONF_THRESHOLD_FUZZY = 0.6  # 低于此值 → unresolved


def norm_name(s: str) -> str:
    s = re.sub(r"[\(\[][^\)\]]*[\)\]]", "", s or "")  # 去单位括号
    return re.sub(r"[^0-9a-z一-鿿]+", "", s.lower())


def map_columns(source_cols: list[str], target_cols: list[str],
                synonyms: dict | None = None) -> dict:
    syn = dict(SYNONYMS)
    if synonyms:
        syn.update({norm_name(k): v for k, v in synonyms.items()})
    target_norm = {norm_name(t): t for t in target_cols}
    mappings, unresolved = [], []
    for col in source_cols:
        n = norm_name(col)
        if col in target_cols:
            mappings.append({"source": col, "target": col, "method": "exact", "confidence": 1.0})
            continue
        if n in target_norm:
            mappings.append({"source": col, "target": target_norm[n], "method": "normalized",
                             "confidence": 0.9})
            continue
        if n in syn and syn[n] in target_norm:
            mappings.append({"source": col, "target": target_norm[syn[n]], "method": "synonym",
                             "confidence": 0.75, "needs_review": True})
            continue
        best, best_r = None, 0.0
        for tn, t in target_norm.items():
            r = difflib.SequenceMatcher(None, n, tn).ratio()
            if r > best_r:
                best, best_r = t, r
        if best and best_r >= CONF_THRESHOLD_FUZZY:
            conf = round(0.5 + 0.2 * best_r, 3)
            mappings.append({"source": col, "target": best, "method": "fuzzy",
                             "confidence": conf, "needs_review": True,
                             "similarity": round(best_r, 3)})
        else:
            unresolved.append({"source": col, "reason": "no target match above 0.6 similarity",
                               "best_guess": best, "best_similarity": round(best_r, 3)})
    used = {m["target"] for m in mappings}
    missing_targets = [t for t in target_cols if t not in used]
    return {"mappings": mappings, "unresolved": unresolved, "missing_targets": missing_targets,
            "auto_usable": [m for m in mappings
                            if m["confidence"] >= CONF_THRESHOLD_AUTO and not m.get("needs_review")],
            "policy": "confidence < 0.9 requires agent confirmation against the data dictionary; "
                      "unresolved fields are kept in the output, never silently dropped"}


def merge_sources(sources: list[dict], mapping_report: dict) -> dict:
    """按确认后的映射合并多表为统一长表行。sources: [{name, rows, mapping:{src:tgt}}]。
    未映射列进入 extra_fields（保留原值与来源），不丢弃。"""
    merged = []
    for src in sources:
        for i, row in enumerate(src["rows"]):
            out = {"_source": src["name"], "_row": i}
            extra = {}
            for k, v in row.items():
                tgt = src["mapping"].get(k)
                if tgt:
                    out[tgt] = v
                else:
                    extra[k] = v
            if extra:
                out["_extra_fields"] = extra
            merged.append(out)
    return {"n_rows": len(merged), "rows": merged,
            "note": "unmapped columns preserved under _extra_fields with provenance (_source, _row)"}


def _demo() -> int:
    target = ["id", "group", "value", "date", "batch"]
    src = ["sample_id", "grp", "测定值", "Measured_on", "lot", "odd_column"]
    rep = map_columns(src, target)
    by_src = {m["source"]: m for m in rep["mappings"]}
    assert by_src["sample_id"]["method"] == "synonym" and by_src["sample_id"]["target"] == "id"
    assert by_src["grp"]["method"] == "synonym" and by_src["grp"]["confidence"] == 0.75
    assert by_src["测定值"]["target"] == "value"
    assert by_src["Measured_on"]["target"] == "date" and by_src["Measured_on"]["method"] == "synonym"
    assert by_src["lot"]["target"] == "batch"
    assert [u["source"] for u in rep["unresolved"]] == ["odd_column"], rep["unresolved"]
    assert rep["missing_targets"] == []
    # 合并不丢列
    rows = [{"sample_id": "S1", "grp": "A", "测定值": 3.2, "odd_column": "keep-me"}]
    m = merge_sources([{"name": "lab1", "rows": rows,
                        "mapping": {"sample_id": "id", "grp": "group", "测定值": "value"}}], rep)
    assert m["rows"][0]["id"] == "S1" and m["rows"][0]["_extra_fields"] == {"odd_column": "keep-me"}
    print(json.dumps({"demo": "align", "mapped": len(rep["mappings"]),
                      "auto_usable": len(rep["auto_usable"]),
                      "unresolved": [u["source"] for u in rep["unresolved"]],
                      "extra_preserved": m["rows"][0]["_extra_fields"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.align sources.json out.json
    # sources.json: {"target_columns":[...], "sources":[{"name":..., "columns":[...]}],
    #                "synonyms": {..}?}
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    reports = []
    for s in spec["sources"]:
        reports.append({"source": s["name"]} | map_columns(
            s["columns"], spec["target_columns"], spec.get("synonyms")))
    json.dump({"reports": reports}, open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    n_un = sum(len(r["unresolved"]) for r in reports)
    print(f"aligned {len(reports)} sources, {n_un} unresolved columns -> {sys.argv[2]}")
