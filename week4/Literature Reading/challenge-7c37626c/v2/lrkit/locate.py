"""Evidence locating: 每条结论必须能回到原文的具体位置。

材料由 hk.extract 切成带 loc 的 blocks（p.N / para.N / block.N / 表格行）。
本模块提供可复算的定位原语：
  - search_text: 按关键词在 blocks 中定位，返回 file+loc+原文片段
  - verify_quote: 核验交付物里的引文是否真实存在于所标位置（防编造）
  - split_claims: 把复杂论断机械拆成子判断候选（Agent 语义确认）
  - coverage_report: 已读/未读章节清单，配合 QA 的 coverage 字段

引用规则：引文必须 ≤ quote_max 字符、在所标 block 中可逐字匹配
（允许空白折叠）。匹配不上即判 unverified，不得放行。
"""
from __future__ import annotations

import json
import re
import sys

QUOTE_MAX = 240


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def search_text(blocks: list[dict], query: str, max_hits: int = 20) -> list[dict]:
    """blocks: [{loc, text, source?}]. query: 空格分隔的词，全部命中才算。"""
    terms = [t for t in re.split(r"\s+", query.strip()) if t]
    hits = []
    for b in blocks:
        text = _norm_ws(b.get("text", ""))
        low = text.lower()
        if all(t.lower() in low for t in terms):
            # 截取首个命中词附近的片段作为定位预览
            i = low.find(terms[0].lower()) if terms else 0
            start = max(0, i - 60)
            hits.append({"loc": b.get("loc", "?"), "source": b.get("source", ""),
                         "snippet": text[start:start + QUOTE_MAX],
                         "chars": len(b.get("text", ""))})
            if len(hits) >= max_hits:
                break
    return hits


def verify_quote(blocks: list[dict], loc: str, quote: str) -> dict:
    """核验引文：loc 必须存在，quote 折叠空白后必须是该 block 的子串。"""
    q = _norm_ws(quote)
    if not q:
        return {"loc": loc, "verified": False, "reason": "empty quote"}
    if len(q) > QUOTE_MAX:
        return {"loc": loc, "verified": False,
                "reason": f"quote too long ({len(q)} > {QUOTE_MAX})"}
    cand = [b for b in blocks if str(b.get("loc")) == str(loc)]
    if not cand:
        return {"loc": loc, "verified": False, "reason": f"loc '{loc}' not found"}
    for b in cand:
        if q in _norm_ws(b.get("text", "")):
            return {"loc": loc, "verified": True, "reason": "verbatim substring",
                    "source": b.get("source", "")}
    return {"loc": loc, "verified": False,
            "reason": "quote not a verbatim substring of the located block"}


def verify_many(blocks: list[dict], citations: list[dict]) -> dict:
    """citations: [{id, loc, quote}]. 逐条核验并汇总。"""
    out = []
    for c in citations:
        r = verify_quote(blocks, str(c.get("loc", "")), c.get("quote", ""))
        r["id"] = c.get("id", "")
        out.append(r)
    bad = [r for r in out if not r["verified"]]
    return {"results": out, "n": len(out), "verified": len(out) - len(bad),
            "failed": bad, "ok": not bad,
            "rule": "quote must be a verbatim (whitespace-folded) substring of the located block"}


# 子判断类型（与 claims 模块共享）
SUBCLAIM_KINDS = ["fact", "comparison", "causal", "scope"]

_MARKERS = [
    (re.compile(r"(高于|低于|大于|小于|优于|差于|超过|快于|慢于|相比|提高|降低|改善|上升|下降|"
                r"versus|vs\.?|higher|lower|greater|less|outperform|better|worse|compared)",
                re.I), "comparison"),
    (re.compile(r"(导致|引起|因此|使得|从而|促进|抑制|because|therefore|thus|leads? to|"
                r"results? in|enables?|causes?|due to)", re.I), "causal"),
    (re.compile(r"(仅|只|所有|任何|普遍|总是|从不|在.+条件下|范围内|all|any|only|every|"
                r"always|never|under .* conditions|in general)", re.I), "scope"),
]


