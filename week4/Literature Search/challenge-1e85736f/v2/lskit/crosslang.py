"""Cross-language retrieval helpers: term alignment table, language id,
cross-language record matching with per-hit language/version provenance.

Term alignment is supplied by the agent (bilingual glossary); the engine
applies it deterministically and keeps the evidence chain inspectable.
"""
from __future__ import annotations

import json
import re
import sys

from .identity import norm_title, jaccard, title_tokens

CJK = re.compile(r"[一-鿿぀-ヿ가-힯]")


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[가-힯]", text):
        return "ko"
    if re.search(r"[àâäéèêëïîôùûüÿçœæ]", text, re.I):
        return "fr/de-latin"
    return "en"


def build_query_matrix(terms: list[dict]) -> dict:
    """terms: [{concept, en, zh, synonyms:[...]}] -> query strings per language pair."""
    queries = []
    for t in terms:
        for lang_key in ("en", "zh"):
            base = t.get(lang_key)
            if not base:
                continue
            variants = {base} | set(t.get("synonyms") or [])
            queries.append({"concept": t["concept"], "lang": lang_key,
                            "query": " OR ".join(f'"{v}"' for v in sorted(variants))})
    return {"queries": queries,
            "note": "术语对齐表由 Agent 填写并随结果交付，供人工核对；引擎只机械展开"}


def match_crosslang(reference: dict, candidates: list[dict],
                    translations: dict | None = None) -> dict:
    """reference: EN record; candidates: any-language records.
    translations: {candidate_id: "english title translation"} supplied by agent."""
    translations = translations or {}
    out = []
    ref_tokens = title_tokens(reference.get("title", ""))
    for c in candidates:
        cid = str(c.get("id"))
        lang = detect_language(c.get("title", ""))
        cand_title_en = translations.get(cid, c.get("title_en") or (c.get("title") if lang == "en" else ""))
        cand_tokens = title_tokens(cand_title_en) if cand_title_en else set()
        jac = jaccard(ref_tokens, cand_tokens) if cand_tokens else 0.0
        containment = (len(ref_tokens & cand_tokens) / max(1, min(len(ref_tokens), len(cand_tokens)))) if cand_tokens else 0.0
        same_year = str(c.get("year") or "") == str(reference.get("year") or "")
        verdict = "match" if (jac >= 0.75 or containment >= 0.85) else ("review" if (jac >= 0.45 or containment >= 0.6) and same_year else "no_match")
        out.append({"candidate_id": cid, "language": lang, "title": c.get("title"),
                    "title_used": cand_title_en, "translation_source": "agent_glossary" if cid in translations else ("record_field" if c.get("title_en") else "none"),
                    "jaccard": round(jac, 3), "containment": round(containment, 3), "same_year": same_year, "verdict": verdict,
                    "version_note": f"{lang} version; translation provenance recorded"})
    return {"reference": reference.get("title"), "results": out,
            "note": "非英语命中必须给出 language、所用译名与译名来源；review 档须人工核对"}


def _demo() -> int:
    assert detect_language("深度学习在蛋白质设计中的应用") == "zh"
    assert detect_language("Deep learning for proteins") == "en"
    terms = [{"concept": "protein design", "en": "protein design", "zh": "蛋白质设计",
              "synonyms": ["protein engineering", "蛋白工程"]}]
    qm = build_query_matrix(terms)
    assert len(qm["queries"]) == 2
    ref = {"title": "Deep learning for protein design", "year": 2021}
    cands = [{"id": "C1", "title": "深度学习在蛋白质设计中的应用", "year": 2021},
             {"id": "C2", "title": "Unrelated topic in English", "year": 2020}]
    rep = match_crosslang(ref, cands, translations={"C1": "Application of deep learning in protein design"})
    assert rep["results"][0]["verdict"] == "match"
    assert rep["results"][0]["language"] == "zh"
    assert rep["results"][1]["verdict"] == "no_match"
    print(json.dumps({"demo": "crosslang", "queries": len(qm["queries"]),
                      "verdicts": [r["verdict"] for r in rep["results"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "matrix":
        rep = build_query_matrix(json.load(open(sys.argv[2], encoding="utf-8")))
    elif cmd == "match":
        ref = json.load(open(sys.argv[2], encoding="utf-8"))
        cands = json.load(open(sys.argv[3], encoding="utf-8"))
        trans = json.load(open(sys.argv[5], encoding="utf-8")) if len(sys.argv) > 5 else {}
        rep = match_crosslang(ref, cands.get("records", cands), trans)
    elif cmd == "lang":
        print(detect_language(sys.argv[2])); sys.exit(0)
    else:
        print("usage: crosslang.py [matrix|match|lang] ..."); sys.exit(2)
    json.dump(rep, open(sys.argv[4] if cmd == "matrix" else sys.argv[4], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{cmd} done")
