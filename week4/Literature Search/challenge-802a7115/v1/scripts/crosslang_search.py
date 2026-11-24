#!/usr/bin/env python3
"""crosslang-search-forge: bilingual term matrix, language detection, cross-lang match rules.

Deterministic subcommands (0 model requests):
  --termmatrix TERM_PAIRS_TSV   build bilingual expansion matrix (zh-en + variants)
                                tsv: zh_term<TAB>en_term<TAB>type(synonym|abbr|translit|localname)
  --detect RECORDS_JSON         language & version detection for records (title/abstract heuristics)
  --match RECORDS_JSON QUERY_TERMS_JSON  cross-language matching with evidence
  --backtranslate HITS_JSON     high-risk hit review queue (backtranslation flag)
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata

CJK = re.compile(r"[\u4e00-\u9fff]")


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()


def detect_lang(text):
    t = norm(text)
    if not t:
        return "unknown", "empty"
    cjk_ratio = len(CJK.findall(t)) / max(1, len(t))
    if cjk_ratio > 0.15:
        return "zh", f"CJK占比 {cjk_ratio:.0%}"
    if re.match(r"^[a-z0-9\s]+$", t):
        return "en", "纯拉丁字符"
    return "mixed", "多语言混合"


def cmd_termmatrix(path):
    pairs = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        while len(parts) < 3:
            parts.append("synonym")
        zh, en, typ = parts[0], parts[1], parts[2]
        entry = {"zh": zh, "en": en, "type": typ}
        # variants: morphological + case
        variants = {en, en.lower(), en.upper()}
        if en.endswith("s"):
            variants.add(en[:-1])
        else:
            variants.add(en + "s")
        if typ == "abbr":
            variants.add(en.replace(".", ""))
        entry["en_variants"] = sorted(variants)
        pairs.append(entry)
    print(json.dumps({"schema": "crosslang/term-matrix@1", "n_pairs": len(pairs), "pairs": pairs},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_detect(records_path):
    recs = json.load(open(records_path, encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("records", recs.get("items", []))
    out = []
    for r in recs:
        lang_t, ev_t = detect_lang(r.get("title", ""))
        lang_a, ev_a = detect_lang(r.get("abstract", ""))
        version = "original"
        if lang_t != lang_a and "unknown" not in (lang_t, lang_a):
            version = "bilingual_journal"
        elif lang_t == "zh" and (r.get("doi") or "").startswith("10."):
            version = "original_zh"
        out.append({"id": r.get("id", r.get("idx", "")), "title": (r.get("title") or "")[:50],
                    "lang_title": lang_t, "lang_abstract": lang_a, "version": version,
                    "evidence": f"title:{ev_t}; abstract:{ev_a}",
                    "risk": "语种标错会导致查询词错配" if version == "bilingual_journal" else ""})
    print(json.dumps({"schema": "crosslang/detect@1", "records": out,
                      "summary": {k: sum(1 for o in out if o['lang_title'] == k) for k in ('zh', 'en', 'mixed', 'unknown')}},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_match(records_path, terms_path):
    recs = json.load(open(records_path, encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("records", recs.get("items", []))
    terms = json.load(open(terms_path, encoding="utf-8"))
    pairs = terms.get("pairs", terms if isinstance(terms, list) else [])
    matches = []
    for r in recs:
        t = norm(r.get("title", "")) + " " + norm(r.get("abstract", ""))
        hit_terms = []
        for p in pairs:
            for v in p.get("en_variants", [p.get("en", "")]):
                if v.lower() in t:
                    hit_terms.append({"zh": p["zh"], "en_hit": v, "type": p.get("type")})
                    break
            if norm(p.get("zh", "")) and p["zh"] in (r.get("title", "") + (r.get("abstract") or "")):
                hit_terms.append({"zh_hit": p["zh"], "type": p.get("type")})
        if hit_terms:
            matches.append({"id": r.get("id", r.get("idx", "")), "title": (r.get("title") or "")[:50],
                            "matched_terms": hit_terms[:8],
                            "evidence": f"命中 {len(hit_terms)} 个双语术语"})
    print(json.dumps({"schema": "crosslang/match@1", "n_records": len(recs), "n_matched": len(matches),
                      "matches": matches[:30]}, ensure_ascii=False, indent=1))
    return 0


def cmd_backtranslate(hits_path):
    hits = json.load(open(hits_path, encoding="utf-8"))
    if isinstance(hits, dict):
        hits = hits.get("matches", [])
    queue = []
    for h in hits:
        terms = h.get("matched_terms", [])
        # high-risk: only translit/localname types, or single-term hits
        risky = any(t.get("type") in ("translit", "localname") for t in terms) or len(terms) == 1
        queue.append({"id": h.get("id"), "backtranslate_required": risky,
                      "reason": "音译/本地名命中，词面对应语义可能不同——需回译或人工抽检" if risky else "多术语语义命中，风险低",
                      "false_positive_flag": risky})
    print(json.dumps({"schema": "crosslang/backtranslate@1", "queue": queue,
                      "summary": {"high_risk": sum(1 for q in queue if q['backtranslate_required']),
                                   "total": len(queue)}}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--termmatrix")
    ap.add_argument("--detect")
    ap.add_argument("--match", nargs=2)
    ap.add_argument("--backtranslate")
    a = ap.parse_args()
    if a.termmatrix:
        return cmd_termmatrix(a.termmatrix)
    if a.detect:
        return cmd_detect(a.detect)
    if a.match:
        return cmd_match(a.match[0], a.match[1])
    if a.backtranslate:
        return cmd_backtranslate(a.backtranslate)
    ap.error("choose --termmatrix / --detect / --match / --backtranslate")


if __name__ == "__main__":
    sys.exit(main())
