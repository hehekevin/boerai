#!/usr/bin/env python3
"""novelty-matrix-forge: research proposal novelty & feasibility assessment.

Deterministic subcommands (0 model requests):
  --decompose PROPOSAL      split vague idea into checkable statement (object/variable/baseline/falsifiable)
  --matrix PAPERS_JSON      prior-work comparison matrix (task/method/data/eval/conclusion)
  --novelty MATRIX_JSON CLAIMS_JSON   novelty verdict per claim: method/data/transfer/conclusion-correction
  --feasibility PROPOSAL_JSON         condition-checked feasibility with failure risks
Stdlib only.
"""
import argparse, json, re, sys, unicodedata

def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()

def cmd_decompose(proposal):
    p = unicodedata.normalize("NFKC", proposal or "").strip()
    m_year = re.search(r"(20\d{2})", p)
    compar = re.search(r"(?i)(相比|优于|超过|improve|outperform|vs)", p)
    falsifiable = bool(compar or re.search(r"(?i)(验证|检验|evaluat|test|证明)", p))
    out = {"schema": "novelty/decompose@1", "proposal": p[:300],
           "statement_elements": {
               "research_object": re.findall(r"(?i)(肿瘤|细胞|影像|文献|材料|图| protein|sample)", p)[:3] or ["待模型补充"],
               "key_variables": re.findall(r"(?i)(准确率|auc|loss|效率|性能|accuracy)", p)[:3] or ["待模型补充"],
               "comparison_baseline": "存在比较词→基线待明确" if compar else "N/A（无比较关系）",
               "expected_conclusion": compar.group(0) if compar else "待明确",
               "time_scope": m_year.group(1) if m_year else "N/A",
               "falsifiable_statement": "可证伪（有验证/比较表述）" if falsifiable else "不可证伪——缺验证途径，需模型补全"},
           "gaps_for_model": ["若上述任一要素'待补充'，模型需从题面上下文回填并标注 basis=model"],
           "note": "模糊设想→可检验问题陈述"}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0

def cmd_matrix(papers_path):
    papers = json.load(open(papers_path, encoding="utf-8"))
    if isinstance(papers, dict):
        papers = papers.get("papers", [])
    dims = ["task", "method", "data", "eval", "conclusion"]
    rows = []
    for p in papers:
        rows.append({"paper_id": p.get("paper_id", p.get("id", "")),
                     **{d: p.get(d, "missing") for d in dims},
                     "comparison_note": "标出无法直接比较的原因（数据/评价口径）" })
    print(json.dumps({"schema": "novelty/matrix@1", "n_papers": len(papers), "dims": dims, "matrix": rows},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_novelty(matrix_path, claims_path):
    matrix = json.load(open(matrix_path, encoding="utf-8"))
    papers = matrix.get("matrix", matrix if isinstance(matrix, list) else [])
    claims = json.load(open(claims_path, encoding="utf-8"))
    if isinstance(claims, dict):
        claims = claims.get("claims", [])
    verdicts = []
    for c in claims:
        claim = norm(c.get("claim", ""))
        covered = []
        for p in papers:
            overlap = sum(1 for w in re.findall(r"[a-z]{3,}", claim) if w in norm(str(p)))
            if overlap >= 2:
                covered.append({"paper_id": p.get("paper_id"), "overlap_terms": overlap,
                                "reason": f"已有工作覆盖该陈述（{overlap}个术语重合）"})
        ntype = "method" if re.search(r"(?i)(方法|架构|算法|model|method)", claim) else \
                "data" if re.search(r"(?i)(数据|dataset|corpus)", claim) else \
                "transfer" if re.search(r"(?i)(迁移|应用|应用到|apply)", claim) else "conclusion_correction"
        verdicts.append({"claim": c.get("claim", "")[:80], "novelty_type": ntype,
                         "covered_by": covered[:3],
                         "verdict": "已被覆盖" if covered else "未见覆盖（基于给定比较集）",
                         "uncertainty": "覆盖判定仅限给定论文集，不声明绝对新颖"})
    print(json.dumps({"schema": "novelty/verdict@1", "verdicts": verdicts,
                      "note": "区分方法创新/数据创新/场景迁移/结论修正"}, ensure_ascii=False, indent=1))
    return 0

def cmd_feasibility(proposal_path):
    prop = json.load(open(proposal_path, encoding="utf-8"))
    if isinstance(prop, dict):
        prop = prop.get("statement_elements", prop)
    checks = []
    for k, pat, label in [("data", re.compile(r"(?i)(数据|dataset|data)", re.I), "数据可得性"),
                          ("compute", re.compile(r"(?i)(gpu|算力|compute|卡)", re.I), "算力前提"),
                          ("time", re.compile(r"(20\d{2})", re.I), "时间窗口"),
                          ("personnel", re.compile(r"(?i)(人员|团队|能力)", re.I), "人员能力")]:
        found = bool(pat.search(json.dumps(prop, ensure_ascii=False)))
        checks.append({"condition": label, "stated_in_proposal": found,
                       "verdict": "有条件成立" if found else "未声明——列为前提假设（带条件结论）",
                       "failure_risk": None if found else f"{label}未确认时结论不可靠"})
    print(json.dumps({"schema": "novelty/feasibility@1", "checks": checks,
                      "conclusion_type": "带条件的可行性结论（每条结论列出成立条件与失败风险）"},
                     ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decompose")
    ap.add_argument("--matrix")
    ap.add_argument("--novelty", nargs=2)
    ap.add_argument("--feasibility")
    a = ap.parse_args()
    if a.decompose: return cmd_decompose(a.decompose)
    if a.matrix: return cmd_matrix(a.matrix)
    if a.novelty: return cmd_novelty(a.novelty[0], a.novelty[1])
    if a.feasibility: return cmd_feasibility(a.feasibility)
    ap.error("choose --decompose / --matrix / --novelty / --feasibility")

if __name__ == "__main__":
    sys.exit(main())
