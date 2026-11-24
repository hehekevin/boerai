"""Incremental tracking: diff a new snapshot against the frozen previous one.

Each changed item gets a replay-able判定依据: matched by identity rule, or
absent from the frozen snapshot (= new), or present before but gone (= removed).
Never compares by list position or recollection.
"""
from __future__ import annotations

import json
import sys

from . import identity


def diff_snapshots(prev: list[dict], curr: list[dict]) -> dict:
    new_items, removed, matched = [], [], []
    used = set()
    for c in curr:
        hit = None
        for i, p in enumerate(prev):
            if i in used:
                continue
            rule, score = identity.match_pair(c, p)
            if rule and rule != "doi_conflict":
                hit = (i, rule, score)
                break
        if hit:
            used.add(hit[0])
            matched.append({"id": c.get("id") or identity.norm_title(c.get("title", ""))[:48],
                            "rule": hit[1], "score": hit[2],
                            "basis": "identity match against frozen previous snapshot"})
        else:
            new_items.append({"record": c,
                              "basis": "no identity match in frozen previous snapshot (checked doi/title/author-year)"})
    for i, p in enumerate(prev):
        if i not in used:
            removed.append({"record": p, "basis": "present in previous snapshot, absent in current"})
    return {"previous_n": len(prev), "current_n": len(curr),
            "new": new_items, "removed": removed, "matched": matched,
            "new_n": len(new_items), "removed_n": len(removed),
            "note": "增量判定可回放：每条 new/removed 都给出与冻结快照的比对依据"}


def _demo() -> int:
    prev = [{"id": "P1", "title": "Alpha Paper", "authors": ["Smith"], "year": 2020, "doi": "10.1/a"},
            {"id": "P2", "title": "Beta Paper", "authors": ["Lee"], "year": 2021}]
    curr = [{"id": "P1", "title": "Alpha paper.", "authors": ["Smith"], "year": 2020, "doi": "10.1/a"},
            {"id": "P3", "title": "Gamma Paper", "authors": ["Wang"], "year": 2024}]
    rep = diff_snapshots(prev, curr)
    assert rep["new_n"] == 1 and rep["removed_n"] == 1 and len(rep["matched"]) == 1
    assert rep["new"][0]["record"]["id"] == "P3"
    print(json.dumps({"demo": "increment.diff", "new": rep["new_n"], "removed": rep["removed_n"],
                      "matched": len(rep["matched"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    prev = json.load(open(sys.argv[1], encoding="utf-8"))
    curr = json.load(open(sys.argv[2], encoding="utf-8"))
    rep = diff_snapshots(prev.get("records", prev), curr.get("records", curr))
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"new={rep['new_n']} removed={rep['removed_n']} matched={len(rep['matched'])} -> {sys.argv[3]}")
