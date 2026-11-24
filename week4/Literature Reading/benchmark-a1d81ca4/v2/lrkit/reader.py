"""Reading-client session ledger: 打开—定位—选中提问—批注—导出 的闭环簿记。

本模块不是 GUI；它是阅读客户端 MVP 的数据层：会话里的每个动作
（open/locate/ask/annotate/export）都落成一条可复核记录，锚点逐字核验，
导出文件含全部锚点与版本信息，供回看与第三方复算。

session 记录：[{seq, action, ts?, payload}]
  open:      {file, file_sha256, pages}
  locate:    {by: page|section|keyword, target, hit_loc}
  ask:       {question, selection: {loc, quote}, answer, evidence: [{loc, quote}]}
  annotate:  {anno_id, loc, quote, kind, comment}
  export:    {path, includes: [...]}
"""
from __future__ import annotations

import json
import os
import sys

from . import locate

ACTIONS = {"open", "locate", "ask", "annotate", "export"}


def validate_session(session: list[dict], blocks: list[dict]) -> dict:
    problems = []
    opened = [s for s in session if s.get("action") == "open"]
    if not opened:
        problems.append("session has no open action")
    for s in session:
        seq, act = s.get("seq", "?"), s.get("action", "?")
        if act not in ACTIONS:
            problems.append(f"seq {seq}: unknown action '{act}'")
            continue
        p = s.get("payload") or {}
        if act in ("ask", "annotate"):
            sel = p.get("selection") or p
            r = locate.verify_quote(blocks, str(sel.get("loc", "")), sel.get("quote", ""))
            if not r["verified"]:
                problems.append(f"seq {seq} ({act}): selection anchor unverified: {r['reason']}")
            if act == "ask":
                if not (p.get("answer") or "").strip():
                    problems.append(f"seq {seq}: ask without answer text")
                for ev in p.get("evidence") or []:
                    r2 = locate.verify_quote(blocks, str(ev.get("loc", "")), ev.get("quote", ""))
                    if not r2["verified"]:
                        problems.append(f"seq {seq}: answer evidence unverified: {r2['reason']}")
    seqs = [s.get("seq") for s in session]
    if seqs != sorted(seqs):
        problems.append("session seq not monotonic (记录顺序破坏)")
    counts = {}
    for s in session:
        counts[s.get("action")] = counts.get(s.get("action"), 0) + 1
    return {"counts": counts, "problems": problems, "ok": not problems,
            "rule": "每个选区/批注/答案证据的锚点逐字核验；闭环动作齐全"}


def locate_target(blocks: list[dict], by: str, target: str) -> dict:
    """页码/段落/关键词定位的统一入口（PDF 物理页与印刷页差异由调用方在
    材料准备时以 loc 约定解决，这里只保证命中可核验）。"""
    if by in ("page", "section", "block"):
        hits = [b for b in blocks if str(b.get("loc")) == str(target)]
        return {"hits": [{"loc": b["loc"], "snippet": (b.get("text") or "")[:200]}
                         for b in hits], "found": bool(hits)}
    if by == "keyword":
        hits = locate.search_text(blocks, target, max_hits=10)
        return {"hits": hits, "found": bool(hits)}
    return {"hits": [], "found": False, "error": f"unknown locate mode '{by}'"}


def export_record(session: list[dict], out_path: str,
                  meta: dict | None = None) -> dict:
    """导出一次阅读任务的可交接记录（锚点+哈希+版本），返回清单。"""
    rec = {"meta": meta or {}, "session": session,
           "actions": [s.get("action") for s in session],
           "note": "导出含全部锚点与文件哈希；回看时按 loc+quote 复核"}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    json.dump(rec, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"path": out_path, "n_actions": len(session), "ok": True}


def _demo() -> int:
    import tempfile
    blocks = [{"loc": "p.3", "text": "The activation energy is 0.87 eV, fitted from "
              "Arrhenius plots between 300 and 400 K."}]
    session = [
        {"seq": 1, "action": "open", "payload": {"file": "paper.pdf",
                                                  "file_sha256": "abc", "pages": 6}},
        {"seq": 2, "action": "locate", "payload": {"by": "keyword",
                                                   "target": "activation energy",
                                                   "hit_loc": "p.3"}},
        {"seq": 3, "action": "ask", "payload": {
            "question": "活化能是多少？",
            "selection": {"loc": "p.3", "quote": "activation energy is 0.87 eV"},
            "answer": "0.87 eV（300–400 K Arrhenius 拟合）。",
            "evidence": [{"loc": "p.3", "quote": "fitted from Arrhenius plots"}]}},
        {"seq": 4, "action": "annotate", "payload": {
            "anno_id": "AN1", "loc": "p.3", "quote": "0.87 eV",
            "kind": "highlight", "comment": "关键拟合参数"}},
    ]
    rep = validate_session(session, blocks)
    assert rep["ok"] and rep["counts"]["ask"] == 1, rep
    hit = locate_target(blocks, "keyword", "activation energy")
    assert hit["found"] and hit["hits"][0]["loc"] == "p.3"
    tmp = tempfile.mkdtemp(prefix="reader-demo-")
    ex = export_record(session, os.path.join(tmp, "reading_record.json"),
                       meta={"paper": "demo", "version": "synthetic"})
    assert os.path.exists(ex["path"])
    bad = session + [{"seq": 5, "action": "annotate", "payload": {
        "anno_id": "AN2", "loc": "p.3", "quote": "0.78 eV", "kind": "highlight"}}]
    assert not validate_session(bad, blocks)["ok"]  # 锚点错位被抓
    print(json.dumps({"demo": "reader", "session_ok": rep["ok"], "counts": rep["counts"],
                      "misanchor_caught": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        sess = json.load(open(sys.argv[2], encoding="utf-8"))
        blocks = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = validate_session(sess.get("session", sess), blocks.get("blocks", blocks))
        if len(sys.argv) > 4:
            json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"ok={rep['ok']} counts={rep['counts']}")
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "locate":
        blocks = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = locate_target(blocks.get("blocks", blocks), sys.argv[3], sys.argv[4])
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    elif cmd == "export":
        sess = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = export_record(sess.get("session", sess), sys.argv[3])
        print(f"exported {rep['n_actions']} actions -> {rep['path']}")
    else:
        print("usage: reader.py [validate|locate|export] ...")
        sys.exit(2)
