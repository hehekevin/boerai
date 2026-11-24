#!/usr/bin/env python3
"""compare-matrix-forge: cross-paper comparison matrix with comparability & conflict attribution.

Deterministic subcommands (0 model requests):
  --matrix PAPERS_JSON     build paper x field comparison matrix (unified field defs)
  --comparable MATRIX_JSON comparability verdict per field (same-condition subset)
  --conflicts MATRIX_JSON  conflict attribution: sample/method/condition/metric
Stdlib only.
"""
import argparse, json, re, sys, unicodedata

CANON_FIELDS = ["research_object", "data_source", "method", "conditions", "metrics", "main_result", "limitations"]


def cmd_matrix(papers_path):
    papers = json.load(open(papers_path, encoding="utf-8"))
    if isinstance(papers, dict):
        papers = papers.get("papers", [])
    rows = []
    for p in papers:
        rec = {"paper_id": p.get("paper_id", p.get("id", "")), "fields": {}, "field_sources": {}}
        for f in CANON_FIELDS:
            v = p.get(f)
            rec["fields"][f] = v
            rec["field_sources"][f] = {"from": p.get("paper_id", "?"), "metric_unit": p.get(f + "_unit", ""),
                                        "note": "值随口径记录（单位/数据集/指标口径）" if v else "missing"}
        rows.append(rec)
    print(json.dumps({"schema": "compare/matrix@1", "n_papers": len(papers), "fields": CANON_FIELDS,
                      "matrix": rows,
                      "note": "统一字段定义使逐格对照有意义"}, ensure_ascii=False, indent=1))
    return 0


def cmd_comparable(matrix_path):
    data = json.load(open(matrix_path, encoding="utf-8"))
    rows = data.get("matrix", data if isinstance(data, list) else [])
    verdicts = []
    for f in CANON_FIELDS:
        vals = [(r["paper_id"], r["fields"].get(f)) for r in rows]
        non_missing = [(pid, v) for pid, v in vals if v]
        if len(non_missing) < 2:
            verdicts.append({"field": f, "comparable": "N/A", "reason": "可用值不足2条"})
            continue
        # normalize condition descriptors
        conds = {str(r["fields"].get("conditions", "")).lower()[:40] for r in rows if r["fields"].get(f)}
        same_cond = len(conds) <= 1
        verdicts.append({"field": f, "comparable": "full" if same_cond else "subset_only",
                          "reason": "条件描述一致——可直接比较" if same_cond else
                                    f"条件差异 {len(conds)} 种——只能在可比子集内比较",
                          "subsets": sorted(conds)[:4]})
    print(json.dumps({"schema": "compare/comparable@1", "verdicts": verdicts}, ensure_ascii=False, indent=1))
    return 0


ATTRIB_PATTERNS = [
    ("sample", re.compile(r"(?i)(n\s*=|samples?|patients?|样本|队列)")),
    ("method", re.compile(r"(?i)(method|model|algorithm|架构|方法|基线|baseline)")),
    ("condition", re.compile(r"(?i)(setting|environment|条件|设置|划分|split)")),
    ("metric", re.compile(r"(?i)(metric|measure|指标|口径|accuracy|f1|定义)")),
]


def cmd_conflicts(matrix_path):
    data = json.load(open(matrix_path, encoding="utf-8"))
    rows = data.get("matrix", data if isinstance(data, list) else [])
    conflicts = []
    for f in ("main_result", "metrics"):
        by_pid = {r["paper_id"]: str(r["fields"].get(f, "")) for r in rows if r["fields"].get(f)}
        if len(by_pid) < 2:
            continue
        # naive direction check: contains 提高/高于 vs 降低/低于
        ups = {p for p, v in by_pid.items() if re.search(r"(?i)(提高|高于|提升|improve|higher|outperform)", v)}
        downs = {p for p, v in by_pid.items() if re.search(r"(?i)(降低|低于|下降|lower|decrease|worse)", v)}
        if ups and downs:
            # attribute: which canonical field differs
            diffs = []
            for pf in CANON_FIELDS:
                vals = {str(r["fields"].get(pf, ""))[:30] for r in rows if r["fields"].get(pf)}
                if len(vals) > 1:
                    diffs.append(pf)
            conflicts.append({"field": f, "papers_up": sorted(ups), "papers_down": sorted(downs),
                              "attribution_candidates": diffs or ["条件差异未知——需人工核查"],
                              "attribution_basis": "结论方向冲突归因到字段差异；每个差异值随口径记录"})
    print(json.dumps({"schema": "compare/conflicts@1", "n_conflicts": len(conflicts), "conflicts": conflicts,
                      "note": "差异来自样本/方法/条件还是评价指标——归因到具体字段"}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix")
    ap.add_argument("--comparable")
    ap.add_argument("--conflicts")
    a = ap.parse_args()
    if a.matrix:
        return cmd_matrix(a.matrix)
    if a.comparable:
        return cmd_comparable(a.comparable)
    if a.conflicts:
        return cmd_conflicts(a.conflicts)
    ap.error("choose --matrix / --comparable / --conflicts")

if __name__ == "__main__":
    sys.exit(main())
