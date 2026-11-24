"""SQLite 运行器：schema 自省、只读查询、行数与列出处、结果快照到 CSV。

纪律（对应数据库查询题的判据）：
- 连接一律以 URI mode=ro 只读打开：本 Skill 只分析授权快照，绝不写库。
- 查询前必须先 introspect：表、列、类型、主键、外键、行数 —— 不许猜表名/字段名。
- 每个查询记录：SQL 原文、返回行数、列名与（可推断时的）来源表列出处、耗时、
  错误现场（出错时保留 sqlite3 错误消息，不得改写后重试冒充一次成功）。
- 结果快照落 CSV，带 sha256，行数与 CSV 行数一致性自检。
- 行数膨胀检查：join 结果行数 > 各基表行数之和时给 one-to-many 膨胀警告。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import sys
import time

DEFAULT_ROW_LIMIT = 10000


def connect_ro(db_path: str) -> sqlite3.Connection:
    """只读连接；文件不存在时直接报错而不是静默建空库。"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite snapshot not found: {db_path} (refusing to create an empty db)")
    uri = "file:" + os.path.abspath(db_path).replace("?", "%3f") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def introspect(db_path: str) -> dict:
    conn = connect_ro(db_path)
    try:
        cur = conn.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') "
                           "AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = []
        for name, ttype in cur.fetchall():
            cols = [{"name": r[1], "declared_type": r[2], "notnull": bool(r[3]),
                     "pk": bool(r[5])} for r in conn.execute(f"PRAGMA table_info({name})")]
            fks = [{"from": r[3], "to_table": r[2], "to": r[4]}
                   for r in conn.execute(f"PRAGMA foreign_key_list({name})")]
            n = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            tables.append({"name": name, "type": ttype, "n_rows": n,
                           "columns": cols, "foreign_keys": fks,
                           "pk_columns": [c["name"] for c in cols if c["pk"]]})
        return {"db": os.path.abspath(db_path), "n_tables": len(tables), "tables": tables,
                "note": "read from sqlite_master/PRAGMA on the actual snapshot; never guessed"}
    finally:
        conn.close()


def run_query(db_path: str, sql: str, row_limit: int = DEFAULT_ROW_LIMIT) -> dict:
    """执行单条只读查询。拒绝多语句与写操作关键字。"""
    head = sql.strip().split(None, 1)[0].upper() if sql.strip() else ""
    if ";" in sql.strip().rstrip(";"):
        return {"ok": False, "error": "multiple statements refused", "sql": sql}
    if head not in ("SELECT", "WITH", "PRAGMA", "EXPLAIN"):
        return {"ok": False, "error": f"read-only runner: statement starts with {head!r}, "
                                      "only SELECT/WITH/PRAGMA/EXPLAIN allowed", "sql": sql}
    conn = connect_ro(db_path)
    t0 = time.time()
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(row_limit + 1)
        truncated = len(rows) > row_limit
        rows = rows[:row_limit]
        rec = {"ok": True, "sql": sql, "columns": cols, "n_rows": len(rows),
               "truncated_at_limit": truncated, "elapsed_ms": round((time.time() - t0) * 1000, 2),
               "rows": [list(r) for r in rows]}
        # 列出处：把结果列名映射回基表列（同名列全部列出，标注歧义）
        rec["column_provenance"] = _column_provenance(db_path, cols)
        # join 膨胀检查
        rec["row_inflation_check"] = _inflation_check(db_path, sql, len(rows))
        return rec
    except sqlite3.Error as e:
        return {"ok": False, "sql": sql, "error": f"sqlite3: {e}",
                "error_type": type(e).__name__,
                "note": "error preserved verbatim; fix and rerun, do not paper over"}
    finally:
        conn.close()


def _column_provenance(db_path: str, cols: list[str]) -> dict:
    try:
        info = introspect(db_path)
    except Exception:
        return {}
    prov = {}
    for c in cols:
        hits = [f"{t['name']}.{col['name']}" for t in info["tables"]
                for col in t["columns"] if col["name"] == c]
        prov[c] = {"candidates": hits,
                   "ambiguous": len(hits) > 1,
                   "note": "ambiguous" if len(hits) > 1 else ""}
    return prov


def _inflation_check(db_path: str, sql: str, n_out: int) -> dict:
    """粗粒度 one-to-many 膨胀提示：若 SQL 含 JOIN 且输出行数超过涉及基表最大行数。"""
    if "join" not in sql.lower():
        return {"checked": False}
    try:
        info = introspect(db_path)
    except Exception:
        return {"checked": False}
    names = [t["name"] for t in info["tables"]]
    involved = [t for t in info["tables"] if t["name"].lower() in sql.lower()]
    if not involved:
        return {"checked": True, "note": "could not identify joined tables in SQL text"}
    max_base = max(t["n_rows"] for t in involved)
    inflated = n_out > max_base
    return {"checked": True, "base_tables": {t["name"]: t["n_rows"] for t in involved},
            "max_base_rows": max_base, "result_rows": n_out,
            "inflation_flag": inflated,
            "note": "result rows > largest base table: verify join keys are the intended cardinality"
            if inflated else "row count within base-table cardinality"}


