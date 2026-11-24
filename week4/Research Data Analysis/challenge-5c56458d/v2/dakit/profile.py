"""数据画像：schema 推断、类型检测、单位提示、主键唯一性、跨表连接键兼容。

输入：hk.extract 产出的 table dict（{header, rows:[{col: value}], ...}）或
      rows 列表 + header 列表。
输出：profile JSON —— 每列 {type, n, n_missing, missing_rate, n_distinct,
      min/max（数值）, unit_hint}；候选主键；跨表 join 候选（带重叠率与类型兼容）。

原则：只报告可观察事实；不做任何语义假设。空表、全缺失列如实报告，不猜。
"""
from __future__ import annotations

import json
import re
import statistics
import sys

_INT_RE = re.compile(r"[-+]?\d+$")
_FLOAT_RE = re.compile(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")
_DATE_RE = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")


def unit_hints(header: list[str]) -> dict[str, str]:
    """从表头括号里取单位提示，如 'concentration (mg/L)' -> mg/L。"""
    hints = {}
    for h in header or []:
        m = re.search(r"[\(\[]([^\)\]]+)[\)\]]", h or "")
        if m:
            hints[h] = m.group(1).strip()
    return hints


def _looks_date(s: str) -> bool:
    return bool(_DATE_RE.fullmatch(str(s).strip()))


def infer_type(values: list) -> dict:
    """列类型推断：integer/float/date/text/boolean/empty。返回 {type, confidence, note}。"""
    vals = [v for v in values if v is not None and str(v).strip() != ""]
    if not vals:
        return {"type": "empty", "confidence": 1.0, "note": "no non-missing values"}
    n = len(vals)
    n_int = sum(1 for v in vals if isinstance(v, int) and not isinstance(v, bool)
                or (isinstance(v, str) and _INT_RE.fullmatch(v.strip())))
    n_flt = sum(1 for v in vals if isinstance(v, float)
                or (isinstance(v, str) and _FLOAT_RE.fullmatch(v.strip())))
    n_date = sum(1 for v in vals if isinstance(v, str) and _looks_date(v))
    n_bool = sum(1 for v in vals if str(v).strip().lower() in {"true", "false", "yes", "no", "0", "1"}
                 and n <= 20 and len({str(v).strip().lower() for v in vals}) <= 2)
    if n_int == n:
        return {"type": "integer", "confidence": 1.0, "note": ""}
    if n_flt + n_int == n:
        return {"type": "float", "confidence": round(n_flt / n, 3), "note": ""}
    if n_date == n:
        return {"type": "date", "confidence": 1.0, "note": "string dates; parse downstream"}
    if n_bool == n and n_bool > 0:
        return {"type": "boolean", "confidence": 0.8, "note": "2-level low-cardinality; could be categorical code"}
    if n_flt + n_int > 0 and n_flt + n_int < n:
        return {"type": "mixed", "confidence": round((n_flt + n_int) / n, 3),
                "note": f"{n - n_flt - n_int} non-numeric values in mostly-numeric column; inspect before aggregating"}
    return {"type": "text", "confidence": 1.0, "note": ""}


def profile_table(name: str, header: list[str], rows: list[dict]) -> dict:
    cols = {}
    for h in header:
        values = [r.get(h) for r in rows]
        vals = [v for v in values if v is not None and str(v).strip() != ""]
        t = infer_type(values)
        c = {"type": t["type"], "type_confidence": t["confidence"], "type_note": t["note"],
             "n": len(values), "n_missing": len(values) - len(vals),
             "missing_rate": round((len(values) - len(vals)) / len(values), 4) if values else None,
             "n_distinct": len({str(v) for v in vals})}
        nums = [float(v) for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums and t["type"] in ("integer", "float"):
            c["min"], c["max"] = min(nums), max(nums)
            c["mean"] = round(statistics.fmean(nums), 6)
            if len(nums) > 1:
                c["sd"] = round(statistics.stdev(nums), 6)
        cols[h] = c
    # 候选主键：无缺失且全唯一的列
    key_candidates = [h for h, c in cols.items()
                      if c["n_missing"] == 0 and c["n_distinct"] == c["n"] and c["n"] > 0]
    return {"table": name, "n_rows": len(rows), "n_cols": len(header),
            "columns": cols, "unit_hints": unit_hints(header),
            "key_candidates": key_candidates,
            "warnings": _warnings(name, cols, len(rows))}


def _warnings(name: str, cols: dict, n_rows: int) -> list[str]:
    w = []
    if n_rows == 0:
        w.append(f"{name}: empty table (0 data rows)")
    for h, c in cols.items():
        if c["type"] == "empty":
            w.append(f"{name}.{h}: column entirely missing")
        elif (c["missing_rate"] or 0) > 0.5:
            w.append(f"{name}.{h}: missing rate {c['missing_rate']:.0%} > 50%")
        if c["type"] == "mixed":
            w.append(f"{name}.{h}: mixed types — numeric ops would silently drop values")
    return w


def join_candidates(table_a: dict, rows_a: list[dict], table_b: dict, rows_b: list[dict]) -> list[dict]:
    """跨表连接键候选：名称（归一化后）相同或包含，值集有实际重叠，类型兼容。

    重叠率 = |valuesA ∩ valuesB| / min(|valuesA|, |valuesB|)；重叠为 0 的列对不推荐
    （防止把仅同名的列错当连接键导致笛卡尔膨胀）。
    """
    out = []

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    for ha in table_a["columns"]:
        va = {str(r.get(ha)) for r in rows_a if r.get(ha) not in (None, "")}
        if not va:
            continue
        for hb in table_b["columns"]:
            na, nb = norm(ha), norm(hb)
            if not na or not nb:
                continue
            name_sim = 1.0 if na == nb else (0.7 if (na in nb or nb in na) else 0.0)
            if name_sim < 0.7:
                continue
            vb = {str(r.get(hb)) for r in rows_b if r.get(hb) not in (None, "")}
            if not vb:
                continue
            overlap = len(va & vb) / min(len(va), len(vb))
            ta, tb = table_a["columns"][ha]["type"], table_b["columns"][hb]["type"]
            type_ok = ta == tb or {ta, tb} <= {"integer", "float"}
            conf = round(0.4 * name_sim + 0.4 * overlap + 0.2 * (1 if type_ok else 0), 3)
            out.append({"left": f"{table_a['table']}.{ha}", "right": f"{table_b['table']}.{hb}",
                        "name_similarity": name_sim, "value_overlap": round(overlap, 4),
                        "type_compatible": type_ok, "confidence": conf,
                        "note": "candidate only; agent must confirm semantic equivalence before joining"})
    out.sort(key=lambda x: -x["confidence"])
    return out


def _demo() -> int:
    header = ["sample_id", "conc (mg/L)", "batch", "measured_on"]
    rows = [{"sample_id": f"S{i:02d}", "conc (mg/L)": 1.5 + i * 0.1, "batch": "A" if i % 2 else "B",
             "measured_on": f"2024-03-{(i % 28) + 1:02d}"} for i in range(10)]
    rows[3]["conc (mg/L)"] = None  # 注入 1 个缺失
    prof = profile_table("measurements", header, rows)
    assert prof["n_rows"] == 10
    assert prof["columns"]["sample_id"]["type"] == "text"
    assert prof["columns"]["conc (mg/L)"]["type"] == "float"
    assert prof["columns"]["conc (mg/L)"]["n_missing"] == 1
    assert abs(prof["columns"]["conc (mg/L)"]["missing_rate"] - 0.1) < 1e-9
    assert prof["columns"]["measured_on"]["type"] == "date"
    assert prof["unit_hints"] == {"conc (mg/L)": "mg/L"}
    assert prof["key_candidates"] == ["sample_id", "measured_on"]
    # 跨表连接候选
    hdr2 = ["sample_id", "treatment"]
    rows2 = [{"sample_id": f"S{i:02d}", "treatment": "T1"} for i in range(10)]
    prof2 = profile_table("meta", hdr2, rows2)
    jc = join_candidates(prof, rows, prof2, rows2)
    assert jc and jc[0]["left"] == "measurements.sample_id" and jc[0]["value_overlap"] == 1.0, jc
    assert jc[0]["type_compatible"] is True
    # 空表与全缺失列
    p3 = profile_table("empty", ["a", "b"], [])
    assert p3["n_rows"] == 0 and any("empty table" in w for w in p3["warnings"])
    p4 = profile_table("t", ["x"], [{"x": None}, {"x": None}])
    assert p4["columns"]["x"]["type"] == "empty"
    print(json.dumps({"demo": "profile", "types": {h: prof["columns"][h]["type"] for h in header},
                      "units": prof["unit_hints"], "keys": prof["key_candidates"],
                      "join_top": jc[0]["left"] + " <-> " + jc[0]["right"],
                      "join_conf": jc[0]["confidence"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.profile tables.json out.json
    # tables.json: [{"name":..., "header":[...], "rows":[{...}]}, ...]
    tables = json.load(open(sys.argv[1], encoding="utf-8"))
    profiles, rows_by = [], {}
    for t in tables:
        profiles.append(profile_table(t["name"], t["header"], t["rows"]))
        rows_by[t["name"]] = t["rows"]
    joins = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            joins += join_candidates(profiles[i], rows_by[profiles[i]["table"]],
                                     profiles[j], rows_by[profiles[j]["table"]])
    rep = {"profiles": profiles, "join_candidates": joins}
    json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"profiled {len(profiles)} tables, {len(joins)} join candidates -> {sys.argv[2]}")
