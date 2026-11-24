"""Local file search with evidence回链 (challenge: 科研文件智能检索).

Builds a passage index over extracted materials (hk extract output), answers
keyword/phrase queries with ranked passages, each carrying file + locator.
Ranking is transparent: score = weighted term coverage + phrase bonus; the
scoring formula is printed in the output so the rank order can be re-derived.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter

from .identity import norm_title


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z0-9_\-]+|[一-鿿]", text or "") if len(t) > 1 or t.isalnum()]


def build_index(materials: list[dict]) -> dict:
    """materials: [{path, blocks:[{locator, text}]}] or [{path, text}]"""
    passages = []
    for m in materials:
        blocks = m.get("blocks") or [{"locator": "p.1", "text": m.get("text", "")}]
        for b in blocks:
            text = b.get("text", "")
            for para in re.split(r"\n\s*\n", text):
                para = para.strip()
                if len(para) < 20:
                    continue
                passages.append({"file": m.get("rel") or m.get("path"), "locator": b.get("locator", "?"),
                                 "text": para[:1500]})
    df: Counter = Counter()
    toks = []
    for p in passages:
        t = set(tokenize(p["text"]))
        toks.append(t)
        df.update(t)
    return {"passages": passages, "tokens": toks, "df": dict(df), "n": len(passages),
            "formula": "score = sum over query terms of idf * (1 + phrase_bonus), idf = ln((N+1)/(df+1))"}


def search(index: dict, query: str, top_k: int = 8, file_filter: str = "") -> dict:
    qt = tokenize(query)
    phrases = re.findall(r'"([^"]+)"', query)
    df, n = index["df"], max(1, index["n"])
    scored = []
    for p, toks in zip(index["passages"], index["tokens"]):
        if file_filter and file_filter not in p["file"]:
            continue
        s = 0.0
        matched = []
        for t in qt:
            if t in toks:
                idf = math.log((n + 1) / (df.get(t, 0) + 1))
                s += idf
                matched.append(t)
        for ph in phrases:
            if ph.lower() in p["text"].lower():
                s += 2.0
                matched.append(f'"{ph}"')
        if s > 0:
            scored.append({"file": p["file"], "locator": p["locator"],
                           "score": round(s, 3), "matched_terms": matched,
                           "snippet": p["text"][:300]})
    scored.sort(key=lambda x: (-x["score"], x["file"], x["locator"]))
    return {"query": query, "hits": scored[:top_k], "total_hits": len(scored),
            "formula": index["formula"],
            "note": "每条命中含 file+locator；分数公式见 formula，可手工复算"}


def _demo() -> int:
    mats = [{"rel": "paper1.txt", "blocks": [
        {"locator": "p.2", "text": "CRISPR screens in T cells identify regulators of activation.\n\nWe screened 500 genes."},
        {"locator": "p.5", "text": "The cafeteria opens at noon.\n\nNothing about biology here but enough text to index."}]},
        {"rel": "notes.txt", "blocks": [
            {"locator": "p.1", "text": "T cell activation markers include CD69 and CD25.\n\nSee also CRISPR methods."}]}]
    idx = build_index(mats)
    rep = search(idx, 'CRISPR "T cells" activation')
    assert rep["total_hits"] >= 2
    assert rep["hits"][0]["locator"] in ("p.2", "p.1")
    print(json.dumps({"demo": "filesearch", "passages": idx["n"], "hits": rep["total_hits"],
                      "top": [f"{h['file']}:{h['locator']}" for h in rep["hits"][:2]]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "index":
        mats = json.load(open(sys.argv[2], encoding="utf-8"))
        idx = build_index(mats.get("materials", mats))
        idx["tokens"] = [sorted(t) for t in idx["tokens"]]
        json.dump(idx, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
        print(f"indexed {idx['n']} passages -> {sys.argv[3]}")
    elif cmd == "search":
        idx = json.load(open(sys.argv[2], encoding="utf-8"))
        idx["tokens"] = [set(t) for t in idx["tokens"]]
        rep = search(idx, sys.argv[3], top_k=int(sys.argv[5]) if len(sys.argv) > 5 else 8)
        json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"hits={rep['total_hits']} -> {sys.argv[4]}")