def split_claims(text: str) -> dict:
    """机械拆分：按句切分，再按并列连词切开；标注候选子判断类型。
    结果只是候选——是否构成独立可核验子判断由 Agent 语义确认。"""
    text = (text or "").strip()
    if not text:
        return {"subclaims": [], "note": "empty claim"}
    sentences = [s.strip() for s in re.split(r"(?<=[。；;!?！？.])\s*|(?<=[。；;！？])", text) if s.strip()]
    pieces = []
    for s in sentences:
        for p in re.split(r"，并且|，同时|，而且|；|;|,\s+and\s+|,\s+while\s+", s):
            if p.strip():
                pieces.append(p.strip())
    sub = []
    for i, p in enumerate(pieces, 1):
        kind = "fact"
        for rx, k in _MARKERS:
            if rx.search(p):
                kind = k
                break
        sub.append({"sub_id": f"c{i}", "text": p, "candidate_kind": kind,
                    "needs_agent_confirmation": True})
    return {"subclaims": sub,
            "note": "mechanical split; agent must merge/drop and confirm kinds"}


def coverage_report(materials: list[dict], read_locs: list[dict]) -> dict:
    """materials: hk materials (带 blocks)。read_locs: [{source, loc}]。
    输出已读/未读清单，供 QA 的 coverage 字段与审计使用。"""
    read = {(r.get("source", ""), str(r.get("loc", ""))) for r in read_locs}
    report, unread = [], 0
    for i, m in enumerate(materials, 1):
        sid = m.get("source") or f"S{i}"
        blocks = m.get("blocks") or []
        total = len(blocks)
        n_read = sum(1 for b in blocks if (sid, str(b.get("loc"))) in read)
        unread += total - n_read
        report.append({"source": sid, "path": m.get("path", ""), "blocks": total,
                       "read": n_read, "unread": total - n_read})
    return {"sources": report, "total_unread": unread,
            "note": "unread blocks must be explained in the deliverable coverage field"}


def _demo() -> int:
    blocks = [
        {"loc": "p.1", "source": "S1", "text": "We propose a synthetic alloy. The yield "
         "strength reaches 520 MPa at 25 C, higher than the 410 MPa baseline."},
        {"loc": "p.2", "source": "S1", "text": "The treatment causes grain refinement; "
         "therefore ductility improves. This holds only under slow cooling."},
    ]
    hits = search_text(blocks, "yield strength 520")
    assert hits and hits[0]["loc"] == "p.1", hits
    v = verify_many(blocks, [
        {"id": "e1", "loc": "p.1", "quote": "yield   strength reaches 520 MPa"},
        {"id": "e2", "loc": "p.2", "quote": "yield strength reaches 520 MPa"},
        {"id": "e3", "loc": "p.9", "quote": "anything"},
    ])
    assert v["verified"] == 1 and not v["ok"]
    sp = split_claims("强度提高 27%，并且塑性改善；该结论仅在缓冷条件下成立。")
    kinds = [s["candidate_kind"] for s in sp["subclaims"]]
    assert len(sp["subclaims"]) == 3 and "comparison" in kinds and "scope" in kinds, sp
    cov = coverage_report([{"blocks": blocks, "path": "paper.txt"}],
                          [{"source": "S1", "loc": "p.1"}])
    assert cov["total_unread"] == 1
    print(json.dumps({"demo": "locate", "hits": len(hits), "verified": v["verified"],
                      "subclaims": len(sp["subclaims"]), "unread": cov["total_unread"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    blocks = json.load(open(sys.argv[2], encoding="utf-8"))
    blocks = blocks.get("blocks", blocks)
    if cmd == "search":
        print(json.dumps(search_text(blocks, sys.argv[3]), ensure_ascii=False, indent=1))
    elif cmd == "verify":
        cits = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = verify_many(blocks, cits.get("citations", cits))
        out = sys.argv[4] if len(sys.argv) > 4 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"verified {rep['verified']}/{rep['n']} ok={rep['ok']}")
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "split":
        print(json.dumps(split_claims(open(sys.argv[3], encoding="utf-8").read()),
                         ensure_ascii=False, indent=1))
    elif cmd == "coverage":
        mats = json.load(open(sys.argv[3], encoding="utf-8"))
        read_locs = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = coverage_report(mats.get("materials", mats), read_locs.get("read", read_locs))
        json.dump(rep, open(sys.argv[5], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"total_unread={rep['total_unread']} -> {sys.argv[5]}")
    else:
        print("usage: locate.py [search|verify|split|coverage] ...")
        sys.exit(2)
