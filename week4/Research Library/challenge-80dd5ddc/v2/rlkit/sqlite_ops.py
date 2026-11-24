"""SQLite target operations: transactional, idempotent migration with proof.

Targets in this track are real SQLite files (Zotero's store, the organizer's
initial target DB, a Datasette backend).  Guarantees:
  * transactional — one transaction per batch; any failure rolls the whole
    batch back and is recorded, never leaving half-written state;
  * idempotent — upsert key = identity key (doi > normalised title); re-running
    the same migration reports status "unchanged", not fake new inserts;
  * verifiable — pre/post row counts, per-record status, and verify() compares
    the DB against the expected record set and reports exact diffs;
  * honest conflicts — an existing row whose content differs is updated only
    under policy="update", otherwise logged as a conflict and kept as-is.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys

from .identity import norm_doi, norm_title

COLUMNS = ["item_key", "title", "authors", "year", "venue", "doi", "tags", "extra_json"]


def ident_key(rec: dict) -> str:
    d = norm_doi(rec.get("doi", ""))
    if d:
        return "doi:" + d
    t = norm_title(rec.get("title", ""))
    return "title:" + t if t else "key:" + str(rec.get("item_key") or id(rec))


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS items (
        ident TEXT PRIMARY KEY, item_key TEXT, title TEXT, authors TEXT,
        year TEXT, venue TEXT, doi TEXT, tags TEXT, extra_json TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS migration_log (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT, ident TEXT,
        status TEXT, detail TEXT)""")
    return conn


def _row_of(rec: dict, ident: str) -> tuple:
    authors = rec.get("authors") or []
    if isinstance(authors, list):
        authors = "; ".join(str(a) for a in authors)
    tags = rec.get("tags") or []
    if isinstance(tags, list):
        tags = "; ".join(str(t) for t in tags)
    return (ident, str(rec.get("item_key") or ""), str(rec.get("title") or ""),
            authors, str(rec.get("year") or ""), str(rec.get("venue") or ""),
            norm_doi(rec.get("doi", "")), tags,
            json.dumps(rec.get("extra", {}), ensure_ascii=False, sort_keys=True))


def migrate(records: list, db_path: str, batch: str = "batch-1",
            policy: str = "update") -> dict:
    """policy: 'update' overwrite differing rows; 'keep' leave them + conflict log."""
    assert policy in ("update", "keep")
    conn = open_db(db_path)
    pre = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    results, conflicts = [], []
    try:
        with conn:  # one transaction; exception -> rollback
            for rec in records:
                ident = ident_key(rec)
                new = _row_of(rec, ident)
                old = conn.execute("SELECT * FROM items WHERE ident=?", (ident,)).fetchone()
                if old is None:
                    conn.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?)", new)
                    status = "inserted"
                elif tuple(old) == new:
                    status = "unchanged"
                elif policy == "update":
                    conn.execute("REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,?)", new)
                    status = "updated"
                else:
                    status = "conflict_kept"
                    conflicts.append({"ident": ident, "old": old[2], "new": new[2],
                                      "policy": policy})
                conn.execute("INSERT INTO migration_log (batch,ident,status,detail) "
                             "VALUES (?,?,?,?)", (batch, ident, status,
                                                  str(rec.get("title", ""))[:80]))
                results.append({"ident": ident, "status": status,
                                "title": str(rec.get("title", ""))[:60]})
    except sqlite3.Error as exc:
        conn.close()
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "rolled_back": True, "batch": batch,
                "note": "transaction aborted; database left at pre-batch state"}
    post = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    conn.close()
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"ok": True, "batch": batch, "policy": policy, "results": results,
            "conflicts": conflicts,
            "report": {"pre_rows": pre, "post_rows": post, "delta": post - pre,
                       "input": len(records), **counts}}


def verify(db_path: str, expected: list) -> dict:
    """Compare DB content with the expected record set; return exact diffs."""
    conn = open_db(db_path)
    rows = {r[0]: r for r in conn.execute("SELECT * FROM items")}
    conn.close()
    missing, mismatched = [], []
    for rec in expected:
        ident = ident_key(rec)
        if ident not in rows:
            missing.append({"ident": ident, "title": str(rec.get("title", ""))[:60]})
        elif tuple(rows[ident]) != _row_of(rec, ident):
            mismatched.append({"ident": ident, "title": str(rec.get("title", ""))[:60]})
    return {"ok": not missing and not mismatched, "db_rows": len(rows),
            "expected": len(expected), "missing": missing, "mismatched": mismatched}


def export_csv(db_path: str, csv_path: str, table: str = "items") -> dict:
    """CSV export for downstream targets (e.g. Datasette / 台账交接)."""
    conn = open_db(db_path)
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY ident").fetchall()
    cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
    conn.close()
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    return {"csv": os.path.abspath(csv_path), "rows": len(rows), "columns": cols,
            "bytes": os.path.getsize(csv_path)}


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sqlite-demo-")
    db = os.path.join(tmp, "lib.sqlite")
    recs = [{"item_key": "A1", "title": "Deep Learning for Proteins", "doi": "10.1000/xyz.1",
             "authors": ["Smith, John"], "year": "2021"},
            {"item_key": "B2", "title": "Another Study", "year": "2019"}]
    r1 = migrate(recs, db, batch="b1")
    assert r1["ok"] and r1["report"]["inserted"] == 2 and r1["report"]["post_rows"] == 2
    r2 = migrate(recs, db, batch="b2")            # idempotent re-run
    assert r2["report"]["unchanged"] == 2 and r2["report"]["delta"] == 0, r2["report"]
    recs2 = [dict(recs[0], venue="Nature")]        # changed row
    r3 = migrate(recs2, db, batch="b3", policy="keep")
    assert r3["report"]["conflict_kept"] == 1 and len(r3["conflicts"]) == 1
    v = verify(db, recs)
    assert v["ok"], v                              # DB still matches original set
    out_csv = os.path.join(tmp, "export.csv")
    e = export_csv(db, out_csv)
    assert e["rows"] == 2 and e["bytes"] > 0 and os.path.exists(out_csv)
    print(json.dumps({"demo": "sqlite_ops.migrate+verify+export",
                      "b1": r1["report"], "b2_unchanged": r2["report"]["unchanged"],
                      "conflicts_kept": len(r3["conflicts"]), "verify_ok": v["ok"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "migrate":
        data = json.load(open(sys.argv[2], encoding="utf-8"))
        recs = data.get("records", data) if isinstance(data, dict) else data
        policy = "keep" if "--keep" in sys.argv else "update"
        batch = sys.argv[sys.argv.index("--batch") + 1] if "--batch" in sys.argv else "batch-1"
        json.dump(migrate(recs, sys.argv[3], batch, policy),
                  open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"migrate: {len(recs)} records -> {sys.argv[3]} (log {sys.argv[4]})")
    elif cmd == "verify":
        exp = json.load(open(sys.argv[3], encoding="utf-8"))
        exp = exp.get("records", exp) if isinstance(exp, dict) else exp
        print(json.dumps(verify(sys.argv[2], exp), ensure_ascii=False, indent=1))
    elif cmd == "export":
        print(json.dumps(export_csv(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    else:
        print("usage: sqlite_ops.py migrate <recs.json> <db> <log.json> [--keep] [--batch b] "
              "| verify <db> <expected.json> | export <db> <csv>")
        sys.exit(2)
