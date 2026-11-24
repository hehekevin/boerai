"""Knowledge-base retrieval and evidence anchoring (科研知识库问答 support).

The engine owns the deterministic part of grounded Q&A:
  * index extracted materials into blocks with exact locators
    (file rel path + hk locator like p.3 / para.12 / block.7 + sha256);
  * search blocks by token overlap, returning ranked hits with locators;
  * citation formatting: every claim must cite {source_id, file, locator,
    quote}; citations are validated — the quoted text must actually appear
    in the located block, otherwise the citation is rejected;
  * insufficient-evidence grading: no_evidence / weak_evidence /
    conflicting_evidence, with what-is-missing notes — the honest "库里没有"
    instead of a fluent answer with wrong anchors.
Semantic reading and answer writing stay with the Agent; coordinates,
validation and coverage counts are deterministic and re-runnable.
"""
from __future__ import annotations

import json
import math
import re
import sys

from .identity import norm_title

_TOKEN = re.compile(r"[A-Za-z0-9_]+|[一-鿿]")


def tokens(text: str) -> list:
    return _TOKEN.findall((text or "").casefold())


def build_index(materials: list) -> dict:
    """materials: hk.extract materials list (path, rel, sha256, blocks[{loc,text}])."""
    blocks = []
    for i, m in enumerate(materials, start=1):
        sid = f"S{i}"
        for j, b in enumerate(m.get("blocks") or []):
            text = (b.get("text") or "").strip()
            if not text:
                continue
            blocks.append({"block_id": f"{sid}#{b.get('loc', j)}",
                           "source_id": sid, "file": m.get("rel") or m.get("path", ""),
                           "locator": b.get("loc", str(j)), "sha256": m.get("sha256", ""),
                           "text": text})
    df = {}
    toks = [set(tokens(b["text"])) for b in blocks]
    for ts in toks:
        for t in ts:
            df[t] = df.get(t, 0) + 1
    return {"blocks": blocks, "df": df, "n_blocks": len(blocks),
            "n_files": len({b["file"] for b in blocks})}


def search(index: dict, query: str, top_k: int = 8) -> list:
    blocks, df, n = index["blocks"], index["df"], max(1, index["n_blocks"])
    q = tokens(query)
    if not q or not blocks:
        return []
    scored = []
    for b in blocks:
        ts = tokens(b["text"])
        if not ts:
            continue
        tset = set(ts)
        s = 0.0
        for t in q:
            if t in tset:
                idf = math.log(1 + n / (1 + df.get(t, 0)))
                s += idf * ts.count(t) / (1 + len(ts) / 120)
        if s > 0:
            scored.append({"score": round(s, 4), "block_id": b["block_id"],
                           "source_id": b["source_id"], "file": b["file"],
                           "locator": b["locator"], "sha256": b["sha256"],
                           "text": b["text"][:600]})
    scored.sort(key=lambda x: (-x["score"], x["block_id"]))
    return scored[:top_k]


def make_citation(index: dict, block_id: str, quote: str) -> dict:
    """A citation is only valid if the quote literally occurs in the block."""
    for b in index["blocks"]:
        if b["block_id"] == block_id:
            q = re.sub(r"\s+", " ", quote).strip()
            hay = re.sub(r"\s+", " ", b["text"])
            ok = bool(q) and q in hay
            return {"block_id": block_id, "source_id": b["source_id"], "file": b["file"],
                    "locator": b["locator"], "sha256": b["sha256"], "quote": quote,
                    "verified": ok,
                    "reason": "" if ok else "quote_not_found_in_located_block"}
    return {"block_id": block_id, "verified": False, "reason": "unknown_block_id"}


def validate_answer(claims: list, index: dict) -> dict:
    """claims: [{claim, citations:[{block_id, quote}]}].  Returns per-claim
    verdicts: supported / citation_invalid / no_citation."""
    verdicts = []
    for c in claims:
        cits = c.get("citations") or []
        if not cits:
            verdicts.append({"claim": c.get("claim", "")[:80], "verdict": "no_citation",
                             "grade": "no_evidence",
                             "missing": "需要至少一条指向具体文件+定位的引用"})
            continue
        results = [make_citation(index, x.get("block_id", ""), x.get("quote", ""))
                   for x in cits]
        ok = [r for r in results if r["verified"]]
        if ok:
            verdicts.append({"claim": c.get("claim", "")[:80], "verdict": "supported",
                             "citations": ok})
        else:
            verdicts.append({"claim": c.get("claim", "")[:80], "verdict": "citation_invalid",
                             "grade": "weak_evidence", "failures": results,
                             "missing": "引用文本与定位块不符，需重新核对原文"})
    n_sup = sum(1 for v in verdicts if v["verdict"] == "supported")
    return {"claims": len(claims), "supported": n_sup,
            "unsupported": len(claims) - n_sup, "verdicts": verdicts,
            "coverage": round(n_sup / len(claims), 3) if claims else 0.0}


def _demo() -> int:
    materials = [
        {"rel": "papers/smith2021.txt", "sha256": "h1",
         "blocks": [{"loc": "block.1", "text": "Deep learning models predict protein "
                                                "function with high accuracy."},
                    {"loc": "block.2", "text": "We screened 500 genes across donors."}]},
        {"rel": "notes/todo.txt", "sha256": "h2",
         "blocks": [{"loc": "block.1", "text": "Buy more pipette tips."}]},
    ]
    idx = build_index(materials)
    assert idx["n_blocks"] == 3 and idx["n_files"] == 2
    hits = search(idx, "protein function prediction accuracy")
    assert hits and hits[0]["file"] == "papers/smith2021.txt"
    good = make_citation(idx, hits[0]["block_id"], "predict protein function")
    assert good["verified"]
    bad = make_citation(idx, hits[0]["block_id"], "quantum gravity results")
    assert not bad["verified"] and bad["reason"] == "quote_not_found_in_located_block"
    res = validate_answer([
        {"claim": "DL predicts protein function accurately",
         "citations": [{"block_id": hits[0]["block_id"], "quote": "predict protein function"}]},
        {"claim": "The lab budget increased", "citations": []},
    ], idx)
    assert res["supported"] == 1 and res["unsupported"] == 1
    assert res["verdicts"][1]["grade"] == "no_evidence"
    print(json.dumps({"demo": "kb.index+search+citation+validate",
                      "blocks": idx["n_blocks"], "hits": len(hits),
                      "supported": res["supported"], "coverage": res["coverage"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "index":  # materials_full.json -> index.json
        mats = json.load(open(sys.argv[2], encoding="utf-8"))
        mats = mats.get("materials", mats) if isinstance(mats, dict) else mats
        json.dump(build_index(mats), open(sys.argv[3], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"kb index -> {sys.argv[3]}")
    elif cmd == "search":
        idx = json.load(open(sys.argv[2], encoding="utf-8"))
        print(json.dumps(search(idx, sys.argv[3]), ensure_ascii=False, indent=1))
    elif cmd == "validate":
        idx = json.load(open(sys.argv[2], encoding="utf-8"))
        claims = json.load(open(sys.argv[3], encoding="utf-8"))
        claims = claims.get("claims", claims) if isinstance(claims, dict) else claims
        json.dump(validate_answer(claims, idx), open(sys.argv[4], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"kb validate -> {sys.argv[4]}")
    else:
        print("usage: kb.py index <materials.json> <out.json> | search <index.json> <query> "
              "| validate <index.json> <claims.json> <out.json>")
        sys.exit(2)
