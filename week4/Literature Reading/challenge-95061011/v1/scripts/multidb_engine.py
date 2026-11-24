#!/usr/bin/env python3
"""multidb-union-search-forge: cross-db field mapping, merge with priority, provenance.

Deterministic subcommands (0 model requests):
  --demo                    run built-in demo (3 fake DB records)
  --merge RECORDS_JSON      merge duplicates with field-value priority & conflict resolution
  --degrade DBS_JSON        failure-degradation report: which db failed, what gap it leaves
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata

FIELD_MAP = {
    "title": ["title", "TI", "article-title", "dc:title"],
    "doi": ["doi", "DOI", "dc:identifier", "prism:doi"],
    "authors": ["authors", "author", "AU", "creator", "dc:creator"],
    "year": ["year", "pub_year", "publication_year", "date", "PY"],
    "journal": ["journal", "container-title", "source", "SO", "venue"],
    "type": ["type", "pubtype", "document_type", "record_type"],
    "abstract": ["abstract", "AB", "summary"],
}
PRIORITY = {"doi": 1, "title": 2, "year": 3, "journal": 4, "type": 5, "authors": 6, "abstract": 7}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()


def map_record(rec):
    db = rec.get("db", "?")
    raw = rec.get("raw", rec)
    out = {"db": db, "fields": {}, "provenance": {}}
    for canon, aliases in FIELD_MAP.items():
        val, src_alias = None, None
        for a in aliases:
            if a in raw and raw[a] not in (None, ""):
                val, src_alias = raw[a], a
                break
        out["fields"][canon] = norm(str(val)) if val is not None else None
        out["provenance"][canon] = {"source_db": db, "source_alias": src_alias} if val is not None else {"source_db": None, "source_alias": None, "note": "missing (字段在原始记录中不存在)"}
    return out


def merge_value(canon, candidates):
    vals = [(db, v) for db, v in candidates if v not in (None, "")]
    if not vals:
        return None, "all_missing"
    vals.sort(key=lambda x: PRIORITY.get(canon, 99))
    chosen_db, chosen = vals[0]
    conflict = len({norm(str(v)) for _, v in vals}) > 1
    rule = "field_priority" if not conflict else f"conflict_resolved(priority={canon}_order, first={chosen_db})"
    return chosen, f"{rule} (from {chosen_db}, alternatives={[d for d, _ in vals[1:]][:3]})"


def cmd_merge(normed):
    groups = {}
    for r in normed:
        f = r["fields"]
        t = (f.get("title") or "").lower()
        k = ("doi:" + (f.get("doi") or "")) if f.get("doi") else ("title:" + re.sub(r"[^\w\s]", "", t)[:60])
        groups.setdefault(k, []).append(r)
    merged, conflicts = [], []
    for k, members in groups.items():
        rec = {"merge_key": k, "n_sources": len(members), "source_dbs": [m["db"] for m in members], "fields": {}, "field_merge_log": {}}
        for canon in FIELD_MAP:
            cands = [(m["db"], m["fields"].get(canon)) for m in members]
            val, rule = merge_value(canon, cands)
            rec["fields"][canon] = val
            rec["field_merge_log"][canon] = rule
            if rule.startswith("conflict"):
                conflicts.append({"key": k, "field": canon, "rule": rule})
        merged.append(rec)
    print(json.dumps({"schema": "multidb/merge@1", "n_input": len(normed), "n_merged": len(merged),
                      "n_conflicts": len(conflicts), "merged": merged, "conflicts": conflicts[:30]},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_degrade(spec):
    dbs = spec if isinstance(spec, list) else spec.get("dbs", [])
    report = []
    for d in dbs:
        st = d.get("status", "ok")
        entry = {"db": d.get("db"), "status": st}
        if st != "ok":
            entry["gap"] = f"{d.get('db')} 不可用({d.get('error', '')}): 该库特有覆盖缺失，结果标记 incomplete"
            entry["action"] = "结果集标注 coverage_gap_sources；不静默返回不完整结果"
        report.append(entry)
    failed = [r for r in report if r["status"] != "ok"]
    print(json.dumps({"schema": "multidb/degrade@1", "dbs": report,
                      "overall": "incomplete" if failed else "complete",
                      "n_failed": len(failed),
                      "disclosure": "失败库已在结果中显式披露缺口" if failed else "全库可用"},
                     ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--merge")
    ap.add_argument("--degrade")
    a = ap.parse_args()
    if a.demo:
        demo = [
            {"db": "PubMed", "raw": {"TI": "Deep learning for imaging", "DOI": "10.1/x", "AU": "Zhang;Li", "PY": "2023", "AB": ""}},
            {"db": "Scopus", "raw": {"title": "deep learning  for imaging", "doi": "10.1/x", "year": "2023", "journal": "Radiology AI"}},
            {"db": "WoS", "raw": {"title": "DL imaging review", "year": "2024"}},
        ]
        normed = [map_record(r) for r in demo]
        return cmd_merge(normed)
    if a.merge:
        return cmd_merge(json.load(open(a.merge, encoding="utf-8")))
    if a.degrade:
        return cmd_degrade(json.load(open(a.degrade, encoding="utf-8")))
    ap.error("choose --demo / --merge / --degrade")


if __name__ == "__main__":
    sys.exit(main())
