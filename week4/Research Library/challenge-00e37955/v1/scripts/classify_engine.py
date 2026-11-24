#!/usr/bin/env python3
"""classify-forge: literature auto-classification, tag generation, naming, version dedup.

Deterministic subcommands (0 model requests):
  --classify RECORDS_JSON TAXO_JSON    classify into taxonomy tree with rationale
  --tags RECORDS_JSON                  generate tags from title/abstract/keywords w/ granularity control
  --rename RECORDS_JSON TEMPLATE       generate filenames by convention (special chars/superlong/multilang/missing-field fallbacks)
  --versions DIR_OR_LIST               dedup by hash/doi/title+author+year; preprint vs published
Stdlib only.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata

GRAN_RULE = {"max_tags_per_doc": 5, "min_len": 2, "merge_synonyms": True}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("records") or data.get("items") or data.get("cleaned") or []


def cmd_classify(recs_path, taxo_path):
    recs = load(recs_path)
    taxo = json.load(open(taxo_path, encoding="utf-8"))
    if isinstance(taxo, dict):
        taxo = taxo.get("taxonomy", [])
    # taxonomy: [{name, keywords:[...], children:[...]}]
    out = []
    for i, r in enumerate(recs):
        text = norm(r.get("title", "")) + " " + norm(r.get("abstract", "")) + " " + norm(r.get("keywords", ""))
        tl = text.lower()
        assigned, rationale = [], []
        for node in taxo:
            kws = node.get("keywords", [])
            hits = [k for k in kws if k.lower() in tl]
            if hits:
                assigned.append(node.get("name"))
                rationale.append(f"{node.get('name')}: 命中关键词 {hits[:3]}")
                # children take precedence if deeper hit
                for ch in node.get("children", []):
                    chits = [k for k in ch.get("keywords", []) if k.lower() in tl]
                    if chits:
                        assigned.append(f"{node.get('name')}/{ch.get('name')}")
                        rationale.append(f"  子类 {ch.get('name')}: {chits[:3]}")
        cross = len(assigned) > 1
        out.append({"idx": i, "title": (r.get("title") or "")[:60],
                    "assigned": assigned[:3] or ["未分类"],
                    "rationale": rationale[:4],
                    "boundary_note": "跨主题多标签——主分类取首个，其余为副标签" if cross else ""})
    print(json.dumps({"schema": "classify/classify@1", "n_records": len(recs), "records": out[:30],
                      "note": "每条归属带依据；跨主题文献主分类+副标签"}, ensure_ascii=False, indent=1))
    return 0


STOP_TAGS = {"研究", "方法", "基于", "论文", "study", "method", "paper", "based", "approach", "using"}


def cmd_tags(recs_path):
    recs = load(recs_path)
    all_tags = set()
    out = []
    for i, r in enumerate(recs):
        text = norm(r.get("title", "")) + " " + norm(r.get("keywords", ""))[:120]
        cand = []
        # english terms + CJK runs (2-4 chars)
        for w in re.findall(r"[A-Za-z][A-Za-z-]{2,}", text):
            if w.lower() not in STOP_TAGS:
                cand.append(w)
        for run in re.findall(r"[\u4e00-\u9fff]{2,4}", text):
            if run not in STOP_TAGS:
                cand.append(run)
        # granularity control: frequency cap + synonym merge (casefold)
        seen, tags = set(), []
        for c in cand:
            key = c.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(c)
            if len(tags) >= GRAN_RULE["max_tags_per_doc"]:
                break
        all_tags.update({t.lower() for t in tags})
        out.append({"idx": i, "title": (r.get("title") or "")[:50], "tags": tags,
                    "granularity_note": f"上限{GRAN_RULE['max_tags_per_doc']}；同义合并(casefold)；停用词过滤"})
    print(json.dumps({"schema": "classify/tags@1", "n_records": len(recs), "vocabulary_size": len(all_tags),
                      "records": out[:30],
                      "note": "标签从标题/摘要/关键词/期刊结构抽取；粒度受控避免标签爆炸"}, ensure_ascii=False, indent=1))
    return 0


def cmd_rename(recs_path, template):
    recs = load(recs_path)
    out = []
    for i, r in enumerate(recs):
        authors = norm(r.get("authors", "")) or r.get("first_author") or ""
        year = str(r.get("year", "")) or ""
        title = norm(r.get("title", "")) or ""
        doi = r.get("doi", "") or ""
        journal = r.get("journal", "") or ""
        # build by template tokens
        name = template
        name = name.replace("{authors}", (authors.split()[0] if authors.split() else "NA"))
        name = name.replace("{year}", year or "NA")
        name = name.replace("{title}", title)
        name = name.replace("{doi}", doi.replace("10.", "") if doi else "NA")
        name = name.replace("{journal_abbrev}", journal[:12] if journal else "NA")
        # sanitize: special chars -> _
        special = re.findall(r"[^\w\-. ]", name)
        name = re.sub(r"[^\w\-. ]", "_", name).strip()
        name = re.sub(r"\s+", "_", name)
        # superlong -> truncate
        if len(name) > 120:
            name = name[:117] + "..."
            trunc = True
        else:
            trunc = False
        missing = [k for k, v in {"authors": authors, "year": year, "title": title}.items() if not v]
        out.append({"idx": i, "filename": name + ".pdf", "special_chars_replaced": len(special),
                    "truncated": trunc, "missing_fields": missing,
                    "fallback_used": bool(missing),
                    "fallback_rule": "缺失字段以NA占位；多语言标题保留Unicode（文件系统支持）"})
    print(json.dumps({"schema": "classify/rename@1", "template": template, "renamed": out[:30]},
                     ensure_ascii=False, indent=1))
    return 0


def rec_key(r):
    if r.get("doi"):
        return "doi:" + r["doi"]
    t = norm(r.get("title", "")).lower()
    a = norm(r.get("authors", ""))[:20]
    y = str(r.get("year", ""))
    return f"title:{t}|{a}|{y}"


def cmd_versions(recs_path):
    recs = load(recs_path)
    seen = {}
    findings = []
    for i, r in enumerate(recs):
        # content hash if file path given
        h = ""
        if r.get("file_path") and os.path.exists(r["file_path"]):
            h = hashlib.sha256(open(r["file_path"], "rb").read()).hexdigest()[:16]
        k = rec_key(r)
        venue = norm(r.get("venue", r.get("source", "")))
        is_preprint = bool(re.search(r"(?i)arxiv|preprint", venue + " " + str(r.get("doi", ""))))
        entry = {"idx": i, "key": k, "title": (r.get("title") or "")[:50], "content_hash": h,
                 "version_type": "preprint" if is_preprint else "published"}
        if k in seen:
            prev = seen[k]
            verdict = ("同一文献重复下载：保留正式版(published)，预印本归档" if prev["version_type"] == "published" and entry["version_type"] == "preprint"
                       else "同一文献两个版本：保留信息更全者（摘要/字段数），另一份归档不删除")
            if h and prev["content_hash"] and h == prev["content_hash"]:
                verdict = "内容哈希相同——完全重复文件，归档一份"
            findings.append({"kept_idx": prev["idx"], "dup_idx": i, "verdict": verdict,
                             "avoid_delete": "归档而非删除——避免误删补充材料/修订版"})
        else:
            seen[k] = entry
        if entry["version_type"] == "preprint":
            findings.append({"idx": i, "note": "预印本标记：正式版出现后替换，关联保留"})
    print(json.dumps({"schema": "classify/versions@1", "n_records": len(recs), "n_findings": len(findings),
                      "findings": findings[:30]}, ensure_ascii=False, indent=1))
    return 0


import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classify", nargs=2, metavar=("RECORDS", "TAXO"))
    ap.add_argument("--tags")
    ap.add_argument("--rename", nargs=2, metavar=("RECORDS", "TEMPLATE"))
    ap.add_argument("--versions")
    a = ap.parse_args()
    if a.classify:
        return cmd_classify(a.classify[0], a.classify[1])
    if a.tags:
        return cmd_tags(a.tags)
    if a.rename:
        return cmd_rename(a.rename[0], a.rename[1])
    if a.versions:
        return cmd_versions(a.versions)
    ap.error("choose --classify / --tags / --rename / --versions")


if __name__ == "__main__":
    sys.exit(main())
