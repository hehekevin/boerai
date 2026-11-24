#!/usr/bin/env python3
"""review-engine: paper review toolkit — claims/refs/structure/stats/methods/compliance/bias.

Deterministic subcommands (0 model requests):
  --claims DOC_JSON         claim extraction w/ qualifiers (author-claim vs cited vs hypothesis)
  --support DOC_JSON        claim-evidence sufficiency: 结论超出数据 / 引用不对应 detection
  --structure DOC_JSON      completeness: sections/hierarchy/abstract-body correspondence/answers-intro
  --stats DOC_JSON          statistical reporting audit: controls/sample/randomization/CI/significance
  --variables DOC_JSON      variable definitions consistency: exposure/outcome/covariate coding/cutpoints
  --methods DOC_JSON        test-vs-data match: distribution/independence/multiplicity/repeated measures
  --integrity DOC_JSON      integrity: image reuse/duplicate pub/authorship/COI/funding consistency
  --cites DOC_JSON REFS_JSON   citation conformance: real-exists/metadata-match/one-to-one w/ claims
  --datacompliance DOC_JSON identifiable-info/restricted-data/ethics basis + de-identification advice
  --bias DOC_JSON TYPE      bias domains per study-type: 明确存在/可能存在/未见迹象/证据不足
Stdlib only.
"""
import argparse, json, re, sys

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else {"paragraphs": d}

CLAIM_PATS = [
    ("author_claim", re.compile(r"(?i)(we show|we demonstrate|our results|we find|本文(表明|证明|发现)|结果表明)")),
    ("cited_claim", re.compile(r"(?i)(previous(ly)? (shown|reported)|\[\d+\]|如\[\d+\]所(示|述)|已有研究)")),
    ("hypothesis", re.compile(r"(?i)(hypothes|we assume|假设|推测|may |might )")),
]
QUALIFIER = re.compile(r"(?i)(only|部分|在.*条件下|under .* conditions|limited|除外|except)")

def cmd_claims(path):
    p = load(path)
    out = []
    for para in p.get("paragraphs", []):
        text = norm(para.get("text", ""))
        for sent in re.split(r"(?<=[.。])\s+", text):
            for label, pat in CLAIM_PATS:
                m = pat.search(sent)
                if m and len(sent) > 25:
                    out.append({"type": label, "para_no": para.get("no"), "sentence": sent[:180],
                                "qualifiers": [q.group(0) for q in [QUALIFIER.search(sent)] if q],
                                "claim_id": f"C{len(out)+1}",
                                "note": "区分作者主张/引用观点/假设情形——逐条可核查"})
                    break
    print(json.dumps({"schema": "review/claims@1", "n_claims": len(out), "claims": out[:40]}, ensure_ascii=False, indent=1))
    return 0

SUFFICIENT = re.compile(r"(?i)(we show|demonstrate|p\s*[<=]\s*0?\.\d+|significan|表明|证实)")
HEDGED = re.compile(r"(?i)(may|might|suggest|可能|提示|有望)")

def cmd_support(path):
    p = load(path)
    items = p.get("claims", p.get("paragraphs", []))
    out = []
    for c in (items if isinstance(items, list) else []):
        text = norm(c.get("sentence", c.get("text", "")))
        has_evidence = bool(SUFFICIENT.search(text)) or bool(c.get("evidence_para"))
        hedged = bool(HEDGED.search(text))
        if not has_evidence and not hedged:
            verdict = "结论超出数据（无支撑证据标记）"
        elif hedged:
            verdict = "强度匹配（提示性表述）"
        else:
            verdict = "有支撑标记——需核对证据来源（本文实验 vs 所引文献）"
        out.append({"claim_id": c.get("claim_id", ""), "text": text[:120], "verdict": verdict,
                    "cite_mismatch_risk": bool(re.search(r"\[\d+\]", text)) and not has_evidence})
    print(json.dumps({"schema": "review/support@1", "items": out[:40],
                      "note": "识别'结论超出数据'与'引用不对应'"}, ensure_ascii=False, indent=1))
    return 0

SECTIONS_REQ = ["abstract", "introduction", "methods", "results", "discussion", "references"]

