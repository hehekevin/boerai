"""Terminology consistency & segment alignment: 翻译辅助簿记。

术语表（glossary.json）：[{source, target, note?}]
对齐表（alignment.json）：[{seg_id, source_loc, source_text, translation,
                           terms_applied: [source 词]}]

引擎职责（不翻译——翻译是 Agent 的事）：
  - 术语一致性：同一 source 词在全文中出现处的译法是否等于术语表 target
  - 漏译/补写检查：对齐表中每个 source 段都有 translation（可空但须标
    omitted+reason）；translation 不得包含材料中不存在的数字
  - 覆盖率统计：已译/未译段数、术语命中率
  - 术语表本身的冲突检测（一词多译未注明条件即报警）
"""
from __future__ import annotations

import json
import re
import sys

_NUM = re.compile(r"\d+(?:\.\d+)?")


def glossary_conflicts(glossary: list[dict]) -> dict:
    by_src = {}
    for g in glossary:
        by_src.setdefault(g.get("source", ""), []).append(g)
    conflicts = []
    for src, items in by_src.items():
        targets = {i.get("target", "") for i in items}
        if len(targets) > 1 and not all(i.get("note") for i in items):
            conflicts.append({"source": src, "targets": sorted(targets),
                              "problem": "一词多译且未注明适用条件"})
    return {"conflicts": conflicts, "n_terms": len(glossary),
            "ok": not conflicts}


def check_terms(glossary: list[dict], alignment: list[dict]) -> dict:
    """每个段落中出现术语表 source 词时，translation 应包含对应 target。"""
    gmap = {}
    for g in glossary:
        if g.get("source"):
            gmap.setdefault(g["source"], []).append(g.get("target", ""))
    misses, hits = [], []
    for seg in alignment:
        src_text = seg.get("source_text", "")
        tgt = seg.get("translation", "")
        if seg.get("omitted"):
            continue
        for s, targets in gmap.items():
            if re.search(re.escape(s), src_text, re.I):
                used = next((t for t in targets if re.search(re.escape(t), tgt)), None)
                if used:
                    hits.append({"seg_id": seg.get("seg_id"), "source": s, "target": used})
                else:
                    misses.append({"seg_id": seg.get("seg_id"), "source": s,
                                   "expected_target": targets,
                                   "translation_preview": tgt[:120]})
    return {"term_hits": len(hits), "term_misses": misses, "ok": not misses,
            "rule": "术语表中的词在源段出现时，译文必须使用术语表译法"}


def check_alignment(alignment: list[dict], source_locs: list[str]) -> dict:
    """逐段对齐簿记：源段全覆盖、无重复、无源段之外的发明内容。"""
    seen = {}
    problems = []
    for seg in alignment:
        loc = str(seg.get("source_loc", ""))
        sid = seg.get("seg_id", "?")
        if loc in seen:
            problems.append(f"source_loc {loc} aligned twice ({seen[loc]}, {sid})")
        seen[loc] = sid
        if not seg.get("omitted") and not (seg.get("translation") or "").strip():
            problems.append(f"{sid}: empty translation without omitted+reason")
        if seg.get("omitted") and not seg.get("reason"):
            problems.append(f"{sid}: omitted without reason")
        # 数字防补写：译文中的数字须出现在源段中
        for n in set(_NUM.findall(seg.get("translation", ""))) - \
                 set(_NUM.findall(seg.get("source_text", ""))):
            problems.append(f"{sid}: number {n} in translation not in source segment")
    missing = [l for l in source_locs if str(l) not in seen]
    return {"aligned": len(alignment), "untranslated_sources": missing,
            "problems": problems, "ok": not problems and not missing,
            "rule": "每段源文必须出现一次；漏译标 omitted+reason；译文不得补写数字"}


def _demo() -> int:
    glossary = [{"source": "photocatalysis", "target": "光催化"},
                {"source": "band gap", "target": "带隙"},
                {"source": "support", "target": "载体", "note": "催化剂语境"},
                {"source": "support", "target": "支持", "note": "论据语境"}]
    gc = glossary_conflicts(glossary)
    assert gc["ok"]  # 多译但注明条件 → 合法
    align = [
        {"seg_id": "seg1", "source_loc": "p.1",
         "source_text": "Photocatalysis uses the band gap of 1.62 eV.",
         "translation": "光催化利用了 1.62 eV 的带隙。"},
        {"seg_id": "seg2", "source_loc": "p.2",
         "source_text": "The support was alumina.",
         "translation": "载体为氧化铝。", "terms_applied": ["support"]},
        {"seg_id": "seg3", "source_loc": "p.3", "source_text": "(figure only)",
         "translation": "", "omitted": True, "reason": "纯图注无正文内容"},
    ]
    tc = check_terms(glossary, align)
    assert tc["ok"] and tc["term_hits"] == 3, tc
    ac = check_alignment(align, ["p.1", "p.2", "p.3"])
    assert ac["ok"], ac
    bad = align + [{"seg_id": "seg4", "source_loc": "p.1",
                    "source_text": "Photocatalysis uses the band gap of 1.62 eV.",
                    "translation": "光催化利用了 1.85 eV 的能隙。"}]
    tc2, ac2 = check_terms(glossary, bad), check_alignment(bad, ["p.1", "p.2", "p.3"])
    assert not tc2["ok"] and not ac2["ok"]
    print(json.dumps({"demo": "terms", "term_hits": tc["term_hits"],
                      "aligned": ac["aligned"],
                      "violations_caught": len(tc2["term_misses"]) + len(ac2["problems"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    glossary = json.load(open(sys.argv[2], encoding="utf-8"))
    glossary = glossary.get("glossary", glossary)
    if cmd == "glossary":
        rep = glossary_conflicts(glossary)
    elif cmd == "terms":
        align = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = check_terms(glossary, align.get("segments", align))
    elif cmd == "align":
        align = json.load(open(sys.argv[3], encoding="utf-8"))
        locs = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = check_alignment(align.get("segments", align), locs.get("source_locs", locs))
    else:
        print("usage: terms.py [glossary|terms|align] ...")
        sys.exit(2)
    if len(sys.argv) > 5 and cmd == "align" or (cmd in ("glossary", "terms") and len(sys.argv) > 4):
        out = sys.argv[-1]
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ok={rep['ok']}")
    sys.exit(0 if rep["ok"] else 1)
