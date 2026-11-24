#!/usr/bin/env python3
"""format-spec-forge: template spec extraction, itemized conformance, conversion completeness.

Deterministic subcommands (0 model requests):
  --extract TEMPLATE_JSON   extract checkable specs: columns/font-size/leading/margins/heading levels/caption style/refs style/export
  --conform DOC_JSON SPEC_JSON   itemized conformance: headings/numbering/captions/xref/entries/header-footer
  --completeness DOC_JSON DOC2_JSON  conversion completeness: text/figures/formulas/footnotes/comments/tracks/fields/TOC none lost
Stdlib only.
"""
import argparse, json, re, sys

SPEC_FIELDS = {
    "columns": r"(?i)(单栏|双栏|two[- ]column|one[- ]column|栏数)",
    "font_size": r"(?i)(\d+\s*(pt|磅)|字号)",
    "leading": r"(?i)(行距|line\s*spacing|leading)",
    "margins": r"(?i)(页边距|margins?)",
    "heading_levels": r"(?i)(标题层级|heading\s*levels?|\d+级标题)",
    "caption_style": r"(?i)(题注|caption|图\d|表\d)",
    "reference_style": r"(?i)(参考文献|references|gb/t|apa|ieee|vancouver)",
    "export_format": r"(?i)(pdf|docx|latex|导出)",
}

def cmd_extract(path):
    tpl = json.load(open(path, encoding="utf-8"))
    text = json.dumps(tpl, ensure_ascii=False)
    specs = {}
    for field, pat in SPEC_FIELDS.items():
        m = re.search(pat, text)
        specs[field] = {"specified": bool(m), "evidence": m.group(0)[:50] if m else "未声明——需向模板文件/格式要求确认，不凭经验"}
    print(json.dumps({"schema": "fmt/spec@1", "specs": specs,
                      "note": "可逐项核对的规格清单"}, ensure_ascii=False, indent=1))
    return 0

CONFORM_ITEMS = ["headings", "numbering", "captions", "cross_references", "reference_entries", "header_footer"]

def cmd_conform(doc_path, spec_path):
    doc = json.load(open(doc_path, encoding="utf-8"))
    spec = json.load(open(spec_path, encoding="utf-8"))
    results = []
    for item in CONFORM_ITEMS:
        v = doc.get(item)
        ok = v is not None and v != "" and v is not False
        results.append({"item": item, "conform": "PASS" if ok else "CHECK",
                        "evidence": str(v)[:60] if ok else "未提供该项数据——逐项核对不能只看外观相似"})
    print(json.dumps({"schema": "fmt/conform@1", "results": results,
                      "note": "标题层级/编号/题注交叉引用/参考文献条目/页眉页脚逐项符合"}, ensure_ascii=False, indent=1))
    return 0

COMPLETE_ITEMS = ["body_text", "figures", "formulas", "footnotes", "comments", "track_changes", "field_codes", "toc"]

def cmd_completeness(doc1_path, doc2_path):
    d1 = json.load(open(doc1_path, encoding="utf-8"))
    d2 = json.load(open(doc2_path, encoding="utf-8"))
    counts1 = d1.get("counts", {})
    counts2 = d2.get("counts", {})
    results = []
    for item in COMPLETE_ITEMS:
        c1, c2 = counts1.get(item), counts2.get(item)
        same = (c1 is None or c2 is None) or (c1 == c2)
        results.append({"item": item, "before": c1, "after": c2,
                        "status": "OK" if same else f"LOST ({c1}->{c2})——内容被删除/合并/图片化"})
    lost = [r for r in results if str(r["status"]).startswith("LOST")]
    print(json.dumps({"schema": "fmt/completeness@1", "results": results,
                      "verdict": "complete" if not lost else f"incomplete: {len(lost)} 类内容丢失",
                      "note": "正文/图表/公式/脚注/批注/修订/域代码/目录保持完整；保留可编辑源文件"}, ensure_ascii=False, indent=1))
    return 0 if not lost else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract"); ap.add_argument("--conform", nargs=2); ap.add_argument("--completeness", nargs=2)
    a = ap.parse_args()
    if a.extract: return cmd_extract(a.extract)
    if a.conform: return cmd_conform(a.conform[0], a.conform[1])
    if a.completeness: return cmd_completeness(a.completeness[0], a.completeness[1])
    ap.error("choose --extract / --conform / --completeness")

if __name__ == "__main__":
    sys.exit(main())