def cmd_structure(path):
    p = load(path)
    paras = p.get("paragraphs", [])
    found = {norm(x.get("section", "")).lower() for x in paras}
    missing = [s for s in SECTIONS_REQ if not any(s[:5] in f for f in found)]
    # abstract-body correspondence: numbers in abstract vs body
    abs_nums = set(re.findall(r"\d+\.?\d*", norm(next((x.get("text") for x in paras if "abstract" in norm(x.get("section","")).lower()), ""))))
    body_text = " ".join(norm(x.get("text", "")) for x in paras if "abstract" not in norm(x.get("section", "")).lower())
    nums_not_in_body = [n for n in abs_nums if n not in body_text and float(n) > 1] if abs_nums else []
    print(json.dumps({"schema": "review/structure@1", "missing_sections": missing,
                      "abstract_numbers_absent_in_body": nums_not_in_body[:10],
                      "verdict": "结构关键部分缺位风险" if missing or nums_not_in_body else "PASS",
                      "note": "结构看着完整但关键部分缺位的识别"}, ensure_ascii=False, indent=1))
    return 0

STAT_ITEMS = [
    ("controls", re.compile(r"(?i)(control|对照|sham|vehicle)")),
    ("sample_size", re.compile(r"(?i)(n\s*=|样本量|sample size)")),
    ("randomization", re.compile(r"(?i)(random|随机)")),
    ("blind", re.compile(r"(?i)(blind|盲法)")),
    ("significance", re.compile(r"(?i)(p\s*[<=]|significan|显著)")),
    ("ci", re.compile(r"(?i)(confidence interval|95%|置信区间|CI)")),
    ("error_bars", re.compile(r"(?i)(error bar|误差|SD|SEM|标准差)")),
    ("repeats", re.compile(r"(?i)(replicat|重复|biological replicate)")),
]

def cmd_stats(path):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    out = []
    for name, pat in STAT_ITEMS:
        m = pat.search(text)
        out.append({"item": name, "reported": bool(m), "evidence": m.group(0)[:40] if m else "未报告",
                    "verdict": "" if m else "报告缺位——区分'方法缺陷'与'报告缺陷'"})
    print(json.dumps({"schema": "review/stats@1", "items": out}, ensure_ascii=False, indent=1))
    return 0

VAR_CHECKS = [
    ("coding_consistency", re.compile(r"(?i)(编码|coding|category|分Levels?)")),
    ("cutpoint_basis", re.compile(r"(?i)(cut[- ]?off|切点|阈值|threshold)")),
    ("unit_conversion", re.compile(r"(?i)(单位|unit|换算)")),
    ("missing_handling", re.compile(r"(?i)(missing|缺失|imput|填补)")),
]

def cmd_variables(path):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    out = []
    for name, pat in VAR_CHECKS:
        m = pat.search(text)
        out.append({"item": name, "addressed": bool(m), "evidence": m.group(0)[:40] if m else "未见依据——切点/换算/缺失处理需有依据"})
    print(json.dumps({"schema": "review/variables@1", "items": out}, ensure_ascii=False, indent=1))
    return 0

METHOD_CHECKS = [
    ("test_data_match", re.compile(r"(?i)(t[- ]test|anova|chi|wilcoxon|mann|regression|检验)")),
    ("normality", re.compile(r"(?i)(normality|shapiro|正态)")),
    ("variance_homogeneity", re.compile(r"(?i)(levene|方差齐|homogeneity)")),
    ("independence", re.compile(r"(?i)(independen|独立)")),
    ("multiplicity", re.compile(r"(?i)(bonferroni|fdr|多重比较|correction)")),
    ("repeated_measures", re.compile(r"(?i)(repeated|重复测量|paired|配对)")),
    ("sensitivity", re.compile(r"(?i)(sensitivity|敏感性)")),
]

def cmd_methods(path):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    out = []
    for name, pat in METHOD_CHECKS:
        m = pat.search(text)
        out.append({"item": name, "addressed": bool(m), "evidence": m.group(0)[:40] if m else "未处理/未说明"})
    print(json.dumps({"schema": "review/methods@1", "items": out}, ensure_ascii=False, indent=1))
    return 0

INTEGRITY_CHECKS = [
    ("image_reuse", re.compile(r"(?i)(same image|图像复用|重复图像|western blot duplicat)")),
    ("duplicate_pub", re.compile(r"(?i)(duplicate publication|重复发表|一稿多投)")),
    ("authorship", re.compile(r"(?i)(author contribution|作者贡献|署名)")),
    ("coi", re.compile(r"(?i)(conflict of interest|利益冲突)")),
    ("funding", re.compile(r"(?i)(funding|基金|致谢|acknowledg)")),
]

