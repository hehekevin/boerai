#!/usr/bin/env python3
"""file-retrieval-forge: file search with section location, hard filters, evidence backlink, version dedup.

Deterministic subcommands (0 model requests):
  --find DIR --terms "w1,w2"   search files by terms (filename + content), rank by hit count
  --locate FILE --term W       locate term hits to line:section with context (evidence backlink)
  --filter DIR --json FILTERS  hard filters (year/type/keyword/ext); unsatisfiable reported not relaxed
  --versions DIR               detect duplicate/old-version files by name pattern & content hash
Stdlib only.
"""
import argparse
import hashlib
import json
import os
import re
import sys

TEXT_EXT = {".py", ".yaml", ".yml", ".json", ".toml", ".ini", ".csv", ".tsv", ".log", ".txt", ".md", ".tex", ".bib", ".rst"}
MAX_SIZE = 2 * 1024 * 1024
SECTION_RE = re.compile(r"^(#{1,6})\s+(.+)$|^(\\section\{)(.+?)(\})$", re.M)


def walk(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [x for x in dn if x not in {".git", "__pycache__", "node_modules"}]
        for f in fn:
            out.append(os.path.join(dp, f))
    return sorted(out)


def is_text(path):
    return os.path.splitext(path)[1].lower() in TEXT_EXT and os.path.getsize(path) <= MAX_SIZE


def sections_of(text):
    """Extract (line_no, heading) list."""
    secs = []
    for i, line in enumerate(text.splitlines(), 1):
        m = SECTION_RE.match(line)
        if m:
            secs.append({"line": i, "heading": (m.group(2) or m.group(4))[:80]})
    return secs


def current_section(sections, line_no):
    cur = None
    for s in sections:
        if s["line"] <= line_no:
            cur = s
        else:
            break
    return cur


def cmd_find(root, terms):
    term_list = [t.strip() for t in terms.split(",") if t.strip()]
    results = []
    for p in walk(root):
        base = os.path.basename(p)
        fname_hits = sum(1 for t in term_list if norm(t) in norm(base))
        content_hits = 0
        if is_text(p):
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
                content_hits = sum(len(re.findall(re.escape(norm(t)), norm(text))) for t in term_list)
            except OSError:
                pass
        score = fname_hits * 3 + content_hits
        if score > 0:
            results.append({"path": p, "score": score, "filename_hits": fname_hits,
                            "content_hits": content_hits,
                            "evidence_backlink": f"{p} (filename:{fname_hits}, content:{content_hits})"})
    results.sort(key=lambda x: -x["score"])
    print(json.dumps({"schema": "filesearch/find@1", "terms": term_list, "n_files_scanned": len(walk(root)),
                      "n_matched": len(results), "results": results[:30],
                      "note": "rank = filename_hits*3 + content_hits；语义级检索由模型在结果基础上复核"}, ensure_ascii=False, indent=1))
    return 0


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def cmd_locate(path, term):
    text = open(path, encoding="utf-8", errors="replace").read()
    secs = sections_of(text)
    t = norm(term)
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if t in norm(line):
            sec = current_section(secs, i)
            hits.append({"line": i, "section": sec["heading"] if sec else "(无章节)",
                         "section_line": sec["line"] if sec else None,
                         "excerpt": line.strip()[:120]})
    print(json.dumps({"schema": "filesearch/locate@1", "file": path, "term": term,
                      "n_hits": len(hits), "hits": hits[:20],
                      "note": "定位到行号+章节标题；PDF物理页与印刷页错位需按页眉修正"}, ensure_ascii=False, indent=1))
    return 0


def cmd_filter(root, filters_path):
    filters = json.load(open(filters_path, encoding="utf-8"))
    unsatisfiable = []
    results = []
    for p in walk(root):
        base = os.path.basename(p)
        ok = True
        for k, v in filters.items():
            if k == "ext":
                if os.path.splitext(p)[1].lower() != v.lower():
                    ok = False
            elif k == "name_contains":
                if norm(v) not in norm(base):
                    ok = False
            elif k == "year":
                m = re.search(r"(20\d{2})", base)
                if not m or m.group(1) != str(v):
                    ok = False
            elif k == "content_contains":
                if is_text(p):
                    try:
                        if norm(v) not in norm(open(p, encoding="utf-8", errors="replace").read()):
                            ok = False
                    except OSError:
                        ok = False
                else:
                    unsatisfiable.append({"filter": k, "reason": f"{p} 不是可读文本，无法应用内容过滤"})
                    ok = False
        if ok:
            results.append(p)
    print(json.dumps({"schema": "filesearch/filter@1", "filters": filters, "n_matched": len(results),
                      "files": results[:30], "unsatisfiable_filters": unsatisfiable[:10],
                      "note": "硬约束执行：条件无法满足时如实报告，不放宽"}, ensure_ascii=False, indent=1))
    return 0


def cmd_versions(root):
    seen = {}
    dupes = []
    for p in walk(root):
        if not is_text(p):
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
        base = os.path.basename(p)
        ver_marker = re.findall(r"(?i)(v\d+|final|old|copy|备份|旧版)", base)
        key = (h,)
        if h in seen:
            dupes.append({"kept": seen[h], "dup": p, "basis": "content_sha256 相同"})
        else:
            seen[h] = p
        if ver_marker:
            dupes.append({"file": p, "basis": f"文件名版本标记 {ver_marker}", "note": "疑似旧版本/副本，不作为独立证据"})
    print(json.dumps({"schema": "filesearch/versions@1", "n_files": len(seen), "n_duplicate_content": len(dupes),
                      "findings": dupes[:30]}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--find", nargs=2, metavar=("DIR", "TERMS"))
    ap.add_argument("--locate", nargs=2, metavar=("FILE", "TERM"))
    ap.add_argument("--filter", nargs=2, metavar=("DIR", "FILTERS_JSON"))
    ap.add_argument("--versions")
    a = ap.parse_args()
    if a.find:
        return cmd_find(a.find[0], a.find[1])
    if a.locate:
        return cmd_locate(a.locate[0], a.locate[1])
    if a.filter:
        return cmd_filter(a.filter[0], a.filter[1])
    if a.versions:
        return cmd_versions(a.versions)
    ap.error("choose --find / --locate / --filter / --versions")


if __name__ == "__main__":
    sys.exit(main())
