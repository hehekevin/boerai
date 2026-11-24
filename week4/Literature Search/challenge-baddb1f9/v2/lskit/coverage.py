"""Coverage & omission analysis against a frozen reference set.

Reference set: [{id, doi, title, authors, year, include_reason, usable}]
Hits log:      [{query_id, source, query_string, record:{...}}]

Outputs, all recomputable:
  - per-reference hit status (which query, which source, which rule)
  - coverage = usable hits / usable references (denominator never inferred
    from the result set itself)
  - miss classification with evidence (agent confirms the class; the engine
    only proposes candidates from observable facts)
  - supplement delta: after new queries, which misses got resolved
"""
from __future__ import annotations

import json
import sys

from . import identity

MISS_CLASSES = ["query_vocab", "field_restriction", "time_window", "source_not_indexed",
                "record_anomaly", "not_retrievable", "pending_review"]


def measure(refs: list[dict], hits_log: list[dict], year_min: int | None = None) -> dict:
    usable = [r for r in refs if r.get("usable", True)]
    excluded = [r for r in refs if not r.get("usable", True)]
    status = []
    for ref in usable:
        hit = None
        for h in hits_log:
            rule, score = identity.match_pair(ref, h.get("record") or h)
            if rule and rule != "doi_conflict":
                hit = {"query_id": h.get("query_id", "?"), "source": h.get("source", "?"),
                       "rule": rule, "score": score,
                       "query_string": h.get("query_string", "")}
                break
        status.append({"ref_id": ref.get("id") or identity.norm_title(ref.get("title", ""))[:48],
                       "title": ref.get("title", ""), "hit": bool(hit), "hit_by": hit})
    n_hit = sum(1 for s in status if s["hit"])
    cov = round(n_hit / len(usable), 4) if usable else None
    misses = [s for s in status if not s["hit"]]
    proposed = []
    for m in misses:
        cand = "pending_review"
        if year_min and m.get("title"):
            pass
        ref = next((r for r in usable if (r.get("id") or identity.norm_title(r.get("title", ""))[:48]) == m["ref_id"]), {})
        if ref.get("year") and year_min and int(ref["year"]) < year_min:
            cand = "time_window"
        if not identity.norm_doi(ref.get("doi", "")) and not identity.norm_title(ref.get("title", "")):
            cand = "record_anomaly"
        proposed.append({"ref_id": m["ref_id"], "title": m["title"], "candidate_class": cand,
                         "note": "candidate only; agent must confirm with query/source evidence"})
    return {"usable_refs": len(usable), "excluded_refs": [
                {"id": r.get("id"), "reason": r.get("exclude_reason", "")} for r in excluded],
            "hits": n_hit, "coverage": cov,
            "per_reference": status, "misses": proposed,
            "denominator_note": "denominator = frozen usable reference count, never the result set"}


def supplement_delta(before: dict, after_refs_hit_ids: list[str]) -> dict:
    resolved = [m["ref_id"] for m in before["misses"] if m["ref_id"] in set(after_refs_hit_ids)]
    remaining = [m for m in before["misses"] if m["ref_id"] not in set(after_refs_hit_ids)]
    return {"resolved": resolved, "remaining": remaining,
            "resolved_n": len(resolved), "remaining_n": len(remaining),
            "delta_note": "omission下降必须按 ref_id 逐条对应，不得只报总数"}


def _demo() -> int:
    refs = [{"id": "R1", "title": "Deep Learning for Proteins", "authors": ["Smith"], "year": 2021,
             "doi": "10.1000/xyz.1"},
            {"id": "R2", "title": "CRISPR Screens in T Cells", "authors": ["Lee"], "year": 2020},
            {"id": "R3", "title": "Old Method", "authors": ["Wang"], "year": 1998},
            {"id": "R4", "title": "Retracted Work", "usable": False, "exclude_reason": "撤稿"}]
    hits = [{"query_id": "Q1", "source": "crossref", "query_string": "deep learning proteins",
             "record": {"title": "Deep learning for proteins.", "authors": ["Smith"], "year": 2021,
                        "doi": "10.1000/xyz.1"}},
            {"query_id": "Q2", "source": "europepmc", "query_string": "crispr t cell",
             "record": {"title": "CRISPR screens in T cells", "authors": ["Lee"], "year": 2020}}]
    rep = measure(refs, hits, year_min=2015)
    assert rep["coverage"] == round(2 / 3, 4), rep["coverage"]
    assert rep["misses"][0]["candidate_class"] == "time_window"
    print(json.dumps({"demo": "coverage.measure", "usable": rep["usable_refs"],
                      "hits": rep["hits"], "coverage": rep["coverage"],
                      "miss_classes": [m["candidate_class"] for m in rep["misses"]]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    refs = json.load(open(sys.argv[1], encoding="utf-8"))
    hits = json.load(open(sys.argv[2], encoding="utf-8"))
    kw = {}
    if len(sys.argv) > 4 and sys.argv[4]:
        kw["year_min"] = int(sys.argv[4])
    rep = measure(refs.get("references", refs), hits.get("hits", hits), **kw)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"coverage={rep['coverage']} ({rep['hits']}/{rep['usable_refs']}) -> {sys.argv[3]}")
