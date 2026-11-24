"""Metadata repair from case-provided API snapshots (offline, no network).

The case ships frozen snapshots (crossref-like JSON, RIS, publisher pages
saved as files).  repair_records matches each library record to a snapshot
(by DOI first, then normalised title) and fills fields under an explicit
policy:
  fill_missing   only fill fields that are empty in the record (default —
                 never overwrite a field that already has a value)
  prefer_snap    snapshot value wins, old value kept in the conflict log
Every filled field records {field, from_snapshot, value}; every collision is
logged, never silently overwritten.  Records with no matching snapshot are
reported as unrepaired with the reason — honest gaps, not invented metadata.
"""
from __future__ import annotations

import json
import sys

from .identity import norm_doi, norm_title

REPAIRABLE_FIELDS = ["title", "authors", "year", "venue", "doi", "url", "abstract",
                     "volume", "issue", "pages", "publisher", "issn", "item_type"]


def load_snapshots(items) -> list:
    """Snapshots: [{snapshot_id, source, frozen_at, record:{...}}] or bare records."""
    out = []
    for i, s in enumerate(items):
        if isinstance(s, dict) and "record" in s:
            out.append({"snapshot_id": s.get("snapshot_id") or f"snap{i + 1}",
                        "source": s.get("source", "unknown"),
                        "frozen_at": s.get("frozen_at", ""),
                        "record": s["record"]})
        else:
            out.append({"snapshot_id": f"snap{i + 1}", "source": "unknown",
                        "frozen_at": "", "record": s})
    return out


def find_snapshot(rec: dict, snaps: list) -> tuple:
    d = norm_doi(rec.get("doi", ""))
    if d:
        for s in snaps:
            if norm_doi(s["record"].get("doi", "")) == d:
                return s, "doi_exact"
    t = norm_title(rec.get("title", ""))
    if t:
        for s in snaps:
            if norm_title(s["record"].get("title", "")) == t:
                return s, "title_exact"
    return None, ""


def repair_record(rec: dict, snaps: list, policy: str = "fill_missing") -> dict:
    assert policy in ("fill_missing", "prefer_snap")
    snap, rule = find_snapshot(rec, snaps)
    out = dict(rec)
    fills, conflicts = [], []
    if snap is None:
        out["_repair"] = {"status": "unrepaired", "reason": "no_matching_snapshot",
                          "matched": False}
        return out
    srec = snap["record"]
    for f in REPAIRABLE_FIELDS:
        sv = srec.get(f)
        if sv in (None, "", []):
            continue
        rv = out.get(f)
        if rv in (None, "", []):
            out[f] = sv
            fills.append({"field": f, "value": sv, "from_snapshot": snap["snapshot_id"],
                          "source": snap["source"], "match_rule": rule})
        elif json.dumps(rv, ensure_ascii=False) != json.dumps(sv, ensure_ascii=False):
            if policy == "prefer_snap":
                conflicts.append({"field": f, "kept": sv, "discarded": rv,
                                  "policy": policy, "from_snapshot": snap["snapshot_id"]})
                out[f] = sv
            else:
                conflicts.append({"field": f, "kept": rv, "snapshot_value": sv,
                                  "policy": policy, "from_snapshot": snap["snapshot_id"]})
    out["_repair"] = {"status": "repaired" if fills else "verified_no_change",
                      "matched": True, "match_rule": rule,
                      "snapshot_id": snap["snapshot_id"], "fills": fills,
                      "conflicts": conflicts}
    return out


def repair_records(records: list, snapshots, policy: str = "fill_missing") -> dict:
    snaps = load_snapshots(snapshots)
    out = [repair_record(r, snaps, policy) for r in records]
    n_fill = sum(len(r["_repair"].get("fills", [])) for r in out)
    return {"records": out,
            "report": {"input": len(records), "snapshots": len(snaps), "policy": policy,
                       "repaired": sum(1 for r in out if r["_repair"]["status"] == "repaired"),
                       "verified_no_change": sum(1 for r in out if r["_repair"]["status"] == "verified_no_change"),
                       "unrepaired": sum(1 for r in out if r["_repair"]["status"] == "unrepaired"),
                       "fields_filled": n_fill,
                       "conflicts": sum(len(r["_repair"].get("conflicts", [])) for r in out)}}


def _demo() -> int:
    records = [
        {"item_key": "A1", "title": "Deep Learning for Proteins", "doi": "10.1000/xyz.1",
         "venue": ""},                                   # venue missing -> fill
        {"item_key": "B2", "title": "Deep Learning for Proteins", "year": "2020"},
        # title matches snapshot but year differs -> conflict, kept under fill_missing
        {"item_key": "C3", "title": "Totally Unknown Work"},  # no snapshot -> unrepaired
    ]
    snaps = [{"snapshot_id": "crossref-2024-01", "source": "crossref", "frozen_at": "2024-01-01",
              "record": {"title": "Deep Learning for Proteins", "doi": "10.1000/xyz.1",
                         "venue": "Nature", "year": "2021", "authors": ["Smith, John"]}}]
    out = repair_records(records, snaps, policy="fill_missing")
    rep = out["report"]
    assert rep["repaired"] == 2 and rep["unrepaired"] == 1, rep
    r0 = out["records"][0]
    assert r0["venue"] == "Nature" and r0["year"] == "2021"
    r1 = out["records"][1]
    assert r1["year"] == "2020"  # existing value preserved
    assert any(c["field"] == "year" for c in r1["_repair"]["conflicts"])
    print(json.dumps({"demo": "metarepair.repair", **rep}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    policy = "prefer_snap" if "--prefer-snap" in sys.argv else "fill_missing"
    data = json.load(open(argv[0], encoding="utf-8"))
    recs = data.get("records", data) if isinstance(data, dict) else data
    snaps = json.load(open(argv[1], encoding="utf-8"))
    snaps = snaps.get("snapshots", snaps) if isinstance(snaps, dict) else snaps
    json.dump(repair_records(recs, snaps, policy), open(argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"metarepair: {len(recs)} records vs {len(snaps)} snapshots -> {argv[2]}")
