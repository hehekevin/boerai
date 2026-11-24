"""Annotation extraction, note structuring and knowledge linking.

批注（annotations.json）：[{anno_id, file, file_sha256, loc {page, block?},
  kind: highlight|underline|margin|handwrite, color?, quote, comment?}]
笔记（notes.json）：[{note_id, kind: question|method|conclusion|reuse|doubt,
  text, anchor: {anno_id | {file, loc, quote}}, links: [note_id]}]

引擎职责：
  - 锚点核验：批注 quote 必须在所标文件所标 block 中逐字存在
  - 类型保真：highlight/underline/margin/handwrite 不混类；颜色含义保留
  - 笔记论断必须挂原文片段（anchor 齐全，quote 逐字核验）
  - 关联必须声明依据（shared_term 之外须 agent 理由）；过度连接检测
  - 检索入口：按 kind/tag/来源文件检索，返回可回溯条目
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

ANNO_KINDS = {"highlight", "underline", "margin", "handwrite"}
NOTE_KINDS = {"question", "method", "conclusion", "reuse", "doubt"}


def validate_annotations(annos: list[dict], blocks_by_file: dict[str, list[dict]]) -> dict:
    problems, out = [], []
    for a in annos:
        aid = a.get("anno_id", "?")
        ap = []
        if str(a.get("kind", "")) not in ANNO_KINDS:
            ap.append(f"invalid kind '{a.get('kind')}'")
        f = a.get("file", "")
        loc = (a.get("loc") or {})
        blocks = blocks_by_file.get(f)
        if blocks is None:
            ap.append(f"file '{f}' not in materials")
        else:
            blk = str(loc.get("block") or loc.get("page") or "")
            r = locate.verify_quote(blocks, blk, a.get("quote", ""))
            if not r["verified"]:
                ap.append(f"anchor unverified: {r['reason']}")
        if not (a.get("quote") or "").strip():
            ap.append("annotation without quoted source text")
        out.append({"anno_id": aid, "ok": not ap, "problems": ap})
        problems += [f"{aid}: {p}" for p in ap]
    by_kind = {}
    for a in annos:
        by_kind[a.get("kind")] = by_kind.get(a.get("kind"), 0) + 1
    return {"per_annotation": out, "by_kind": by_kind, "problems": problems,
            "ok": not problems,
            "rule": "批注锚点逐字核验；类型与颜色原样保留，不混类不抹平"}


def validate_notes(notes: list[dict], annos: list[dict],
                   blocks_by_file: dict[str, list[dict]]) -> dict:
    anno_ids = {a.get("anno_id") for a in annos}
    problems = []
    for n in notes:
        nid = n.get("note_id", "?")
        if str(n.get("kind", "")) not in NOTE_KINDS:
            problems.append(f"{nid}: invalid kind")
        anc = n.get("anchor") or {}
        if "anno_id" in anc:
            if anc["anno_id"] not in anno_ids:
                problems.append(f"{nid}: anchor anno_id not found")
        else:
            f, loc = anc.get("file", ""), (anc.get("loc") or {})
            blocks = blocks_by_file.get(f)
            if blocks is None:
                problems.append(f"{nid}: anchor file not in materials")
            else:
                r = locate.verify_quote(blocks, str(loc.get("block") or loc.get("page") or ""),
                                        anc.get("quote", ""))
                if not r["verified"]:
                    problems.append(f"{nid}: anchor quote unverified ({r['reason']})")
        for lk in n.get("links") or []:
            if not isinstance(lk, dict) or not lk.get("basis"):
                problems.append(f"{nid}: link without basis (关联依据必填)")
    return {"n_notes": len(notes), "problems": problems, "ok": not problems,
            "rule": "笔记论断必须挂原文片段；关联必须写依据，共享一个术语不算充分依据"}


def link_notes(notes: list[dict], min_shared_terms: int = 2) -> dict:
    """候选关联：共享 ≥2 个实词才作为候选；最终关联由 Agent 写 basis 确认。"""
    def words(t):
        return {w.lower() for w in re.findall(r"[A-Za-z]{4,}|[一-鿿]{2,}", t or "")}
    ws = {n["note_id"]: words(n.get("text", "")) for n in notes}
    cands = []
    ids = sorted(ws)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = ws[a] & ws[b]
            if len(shared) >= min_shared_terms:
                cands.append({"a": a, "b": b, "shared_terms": sorted(shared),
                              "status": "candidate",
                              "note": "候选关联，Agent 须确认并写 basis 才生效"})
    return {"candidates": cands,
            "rule": f"共享词数 >= {min_shared_terms} 才成候选；关键词重合不直接成关联"}


def search_notes(notes: list[dict], query: str = "", kind: str = "",
                 file: str = "") -> dict:
    q = query.lower()
    hits = []
    for n in notes:
        if kind and n.get("kind") != kind:
            continue
        anc = n.get("anchor") or {}
        if file and anc.get("file") != file:
            continue
        if q and q not in (n.get("text", "") + " " + anc.get("quote", "")).lower():
            continue
        hits.append({"note_id": n.get("note_id"), "kind": n.get("kind"),
                     "text": (n.get("text") or "")[:200], "anchor": anc})
    return {"hits": hits, "n": len(hits),
            "note": "每条命中都带 anchor，可回原文核对；召回不足时放宽 query 或 kind"}


def _demo() -> int:
    blocks = {"paperA.pdf": [
        {"loc": "p.2", "text": "The catalyst achieves 92% degradation under visible light."},
        {"loc": "p.4", "text": "We suspect the method fails for hydrophobic dyes."}]}
    annos = [
        {"anno_id": "A1", "file": "paperA.pdf", "loc": {"page": "p.2"},
         "kind": "highlight", "color": "yellow",
         "quote": "92% degradation under visible light", "comment": "核心结果"},
        {"anno_id": "A2", "file": "paperA.pdf", "loc": {"page": "p.4"},
         "kind": "margin", "quote": "fails for hydrophobic dyes", "comment": "边界条件"},
    ]
    va = validate_annotations(annos, blocks)
    assert va["ok"] and va["by_kind"] == {"highlight": 1, "margin": 1}
    notes = [
        {"note_id": "N1", "kind": "conclusion", "text": "催化剂在可见光下降解率达 92%",
         "anchor": {"anno_id": "A1"}},
        {"note_id": "N2", "kind": "doubt", "text": "对疏水染料可能失效，需验证",
         "anchor": {"anno_id": "A2"}, "links": []},
    ]
    vn = validate_notes(notes, annos, blocks)
    assert vn["ok"]
    bad_anno = [{"anno_id": "A9", "file": "paperA.pdf", "loc": {"page": "p.2"},
                 "kind": "highlight", "quote": "99% degradation"}]
    assert not validate_annotations(bad_anno, blocks)["ok"]  # 锚点漂移被抓
    lk = link_notes(notes)
    sr = search_notes(notes, query="降解")
    assert sr["n"] >= 1
    print(json.dumps({"demo": "notes", "annos_ok": va["ok"], "notes_ok": vn["ok"],
                      "drift_caught": True, "link_candidates": len(lk["candidates"]),
                      "search_hits": sr["n"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        annos = json.load(open(sys.argv[2], encoding="utf-8"))
        blocks = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = validate_annotations(annos.get("annotations", annos),
                                   blocks.get("files", blocks))
        out = sys.argv[4] if len(sys.argv) > 4 else None
    elif cmd == "notes":
        notes = json.load(open(sys.argv[2], encoding="utf-8"))
        annos = json.load(open(sys.argv[3], encoding="utf-8"))
        blocks = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = validate_notes(notes.get("notes", notes), annos.get("annotations", annos),
                             blocks.get("files", blocks))
        out = sys.argv[5] if len(sys.argv) > 5 else None
    elif cmd == "link":
        notes = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = link_notes(notes.get("notes", notes))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd == "search":
        notes = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = search_notes(notes.get("notes", notes), query=sys.argv[3] if len(sys.argv) > 3 else "")
        out = None
    else:
        print("usage: notes.py [validate|notes|link|search] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ok={rep.get('ok', True)}")
    sys.exit(0 if rep.get("ok", True) else 1)