def cmd_integrity(path):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    out = []
    for name, pat in INTEGRITY_CHECKS:
        m = pat.search(text)
        out.append({"item": name, "present": bool(m), "evidence": m.group(0)[:40] if m else "未见声明/提示——给出判断依据而非仅提示"})
    print(json.dumps({"schema": "review/integrity@1", "items": out}, ensure_ascii=False, indent=1))
    return 0

def cmd_cites(doc_path, refs_path):
    doc = json.load(open(doc_path, encoding="utf-8"))
    refs = json.load(open(refs_path, encoding="utf-8"))
    ref_list = refs.get("references", refs.get("refs", refs if isinstance(refs, list) else []))
    ref_keys = set()
    for r in ref_list:
        ref_keys.add(str(r.get("id", r.get("no", ""))))
    text = json.dumps(doc, ensure_ascii=False)
    cited = set(re.findall(r"\[(\d+)\]", text))
    uncited = sorted(ref_keys - cited, key=lambda x: (len(x), x))
    missing = sorted(cited - ref_keys, key=lambda x: (len(x), x))
    print(json.dumps({"schema": "review/cites@1", "n_cited": len(cited), "n_refs": len(ref_keys),
                      "cited_but_no_ref": missing[:15], "ref_but_uncited": uncited[:15],
                      "note": "引而不证/张冠李戴需模型逐条核对论断-文献对应"}, ensure_ascii=False, indent=1))
    return 0

COMPLIANCE_CHECKS = [
    ("pii", re.compile(r"(?i)(姓名|身份证|patient name|identifiable|可识别个人)")),
    ("restricted_data", re.compile(r"(?i)(restricted|受限数据|未公开|internal only)")),
    ("ethics", re.compile(r"(?i)(ethics|伦理|IRB|审批|informed consent|知情同意)")),
]

def cmd_datacompliance(path):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    out = []
    for name, pat in COMPLIANCE_CHECKS:
        m = pat.search(text)
        out.append({"item": name, "found": bool(m), "evidence": m.group(0)[:40] if m else "未见相关内容",
                    "advice": {"pii": "脱敏/匿名化改写建议", "restricted_data": "补充授权依据或移除",
                                "ethics": "补充审批号；无依据→提出合规改写"}.get(name, "")})
    print(json.dumps({"schema": "review/compliance@1", "items": out}, ensure_ascii=False, indent=1))
    return 0

BIAS_DOMAINS = {
    "rct": ["selection", "allocation", "blinding", "attrition", "reporting"],
    "cohort": ["selection", "confounding", "exposure_measurement", "attrition", "reporting"],
    "case_control": ["selection", "recall", "confounding", "measurement", "reporting"],
    "review": ["search_comprehensiveness", "screening_reproducibility", "quality_assessment", "synthesis"],
}

def cmd_bias(path, stype):
    p = load(path)
    text = json.dumps(p, ensure_ascii=False)
    domains = BIAS_DOMAINS.get(stype.lower(), BIAS_DOMAINS["cohort"])
    out = []
    for d in domains:
        m = re.search(re.escape(d).replace("\\ ", " "), text, re.I) or re.search(d.split("_")[0], text, re.I)
        if m:
            level = "未见迹象（文中已有对应控制描述）"
        else:
            level = "证据不足（文中未提及该领域——不能判'不存在'）"
        out.append({"domain": d, "level": level,
                    "allowed_levels": ["明确存在", "可能存在", "未见迹象", "证据不足"]})
    print(json.dumps({"schema": "review/bias@1", "study_type": stype, "domains": out}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims"); ap.add_argument("--support"); ap.add_argument("--structure")
    ap.add_argument("--stats"); ap.add_argument("--variables"); ap.add_argument("--methods")
    ap.add_argument("--integrity"); ap.add_argument("--cites", nargs=2); ap.add_argument("--datacompliance")
    ap.add_argument("--bias", nargs=2)
    a = ap.parse_args()
    if a.claims: return cmd_claims(a.claims)
    if a.support: return cmd_support(a.support)
    if a.structure: return cmd_structure(a.structure)
    if a.stats: return cmd_stats(a.stats)
    if a.variables: return cmd_variables(a.variables)
    if a.methods: return cmd_methods(a.methods)
    if a.integrity: return cmd_integrity(a.integrity)
    if a.cites: return cmd_cites(a.cites[0], a.cites[1])
    if a.datacompliance: return cmd_datacompliance(a.datacompliance)
    if a.bias: return cmd_bias(a.bias[0], a.bias[1])
    ap.error("choose a subcommand")

if __name__ == "__main__":
    sys.exit(main())
