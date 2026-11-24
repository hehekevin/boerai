"""Record identity, matching and merge for bibliographic / library records.

Adapted from lskit.identity for the research-library track.  A record is a
dict with any of: id/key/item_key, doi, title, authors (list or str), year,
venue, aliases (list of alternative titles/keys), source_db, raw.
Identity rules, in order of strength:
  1. equal normalised DOI
  2. equal normalised title (or title matches an alias)
  3. same first-author surname + year + title token Jaccard >= 0.90
Every merge decision is logged with the rule that fired and any field
conflicts, so a third party can re-run the dedupe and get the same answer.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")
STOP = {"the", "a", "an", "of", "and", "in", "on", "for", "to", "with", "by", "is", "are",
        "de", "la", "el", "der", "die", "das", "le", "les", "et", "und"}


def norm_doi(doi: str) -> str:
    d = (doi or "").strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d.strip()


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = _PUNCT.sub(" ", t.casefold())
    return _WS.sub(" ", t).strip()


def title_tokens(title: str) -> set:
    return {t for t in norm_title(title).split() if t not in STOP and len(t) > 1}


def first_surname(authors) -> str:
    if isinstance(authors, str):
        authors = [a.strip() for a in re.split(r";| and ", authors) if a.strip()]
    if not authors:
        return ""
    a = str(authors[0]).strip()
    if "," in a:
        return norm_title(a.split(",", 1)[0]).replace(" ", "")
    parts = a.split()
    return norm_title(parts[-1] if parts else "").replace(" ", "")


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def signature(rec: dict) -> str:
    return f"{first_surname(rec.get('authors'))}|{rec.get('year') or ''}"


def _titles_of(rec: dict) -> list:
    ts = [rec.get("title", "")]
    ts += list(rec.get("aliases") or [])
    return [norm_title(t) for t in ts if norm_title(t)]


def match_pair(a: dict, b: dict) -> tuple:
    """Return (rule, score) or ("", 0.0) when not a match."""
    da, db = norm_doi(a.get("doi", "")), norm_doi(b.get("doi", ""))
    if da and db:
        return ("doi_exact", 1.0) if da == db else ("doi_conflict", 0.0)
    ta, tb = _titles_of(a), _titles_of(b)
    if ta and tb and set(ta) & set(tb):
        return "title_exact", 1.0
    sa, sb = signature(a), signature(b)
    if sa == sb and sa != "|":
        jac = max([jaccard(title_tokens(x), title_tokens(y)) for x in ta for y in tb] or [0.0])
        if jac >= 0.90:
            return "author_year_title_fuzzy", round(jac, 3)
    jac = max([jaccard(title_tokens(x), title_tokens(y)) for x in ta for y in tb] or [0.0])
    if jac >= 0.97:
        return "title_fuzzy", round(jac, 3)
    return "", 0.0


MERGE_FIELDS = ["title", "authors", "year", "venue", "abstract", "doi", "item_type"]


def merge_two(base: dict, other: dict, rule: str, log: list) -> dict:
    out = dict(base)
    sources = set(out.get("_sources") or [out.get("source_db") or "unknown"])
    sources.add(other.get("source_db") or "unknown")
    out["_sources"] = sorted(sources)
    keys = set(out.get("_keys") or ([out.get("item_key")] if out.get("item_key") else []))
    if other.get("item_key"):
        keys.add(other["item_key"])
    out["_keys"] = sorted(k for k in keys if k)
    for f in MERGE_FIELDS:
        bv, ov = out.get(f), other.get(f)
        if (bv in (None, "", [])) and ov not in (None, "", []):
            out[f] = ov
        elif bv not in (None, "", []) and ov not in (None, "", []) and f != "abstract":
            sb, so = (json.dumps(bv, ensure_ascii=False), json.dumps(ov, ensure_ascii=False))
            if sb != so:
                log.append({"type": "field_conflict", "field": f, "kept": bv, "other": ov,
                            "rule": rule, "record": norm_title(out.get("title", ""))[:60]})
    return out


def dedupe(records: list) -> dict:
    """Greedy dedupe with full audit: merged records + rule/score per merge."""
    kept: list = []
    merges: list = []
    conflicts: list = []
    suspects: list = []
    for rec in records:
        placed = False
        for i, k in enumerate(kept):
            rule, score = match_pair(k, rec)
            if rule == "doi_conflict":
                suspects.append({"type": "same_title_or_author_different_doi",
                                 "a": norm_title(k.get("title", ""))[:60],
                                 "b": norm_title(rec.get("title", ""))[:60],
                                 "doi_a": norm_doi(k.get("doi", "")), "doi_b": norm_doi(rec.get("doi", ""))})
                continue
            if rule:
                kept[i] = merge_two(k, rec, rule, conflicts)
                merges.append({"rule": rule, "score": score,
                               "merged": norm_title(rec.get("title", ""))[:60],
                               "into": norm_title(k.get("title", ""))[:60],
                               "sources": kept[i].get("_sources")})
                placed = True
                break
        if not placed:
            r = dict(rec)
            r["_sources"] = [rec.get("source_db") or "unknown"]
            r["_keys"] = [rec["item_key"]] if rec.get("item_key") else []
            kept.append(r)
    return {"records": kept,
            "audit": {"input": len(records), "output": len(kept),
                      "merges": merges, "field_conflicts": conflicts,
                      "suspects_not_merged": suspects}}


def _demo() -> int:
    recs = [
        {"item_key": "A1", "title": "Deep Learning for Proteins", "authors": ["Smith, John"],
         "year": 2021, "doi": "10.1000/xyz.1", "source_db": "crossref"},
        {"item_key": "B2", "title": "Deep learning for proteins.", "authors": "J Smith",
         "year": 2021, "doi": "https://doi.org/10.1000/xyz.1", "source_db": "ris_import",
         "venue": "Nat"},
        {"item_key": "C3", "title": "Deep Learning for Protein Design",
         "authors": ["Smith, John"], "year": 2021, "source_db": "local"},
        {"item_key": "D4", "title": " unrelated paper ", "authors": ["Doe, Jane"],
         "year": 2019, "source_db": "local"},
        {"item_key": "E5", "title": "Deep Learning for Proteins", "authors": ["Smith, J"],
         "year": 2021, "doi": "10.9999/different.1", "source_db": "publisher"},
    ]
    out = dedupe(recs)
    assert out["audit"]["output"] == 4, out["audit"]["output"]  # A1+B2 merged; E5 suspect kept
    assert out["audit"]["merges"][0]["rule"] == "doi_exact"
    assert len(out["audit"]["merges"]) == 1
    assert len(out["audit"]["suspects_not_merged"]) == 1  # doi conflict kept separate
    print(json.dumps({"demo": "identity.dedupe", "input": 5, "output": out["audit"]["output"],
                      "merges": len(out["audit"]["merges"]),
                      "conflicts": len(out["audit"]["field_conflicts"]),
                      "suspects": len(out["audit"]["suspects_not_merged"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    recs = data.get("records", data) if isinstance(data, dict) else data
    json.dump(dedupe(recs), open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"dedupe: {len(recs)} -> written {sys.argv[2]}")
