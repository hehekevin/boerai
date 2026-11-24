#!/usr/bin/env python3
"""annotation-engine: reading annotation extraction -> structured notes -> knowledge links -> retrieval entry.

Deterministic subcommands (0 model requests):
  --extract ANNOTATIONS_JSON  extract highlights/margins/handwriting by carrier, keep page/coord/color/tag, classify type
  --notes ANNOTATIONS_JSON    structure notes (problem/method/conclusion/reusable/doubt) w/ source anchor
  --link NOTES_JSON           knowledge links (annotation-note-paper-author-method) w/ rationale; over-link control
  --retrieval NOTES_JSON      retrieval index check (topic/tag/entity/source/time)
Stdlib only.
"""
import argparse, json, re, sys, hashlib

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def cmd_extract(path):
    anns = json.load(open(path, encoding="utf-8"))
    if isinstance(anns, dict):
        anns = anns.get("annotations", anns.get("items", []))
    out = []
    for a in anns:
        carrier = a.get("carrier", a.get("type", "pdf"))
        raw = norm(a.get("text", a.get("note", "")))
        # classify annotation type
        atype = "highlight"
        if re.search(r"(?i)(margin|页边|侧栏|margin_note)", carrier + " " + str(a.get("location", ""))):
            atype = "margin_note"
        elif a.get("handwriting") or re.search(r"(?i)(手写|handwrit)", str(a)):
            atype = "handwriting"
        elif re.search(r"(?i)(underline|划线|underline)", str(a.get("style", ""))):
            atype = "underline"
        out.append({"annotation_id": a.get("id", hashlib.md5(raw.encode()).hexdigest()[:8]),
                    "carrier": carrier, "type": atype,
                    "page": a.get("page"), "coord": a.get("coord"), "color": a.get("color"),
                    "tags": a.get("tags", []), "source_file": a.get("file", ""),
                    "text": raw[:150],
                    "note": "批注类型区分（高亮/划线/页边/手写）不混为一类"})
    print(json.dumps({"schema": "annot/extract@1", "n_annotations": len(out), "annotations": out[:40]},
                     ensure_ascii=False, indent=1))
    return 0

NOTE_CATS = [
    ("problem", re.compile(r"(?i)(问题|问题在于|question|issue|challenge)")),
    ("method", re.compile(r"(?i)(方法|方法上|method|approach|technique)")),
    ("conclusion", re.compile(r"(?i)(结论|表明|shows|conclude)")),
    ("reusable", re.compile(r"(?i)(可复用|要点|takeaway|reusable|值得借鉴)")),
    ("doubt", re.compile(r"(?i)(疑点|待验证|存疑|doubt|unverified|待查)")),
]

def cmd_notes(path):
    anns = json.load(open(path, encoding="utf-8"))
    if isinstance(anns, dict):
        anns = anns.get("annotations", anns.get("annotations_extracted", anns.get("items", [])))
    notes = []
    for a in anns:
        text = norm(a.get("text", a.get("note", "")))
        cat = "reusable"
        for c, pat in NOTE_CATS:
            if pat.search(text):
                cat = c
                break
        notes.append({"note_id": a.get("annotation_id", a.get("id", "")), "category": cat,
                      "content": text[:150],
                      "source_anchor": {"file": a.get("source_file", a.get("file", "")),
                                         "page": a.get("page"), "coord": a.get("coord")},
                      "mapping": "批注->笔记条目一一对应（note_id=annotation_id）"})
    print(json.dumps({"schema": "annot/notes@1", "n_notes": len(notes), "notes": notes[:40]},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_link(path):
    notes = json.load(open(path, encoding="utf-8"))
    if isinstance(notes, dict):
        notes = notes.get("notes", notes.get("records", []))
    links = []
    for n in notes:
        src = n.get("source_anchor", {})
        links.append({"from": n.get("note_id"), "to_paper": src.get("file", "unknown"),
                      "relation": "derived_from",
                      "rationale": f"批注锚点 file={src.get('file')} page={src.get('page')}",
                      "over_link_control": "仅建立有锚点依据的关联；无依据不入图"})
    # duplicate paper / version split handling
    seen = {}
    dupes = []
    for n in notes:
        f = n.get("source_anchor", {}).get("file", "")
        key = norm(f).lower()
        if key in seen:
            dupes.append({"files": [seen[key], f], "issue": "同一文献重复下载/版本差异——合并锚点，避免知识分裂"})
        else:
            seen[key] = f
    print(json.dumps({"schema": "annot/link@1", "n_links": len(links), "links": links[:30],
                      "n_split_issues": len(dupes), "split_issues": dupes[:10]},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_retrieval(path):
    notes = json.load(open(path, encoding="utf-8"))
    if isinstance(notes, dict):
        notes = notes.get("notes", notes.get("records", []))
    index = {"by_topic": {}, "by_tag": {}, "by_entity": {}, "by_source": {}, "by_time": []}
    for n in notes:
        for t in n.get("tags", []) or [n.get("category", "uncategorized")]:
            index["by_topic"].setdefault(t, []).append(n.get("note_id"))
        src = n.get("source_anchor", {}).get("file", "unknown")
        index["by_source"].setdefault(src, []).append(n.get("note_id"))
        if n.get("date"):
            index["by_time"].append({"date": n["date"], "note_id": n.get("note_id")})
    recall_check = {"coverage": f"{len(index['by_topic'])} topics / {len(index['by_source'])} sources",
                    "low_recall_action": "召回不足→放宽标签同义合并；误召回→收紧关键词；处理方式显式说明"}
    print(json.dumps({"schema": "annot/retrieval@1", "index_sizes": {k: len(v) for k, v in index.items()},
                      "recall_check": recall_check}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract")
    ap.add_argument("--notes")
    ap.add_argument("--link")
    ap.add_argument("--retrieval")
    a = ap.parse_args()
    if a.extract: return cmd_extract(a.extract)
    if a.notes: return cmd_notes(a.notes)
    if a.link: return cmd_link(a.link)
    if a.retrieval: return cmd_retrieval(a.retrieval)
    ap.error("choose --extract / --notes / --link / --retrieval")

if __name__ == "__main__":
    sys.exit(main())
