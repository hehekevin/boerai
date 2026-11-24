#!/usr/bin/env python3
"""search-audit-forge: deterministic literature search audit engine.

Deterministic subcommands (0 model requests):
  --plan KEYWORDS...    generate query plan: expansion matrix + boolean templates
  --coverage REF RESULT compute coverage between reference set and search results
  --classify REF RESULT classify misses by actionable cause with evidence
  --dedup RESULT        deduplicate records by identifier/title-fuzzy match
Stdlib only. Exit 0 ok / 1 FAIL (coverage/classify report errors).
"""
import argparse
import json
import re
import sys
import unicodedata

# ---------- helpers ----------

SYNONYM_SEEDS = {
    "machine learning": ["ML", "deep learning", "neural network"],
    "deep learning": ["DL", "neural network", "representation learning"],
    "cancer": ["tumor", "tumour", "neoplasm", "oncology", "carcinoma"],
    "covid": ["SARS-CoV-2", "coronavirus", "COVID-19"],
    "climate": ["climatic", "weather", "meteorological"],
    "protein": ["proteins", "proteomic"],
    "graph": ["network", "graph-structured"],
    "transformer": ["attention", "self-attention"],
    "knowledge graph": ["KG", "knowledge base", "ontology"],
    "reinforcement learning": ["RL", "policy learning", "Q-learning"],
}


def norm_text(s):
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def title_key(s):
    s = norm_text(s)
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s)


def parse_records(path_or_list, is_file=True):
    """Parse records from JSONL/JSON/TSV text: fields doi,title,authors,year,source."""
    recs = []
    if is_file:
        text = open(path_or_list, encoding="utf-8", errors="replace").read()
    else:
        text = path_or_list
    stripped = text.strip()
    if stripped.startswith("[") or "\n{" in stripped[:200]:
        try:
            obj = json.loads(stripped)
            recs = obj if isinstance(obj, list) else obj.get("items", obj.get("results", []))
        except json.JSONDecodeError:
            recs = []
    if not recs:
        # TSV / lines fallback: doi<TAB>title or "title" per line
        for line in stripped.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2 and "@" in parts[0] or parts[0].lower().startswith("10."):
                recs.append({"doi": parts[0], "title": parts[1], "authors": parts[2] if len(parts) > 2 else "", "year": parts[3] if len(parts) > 3 else ""})
            elif len(parts) >= 2:
                recs.append({"doi": "", "title": parts[0], "authors": parts[1], "year": parts[2] if len(parts) > 2 else ""})
            elif line:
                recs.append({"doi": "", "title": line, "authors": "", "year": ""})
    out = []
    for i, r in enumerate(recs):
        if not isinstance(r, dict):
            r = {"title": str(r)}
        out.append({
            "idx": i,
            "doi": norm_text(r.get("doi") or r.get("DOI") or ""),
            "title": r.get("title") or r.get("Title") or "",
            "authors": r.get("authors") or r.get("authors_str") or r.get("author") or "",
            "year": str(r.get("year") or r.get("pub_year") or ""),
            "source": r.get("source") or r.get("db") or "",
        })
    return out


# ---------- subcommands ----------

def cmd_plan(keywords):
    """Expansion matrix + boolean query templates."""
    plan = {"schema": "search-audit/plan@1", "seeds": keywords, "expansions": {}, "templates": []}
    for kw in keywords:
        k = kw.lower().strip()
        exps = set()
        for seed, syns in SYNONYM_SEEDS.items():
            if seed in k or k in seed:
                exps.update(syns)
        # morphological variants
        if k.endswith("s"):
            exps.add(k[:-1])
        else:
            exps.add(k + "s")
        plan["expansions"][kw] = sorted(exps)
    # boolean templates
    t = []
    for kw in keywords:
        exps = plan["expansions"].get(kw, [kw])
        group = " OR ".join('"%s"' % e for e in ([kw] + exps))
        t.append({"field": "topic", "query": "(%s)" % group})
    if t:
        boolean = " AND ".join(x["query"] for x in t[:3])
        plan["templates"].append({"name": "core-conjunction", "query": boolean})
        plan["templates"].append({"name": "broad-or", "query": " OR ".join(x["query"] for x in t[:2])})
        plan["templates"].append({"name": "recent-window", "query": "%s AND (%s)" % (t[0]["query"], "year:>=2019")})
    print(json.dumps(plan, ensure_ascii=False, indent=1))
    return 0


def match_key(rec):
    return (rec["doi"], title_key(rec["title"]))


