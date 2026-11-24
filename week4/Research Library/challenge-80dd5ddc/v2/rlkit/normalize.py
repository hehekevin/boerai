"""Record normalisation and heterogeneous-source field mapping.

Different sources name the same field differently (Author/authors/AU,
Year/PY/date ...), write dates and author names differently, and mix units.
normalize_record maps a raw source record into the canonical schema
  {item_key, item_type, title, authors[], year, venue, doi, tags[], extra{}}
and keeps per-field provenance (which source field filled which canonical
field).  Unmappable fields go to `extra` and are listed in the report —
never silently dropped.
"""
from __future__ import annotations

import json
import re
import sys

from .identity import norm_doi, norm_title

CANONICAL_FIELDS = ["item_key", "item_type", "title", "authors", "year", "venue",
                    "doi", "url", "abstract", "tags", "collections", "date", "language"]

DEFAULT_FIELD_MAP = {
    "item_key": ["item_key", "key", "id", "ID", "ref_id"],
    "item_type": ["item_type", "itemType", "type", "TY", "entrytype"],
    "title": ["title", "Title", "TI", "T1", "name"],
    "authors": ["authors", "Author", "author", "AU", "A1", "creators"],
    "year": ["year", "Year", "PY", "Y1"],
    "venue": ["venue", "journal", "Journal", "JO", "T2", "publication", "booktitle"],
    "doi": ["doi", "DOI"],
    "url": ["url", "URL", "UR"],
    "abstract": ["abstract", "Abstract", "AB", "N2"],
    "tags": ["tags", "KW", "keywords"],
    "date": ["date", "Date", "DA", "issued"],
}


def _as_list(v):
    if v in (None, ""):
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r";|\|", str(v)) if x.strip()]


def norm_authors(v) -> list:
    """Accept 'Smith, John; Doe, Jane', 'John Smith and Jane Doe', or a list
    of str / {name} / {firstName,lastName}; output 'Family, Given' strings."""
    out = []
    if isinstance(v, list):
        for a in v:
            if isinstance(a, dict):
                if a.get("name"):
                    out.append(str(a["name"]).strip())
                else:
                    fam, giv = str(a.get("lastName", "")).strip(), str(a.get("firstName", "")).strip()
                    out.append(f"{fam}, {giv}".strip(", ") if fam else giv)
            else:
                out.extend(norm_authors(str(a)))
        return [x for x in out if x]
    for part in re.split(r";|\||\band\b", str(v)):
        p = part.strip()
        if not p:
            continue
        if "," not in p:
            toks = p.split()
            if len(toks) >= 2 and re.fullmatch(r"[A-Za-z.\-]+", toks[-1]):
                p = f"{toks[-1]}, {' '.join(toks[:-1])}"
        out.append(p)
    return out


def norm_year(v) -> str:
    m = re.search(r"(19|20)\d{2}", str(v or ""))
    return m.group(0) if m else ""


def normalize_record(raw: dict, source: str = "unknown", field_map: dict = None) -> dict:
    fmap = dict(DEFAULT_FIELD_MAP)
    if field_map:
        for k, v in field_map.items():
            fmap[k] = list(v) if isinstance(v, list) else [v]
    rec, prov, used = {}, {}, set()
    for canon, aliases in fmap.items():
        for al in aliases:
            if al in raw and raw[al] not in (None, "", []):
                rec[canon] = raw[al]
                prov[canon] = al
                used.add(al)
                break
    rec["authors"] = norm_authors(rec.get("authors"))
    rec["year"] = norm_year(rec.get("year") or rec.get("date"))
    if rec.get("doi"):
        rec["doi"] = norm_doi(str(rec["doi"]))
    if rec.get("tags"):
        rec["tags"] = _as_list(rec["tags"])
    rec["item_type"] = str(rec.get("item_type") or "document").lower()
    rec["title"] = re.sub(r"\s+", " ", str(rec.get("title") or "")).strip()
    extra = {k: v for k, v in raw.items() if k not in used}
    rec["extra"] = extra
    rec["source_db"] = source
    rec["_provenance"] = prov
    return rec


def normalize_batch(raw_records: list, source: str = "unknown", field_map: dict = None) -> dict:
    recs, unmappable = [], {}
    for i, raw in enumerate(raw_records):
        rec = normalize_record(raw, source, field_map)
        recs.append(rec)
        for k in rec["extra"]:
            unmappable.setdefault(k, 0)
            unmappable[k] += 1
        if not rec.get("title") and not rec.get("doi"):
            recs[-1]["_warning"] = "no_title_no_doi: record may be unidentifiable"
    return {"records": recs,
            "report": {"input": len(raw_records), "output": len(recs), "source": source,
                       "unmappable_source_fields": unmappable,
                       "records_without_title_or_doi": sum(1 for r in recs if r.get("_warning")),
                       "schema": CANONICAL_FIELDS}}


def _demo() -> int:
    raws = [
        {"TY": "JOUR", "TI": "  Deep   Learning for Proteins ", "AU": ["Smith, John", "Doe, Jane"],
         "PY": "2021/03", "DOI": "https://doi.org/10.1000/XYZ.1", "JO": "Nature",
         "KW": "protein; deep learning", "weird_field": "keep-me"},
        {"title": "Another Study", "creators": [{"firstName": "Li", "lastName": "Wei"}],
         "issued": "2019", "type": "article-journal"},
    ]
    out = normalize_batch(raws, source="ris_snapshot")
    r0, r1 = out["records"]
    assert r0["doi"] == "10.1000/xyz.1" and r0["year"] == "2021"
    assert r0["authors"] == ["Smith, John", "Doe, Jane"]
    assert r0["extra"]["weird_field"] == "keep-me"
    assert r0["_provenance"]["title"] == "TI"
    assert r1["authors"] == ["Wei, Li"] and r1["year"] == "2019"
    assert out["report"]["unmappable_source_fields"]["weird_field"] == 1
    print(json.dumps({"demo": "normalize.batch", "records": out["report"]["output"],
                      "unmappable": out["report"]["unmappable_source_fields"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    fmap = None
    if "--map" in sys.argv:
        fmap = json.load(open(sys.argv[sys.argv.index("--map") + 1], encoding="utf-8"))
    data = json.load(open(argv[0], encoding="utf-8"))
    raws = data.get("records", data) if isinstance(data, dict) else data
    src = data.get("source", "unknown") if isinstance(data, dict) else "unknown"
    json.dump(normalize_batch(raws, src, fmap), open(argv[1], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"normalize: {len(raws)} records -> {argv[1]}")
