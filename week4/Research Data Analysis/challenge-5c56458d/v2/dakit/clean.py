"""清洗账本：规则外置为 JSON 数据；每条规则应用都记录受影响行 id、前后行数、分布影响。

规则文件（数据，不是硬编码）示例：
{"rules": [
  {"id": "r1", "type": "missing",  "column": "value", "strategy": "drop_rows"},
  {"id": "r2", "type": "outlier",  "column": "value", "method": "iqr", "strategy": "flag"},
  {"id": "r3", "type": "duplicate","keys": ["sample_id"], "keep": "first"}
]}

支持：
- missing:   detect = null/空串/可配置哨兵值（如 -999, "NA"）；strategy ∈
             drop_rows | fill_value(v) | fill_mean | fill_median | flag
- outlier:   method = iqr（1.5×IQR 栅栏）| zscore（|z|>k，默认 3）；
             strategy ∈ drop | cap | flag。异常判据基于清洗前分布计算并记入账本。
- duplicate: keys = 真实主键列；keep = first|last；多余的行 drop 或 flag。

账本每条：{rule_id, type, column/keys, strategy, affected_row_ids, before_n,
after_n, filled/dropped/flagged 计数, distribution_before/after（数值列的
n/mean/sd），note}。任何静默丢行都是 bug：drop 的行 id 全部列出。
"""
from __future__ import annotations

import json
import statistics
import sys

MISSING_SENTINELS_DEFAULT = ["", "NA", "N/A", "na", "null", "None", "-999", "-999.0", "nan"]


def _is_missing(v, sentinels) -> bool:
    if v is None:
        return True
    return str(v).strip() in sentinels


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _dist(rows, column):
    nums = [_num(r.get(column)) for r in rows]
    nums = [x for x in nums if x is not None]
    if not nums:
        return {"n": 0}
    d = {"n": len(nums), "mean": round(statistics.fmean(nums), 6),
         "min": min(nums), "max": max(nums)}
    if len(nums) > 1:
        d["sd"] = round(statistics.stdev(nums), 6)
    return d


def _row_ids(rows):
    return [r.get("_row_id", i) for i, r in enumerate(rows)]


def _apply_missing(rows, rule, ledger_entry):
    col = rule["column"]
    strat = rule.get("strategy", "flag")
    sentinels = set(rule.get("sentinels") or MISSING_SENTINELS_DEFAULT)
    affected = [r.get("_row_id", i) for i, r in enumerate(rows) if _is_missing(r.get(col), sentinels)]
    ledger_entry["affected_row_ids"] = affected
    ledger_entry["n_affected"] = len(affected)
    if strat == "drop_rows":
        keep = [r for i, r in enumerate(rows) if r.get("_row_id", i) not in set(affected)]
        ledger_entry["action"] = f"dropped {len(affected)} rows"
        return keep
    if strat.startswith("fill"):
        non_missing = [_num(r.get(col)) for r in rows
                       if not _is_missing(r.get(col), sentinels) and _num(r.get(col)) is not None]
        if strat == "fill_value":
            fill = rule.get("value")
            assert fill is not None, "fill_value requires rule.value"
        elif strat == "fill_mean":
            assert non_missing, f"cannot fill_mean {col}: no numeric values"
            fill = statistics.fmean(non_missing)
        else:  # fill_median
            assert non_missing, f"cannot fill_median {col}: no numeric values"
            fill = statistics.median(non_missing)
        for r in rows:
            if r.get("_row_id", rows.index(r)) in set(affected):
                r[col] = fill
                r.setdefault("_clean_flags", []).append(f"{rule['id']}:filled")
        ledger_entry["action"] = f"filled {len(affected)} cells with {fill!r}"
        ledger_entry["fill_value"] = fill
        return rows
    # flag only
    for r in rows:
        if r.get("_row_id", rows.index(r)) in set(affected):
            r.setdefault("_clean_flags", []).append(f"{rule['id']}:missing")
    ledger_entry["action"] = f"flagged {len(affected)} cells, values unchanged"
    return rows


def _apply_outlier(rows, rule, ledger_entry):
    col = rule["column"]
    method = rule.get("method", "iqr")
    strat = rule.get("strategy", "flag")
    nums = [(i, _num(r.get(col))) for i, r in enumerate(rows)]
    nums = [(i, x) for i, x in nums if x is not None]
    vals = [x for _, x in nums]
    if len(vals) < 4:
        ledger_entry["action"] = "skipped: fewer than 4 numeric values, fences unreliable"
        ledger_entry["affected_row_ids"] = []
        return rows
    if method == "iqr":
        q = statistics.quantiles(vals, n=4)
        q1, q3 = q[0], q[2]
        iqr = q3 - q1
        k = float(rule.get("k", 1.5))
        lo, hi = q1 - k * iqr, q3 + k * iqr
        crit = f"IQR fence: [{round(lo, 6)}, {round(hi, 6)}] (k={k})"
    else:  # zscore
        mu, sd = statistics.fmean(vals), statistics.stdev(vals)
        k = float(rule.get("k", 3.0))
        lo, hi = mu - k * sd, mu + k * sd
        crit = f"z-score |z|>{k}: [{round(lo, 6)}, {round(hi, 6)}]"
    ledger_entry["criterion"] = crit
    affected = [rows[i].get("_row_id", i) for i, x in nums if x < lo or x > hi]
    ledger_entry["affected_row_ids"] = affected
    ledger_entry["n_affected"] = len(affected)
    aset = set(affected)
    if strat == "drop":
        ledger_entry["action"] = f"dropped {len(affected)} outlier rows"
        return [r for i, r in enumerate(rows) if r.get("_row_id", i) not in aset]
    if strat == "cap":
        for r in rows:
            if r.get("_row_id", rows.index(r)) in aset:
                x = _num(r.get(col))
                r[col] = lo if x < lo else hi
                r.setdefault("_clean_flags", []).append(f"{rule['id']}:capped")
        ledger_entry["action"] = f"capped {len(affected)} values to fences"
        return rows
    for r in rows:
        if r.get("_row_id", rows.index(r)) in aset:
            r.setdefault("_clean_flags", []).append(f"{rule['id']}:outlier")
    ledger_entry["action"] = f"flagged {len(affected)} rows, values unchanged"
    return rows