def records_match(a, b):
    if a["doi"] and b["doi"]:
        return a["doi"] == b["doi"]
    ta, tb = title_key(a["title"]), title_key(b["title"])
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    # title+author+year approximate match
    if len(ta) > 20 and len(tb) > 20 and (ta[:40] == tb[:40] or ta[-40:] == tb[-40:]):
        ya, yb = a["year"], b["year"]
        if not ya or not yb or ya == yb:
            return True
    return False


def cmd_coverage(ref_path, result_path):
    refs = parse_records(ref_path)
    results = parse_records(result_path)
    problems = []
    if not refs:
        problems.append("reference set is empty or unparsable")
    if not results:
        problems.append("search result set is empty or unparsable")
    if problems:
        for p in problems:
            print("FAIL: %s" % p)
        return 1
    matched_ref, matched_res = set(), set()
    for i, r in enumerate(refs):
        for j, s in enumerate(results):
            if records_match(r, s):
                matched_ref.add(i)
                matched_res.add(j)
                break
    covered = len(matched_ref)
    cov_pct = round(100.0 * covered / len(refs), 2)
    miss_idx = [i for i in range(len(refs)) if i not in matched_ref]
    report = {
        "schema": "search-audit/coverage@1",
        "n_reference": len(refs), "n_results": len(results),
        "covered": covered, "coverage_pct": cov_pct,
        "miss_rate_pct": round(100.0 - cov_pct, 2),
        "missed_refs": [{"idx": i, "title": refs[i]["title"][:80], "doi": refs[i]["doi"]} for i in miss_idx[:50]],
        "n_missed": len(miss_idx),
        "result_file_dedup_needed": len(results) - len({title_key(r["title"]) for r in results if r["title"]}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


def cmd_classify(ref_path, result_path):
    refs = parse_records(ref_path)
    results = parse_records(result_path)
    if not refs:
        print("FAIL: reference set empty")
        return 1
    matched = set()
    for i, r in enumerate(refs):
        for s in results:
            if records_match(r, s):
                matched.add(i)
                break
    results_kw = " ".join(title_key(r["title"]) for r in results)
    classes = {"synonym_gap": [], "narrow_scope": [], "unavailable_record": [], "identifier_anomaly": [], "unknown": []}
    for i, r in enumerate(refs):
        if i in matched:
            continue
        t = title_key(r["title"])
        toks = [w for w in t.split() if len(w) > 3]
        if any(w in results_kw for w in toks[:4]):
            classes["synonym_gap"].append(r["title"][:80])
        elif not r["doi"] and len(t) < 15:
            classes["identifier_anomaly"].append(r["title"][:80])
        elif any(x in t for x in ("retracted", "withdrawn", "erratum")):
            classes["unavailable_record"].append(r["title"][:80])
        elif len(toks) > 12:
            classes["narrow_scope"].append(r["title"][:80])
        else:
            classes["unknown"].append(r["title"][:80])
    out = {"schema": "search-audit/miss-classify@1", "n_missed": len(refs) - len(matched), "classes": {k: {"count": len(v), "samples": v[:10]} for k, v in classes.items()}}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def dedup_key(rec):
    # DOI is authoritative when present; fall back to normalized title
    return ("doi:" + rec["doi"]) if rec["doi"] else ("title:" + title_key(rec["title"]))


def cmd_dedup(result_path):
    recs = parse_records(result_path)
    seen, kept, dupes = {}, [], []
    for r in recs:
        k = dedup_key(r)
        if k in seen:
            dupes.append({"idx": r["idx"], "title": r["title"][:80], "dup_of_idx": seen[k], "key": k})
        else:
            seen[k] = r["idx"]
            kept.append(r)
    print(json.dumps({"schema": "search-audit/dedup@1", "n_input": len(recs), "n_unique": len(kept), "n_duplicates": len(dupes), "duplicates": dupes[:30]}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", nargs="+", metavar="KEYWORD")
    ap.add_argument("--coverage", nargs=2, metavar=("REF", "RESULT"))
    ap.add_argument("--classify", nargs=2, metavar=("REF", "RESULT"))
    ap.add_argument("--dedup")
    a = ap.parse_args()
    if a.plan:
        return cmd_plan(a.plan)
    if a.coverage:
        return cmd_coverage(a.coverage[0], a.coverage[1])
    if a.classify:
        return cmd_classify(a.classify[0], a.classify[1])
    if a.dedup:
        return cmd_dedup(a.dedup)
    ap.error("choose --plan / --coverage / --classify / --dedup")


if __name__ == "__main__":
    sys.exit(main())