def snapshot_csv(query_result: dict, csv_path: str) -> dict:
    """结果集落 CSV + 行数一致性自检 + sha256。"""
    assert query_result.get("ok"), "cannot snapshot a failed query"
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(query_result["columns"])
        w.writerows(query_result["rows"])
    with open(csv_path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    with open(csv_path, encoding="utf-8") as fh:
        n_data_lines = sum(1 for _ in fh) - 1
    ok = n_data_lines == query_result["n_rows"]
    return {"csv": os.path.abspath(csv_path), "sha256": digest, "n_rows_csv": n_data_lines,
            "n_rows_query": query_result["n_rows"], "consistent": ok,
            "note": "csv row count must equal query row count" if ok else "ROW COUNT MISMATCH"}


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="dakit-db-")
    db = os.path.join(tmp, "toy.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE samples (sample_id TEXT PRIMARY KEY, batch TEXT)")
    conn.execute("CREATE TABLE measures (sample_id TEXT, value REAL, "
                 "FOREIGN KEY(sample_id) REFERENCES samples(sample_id))")
    conn.executemany("INSERT INTO samples VALUES (?,?)",
                     [(f"S{i}", "A" if i % 2 else "B") for i in range(10)])
    conn.executemany("INSERT INTO measures VALUES (?,?)",
                     [(f"S{i}", 1.0 + i * 0.1) for i in range(10)]
                     + [("S1", 9.9)])  # S1 两条 → join 膨胀
    conn.commit()
    conn.close()
    info = introspect(db)
    assert info["n_tables"] == 2
    assert {t["name"]: t["n_rows"] for t in info["tables"]} == {"samples": 10, "measures": 11}
    sm = next(t for t in info["tables"] if t["name"] == "samples")
    assert sm["pk_columns"] == ["sample_id"]
    ms = next(t for t in info["tables"] if t["name"] == "measures")
    assert ms["foreign_keys"][0]["to_table"] == "samples"
    # 聚合查询
    q = run_query(db, "SELECT batch, COUNT(*) c, AVG(value) FROM samples "
                      "JOIN measures USING(sample_id) GROUP BY batch ORDER BY batch")
    assert q["ok"] and q["n_rows"] == 2, q
    assert q["columns"] == ["batch", "c", "AVG(value)"]
    assert q["rows"][0][0] == "A" and q["rows"][0][1] == 6  # A 批 5 样本 + S1 重复
    assert q["row_inflation_check"]["checked"] is True
    assert q["column_provenance"]["batch"]["candidates"] == ["samples.batch"]
    # 快照一致性
    snap = snapshot_csv(q, os.path.join(tmp, "by_batch.csv"))
    assert snap["consistent"] and snap["n_rows_csv"] == 2
    # 错误现场保留
    bad = run_query(db, "SELECT nope FROM samples")
    assert not bad["ok"] and "no such column" in bad["error"]
    wr = run_query(db, "DELETE FROM samples")
    assert not wr["ok"] and "read-only" in wr["error"]
    # 缺失文件不静默建库
    try:
        introspect(os.path.join(tmp, "ghost.db"))
        raise SystemExit("should have raised")
    except FileNotFoundError:
        pass
    print(json.dumps({"demo": "dbrun", "tables": info["n_tables"],
                      "query_rows": q["n_rows"], "batch_A_count": q["rows"][0][1],
                      "snapshot_consistent": snap["consistent"],
                      "write_refused": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.dbrun introspect <db> <out.json>
    #        python -m dakit.dbrun query <db> <sql|@file.sql> <out.json> [csv]
    cmd = sys.argv[1]
    if cmd == "introspect":
        rep = introspect(sys.argv[2])
        json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{rep['n_tables']} tables -> {sys.argv[3]}")
    elif cmd == "query":
        sql = open(sys.argv[3][1:], encoding="utf-8").read() if sys.argv[3].startswith("@") else sys.argv[3]
        rep = run_query(sys.argv[2], sql)
        json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if rep["ok"] and len(sys.argv) > 5:
            snap = snapshot_csv(rep, sys.argv[5])
            print(f"snapshot {snap['n_rows_csv']} rows sha256:{snap['sha256'][:12]} -> {sys.argv[5]}")
        print(f"query ok={rep['ok']} rows={rep.get('n_rows')} -> {sys.argv[4]}")
    else:
        raise SystemExit(f"unknown subcommand {cmd!r}")