def _apply_duplicate(rows, rule, ledger_entry):
    keys = rule["keys"]
    keep = rule.get("keep", "first")
    seen, dup_ids = {}, []
    ordered = rows if keep == "first" else list(reversed(rows))
    for i, r in enumerate(ordered):
        sig = tuple(str(r.get(k, "")).strip().lower() for k in keys)
        if sig in seen:
            dup_ids.append(r.get("_row_id", i))
        else:
            seen[sig] = True
    ledger_entry["affected_row_ids"] = dup_ids
    ledger_entry["n_affected"] = len(dup_ids)
    ledger_entry["criterion"] = f"duplicate on keys {keys}, keep={keep}"
    if rule.get("strategy", "drop") == "drop":
        ledger_entry["action"] = f"dropped {len(dup_ids)} duplicate rows"
        dset = set(dup_ids)
        return [r for i, r in enumerate(rows) if r.get("_row_id", i) not in dset]
    for r in rows:
        if r.get("_row_id", rows.index(r)) in set(dup_ids):
            r.setdefault("_clean_flags", []).append(f"{rule['id']}:duplicate")
    ledger_entry["action"] = f"flagged {len(dup_ids)} duplicate rows, kept all"
    return rows


_HANDLERS = {"missing": _apply_missing, "outlier": _apply_outlier, "duplicate": _apply_duplicate}


def run_rules(rows: list[dict], rules: list[dict]) -> dict:
    """顺序应用规则，返回 {rows, ledger}。rows 被复制，输入不被修改。"""
    rows = [dict(r) for r in rows]
    for i, r in enumerate(rows):
        r.setdefault("_row_id", i)
    ledger = []
    for rule in rules:
        handler = _HANDLERS.get(rule["type"])
        assert handler, f"unknown rule type {rule['type']!r} (allowed: {sorted(_HANDLERS)})"
        col = rule.get("column") or "+".join(rule.get("keys") or [])
        entry = {"rule_id": rule.get("id"), "type": rule["type"], "column": col,
                 "strategy": rule.get("strategy", rule.get("keep", "")),
                 "before_n": len(rows),
                 "distribution_before": _dist(rows, col) if rule.get("column") else None}
        rows = handler(rows, rule, entry)
        entry["after_n"] = len(rows)
        entry["distribution_after"] = _dist(rows, col) if rule.get("column") else None
        ledger.append(entry)
    return {"rows": rows, "ledger": ledger,
            "ledger_note": "every rule lists affected _row_id values; nothing is dropped silently"}


def _demo() -> int:
    # 已知答案的微型数据集：12 行，1 缺失（行2），1 异常（行11 值 100），1 重复（行5=行1键）
    rows = [{"sample_id": f"S{i}", "value": v} for i, v in
            enumerate([1.0, 1.1, None, 1.2, 0.9, 1.1, 1.0, 1.3, 0.8, 1.15, 1.05, 100.0])]
    rows[5]["sample_id"] = "S1"  # 与行1键重复
    rules = [
        {"id": "dup1", "type": "duplicate", "keys": ["sample_id"], "keep": "first"},
        {"id": "mis1", "type": "missing", "column": "value", "strategy": "drop_rows"},
        {"id": "out1", "type": "outlier", "column": "value", "method": "iqr", "strategy": "flag"},
    ]
    rep = run_rules(rows, rules)
    l0, l1, l2 = rep["ledger"]
    assert l0["affected_row_ids"] == [5] and l0["after_n"] == 11, l0
    assert l1["affected_row_ids"] == [2] and l1["after_n"] == 10, l1
    assert l2["affected_row_ids"] == [11] and l2["after_n"] == 10, l2  # flag 不删行
    assert rep["rows"][-1]["_clean_flags"] == ["out1:outlier"]
    # 分布影响已记录：outlier flag 前后 mean 不变
    assert l2["distribution_before"]["mean"] == l2["distribution_after"]["mean"]
    # 缺失填补口径
    rep2 = run_rules(rows[:4], [{"id": "m", "type": "missing", "column": "value",
                                 "strategy": "fill_median"}])
    assert rep2["rows"][2]["value"] == 1.1  # median(1.0,1.1,1.2)
    assert rep2["ledger"][0]["fill_value"] == 1.1
    print(json.dumps({"demo": "clean", "ledger": [
        {"rule": e["rule_id"], "affected": e["affected_row_ids"],
         "before": e["before_n"], "after": e["after_n"]} for e in rep["ledger"]],
        "fill_median": rep2["ledger"][0]["fill_value"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.clean table.json rules.json out.json
    # table.json: {"header":[...], "rows":[{...}]}; rules.json: {"rules":[...]}
    table = json.load(open(sys.argv[1], encoding="utf-8"))
    rules = json.load(open(sys.argv[2], encoding="utf-8"))["rules"]
    rep = run_rules(table["rows"], rules)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"applied {len(rules)} rules: {rep['ledger'][0]['before_n'] if rules else len(table['rows'])}"
          f" -> {rep['ledger'][-1]['after_n'] if rules else len(table['rows'])} rows -> {sys.argv[3]}")
