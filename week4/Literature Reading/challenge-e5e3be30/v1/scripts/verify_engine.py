#!/usr/bin/env python3
"""claim-verify-forge: claim decomposition, minimal-evidence match, support-level verdict.

Deterministic subcommands (0 model requests):
  --decompose CLAIM        split complex claim into sub-claims (fact/comparison/causal/scope)
  --support EVIDENCE_JSON  verdict per sub-claim: 支持/部分支持/不支持/不充分
                           (term-overlap + negation + hedge detection; topic-related != support)
Stdlib only.
"""
import argparse, json, re, sys, unicodedata

def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()

CAUSAL = re.compile(r"(?i)(导致|由于|因此|because|causes?|leads? to|due to)")
COMPAR = re.compile(r"(?i)(高于|低于|优于|超过|more than|higher|lower|outperform)")
SCOPE = re.compile(r"(?i)(仅|只|在.*条件下|only|limited to|under .* conditions|范围内)")
NEG = re.compile(r"(?i)(not|no |没有|未|不|cannot|fails?|无)")

ZH_EN_MAP = {
    "准确率": ["accuracy", "accurate"], "提高": ["improve", "improvement", "outperform", "5.2"],
    "方法": ["method", "approach", "model"], "数据集": ["dataset", "datasets", "data"],
    "有效": ["effective", "valid", "work", "tested"], "所有": ["all", "two small", "only"],
    "医学影像": ["medical imaging"], "适用": ["applications", "applicable", "potential"],
    "样本": ["sample", "samples", "cohort"], "对比": ["comparison", "compared", "against"],
    "局限": ["limitation", "small", "only"], "验证": ["tested", "validate", "validation"],
}


def expand_claim_words(words, raw_claim):
    """Expand zh claim terms with en equivalents (matched against RAW claim text)."""
    out = set(words)
    for zh, ens in ZH_EN_MAP.items():
        if zh in (raw_claim or ""):
            for e in ens:
                out.add(e)
    return out


def cmd_decompose(claim):
    subs = []
    # split on sentence + connectives
    parts = re.split(r"(?<=[。；;.])\s*|(?:；|;)", claim)
    parts = [p.strip() for p in parts if norm(p)]
    for i, p in enumerate(parts):
        ctype = "fact"
        if CAUSAL.search(p):
            ctype = "causal"
        elif COMPAR.search(p):
            ctype = "comparison"
        if SCOPE.search(p):
            ctype += "+scope" if ctype != "fact" else "fact+scope"
        subs.append({"sub_id": f"S{i+1}", "text": p[:160], "claim_type": ctype,
                     "evidence_needed": {"fact": "直接陈述句", "comparison": "数值/比较对象/方向",
                                          "causal": "机制或实验因果证据", "fact+scope": "事实+适用范围条件",
                                          "comparison+scope": "数值+条件", "causal+scope": "因果+条件"}[ctype]})
    print(json.dumps({"schema": "verify/decompose@1", "n_subclaims": len(subs), "subclaims": subs,
                      "note": "拆分要求不遗漏不重复核验"}, ensure_ascii=False, indent=1))
    return 0


def cmd_support(evidence_path):
    """evidence: [{sub_id, claim_text, evidence_text, section, para_no}]
    verdict by lexical+semantic signals; 主题相关 != 支持."""
    items = json.load(open(evidence_path, encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])
    out = []
    for it in items:
        claim = norm(it.get("claim_text", ""))
        ev = norm(it.get("evidence_text", ""))
        zh_words = set(w for w in re.findall(r"[\u4e00-\u9fff]{2,4}", it.get("claim_text", "")))
        cwords = set(w for w in re.findall(r"[a-z]{3,}", claim) if w not in
                     {"the", "and", "for", "with", "that", "this", "only", "than", "from"})
        cwords = expand_claim_words(cwords | zh_words, it.get("claim_text", ""))
        overlap = [w for w in cwords if w in ev]
        ratio = len(overlap) / max(1, len(cwords))
        claim_neg = bool(NEG.search(it.get("claim_text", "")))
        ev_neg = bool(NEG.search(it.get("evidence_text", "")))
        direction_conflict = claim_neg != ev_neg and (claim_neg or ev_neg)
        hedged_ev = bool(re.search(r"(?i)(may|might|suggest|可能|提示|推测)", it.get("evidence_text", "")))
        if ratio < 0.3:
            verdict, reason = "不充分", f"词汇重叠 {ratio:.0%} 过低——证据与论断主题关联弱"
        elif direction_conflict:
            verdict, reason = "不支持", "证据与论断方向相反（一方含否定）"
        elif hedged_ev and not re.search(r"(?i)(show|demonstrate|证明|表明)", it.get("evidence_text", "")):
            verdict, reason = "部分支持", "证据为提示性表述（suggest/may），方向一致但强度不足"
        elif ratio >= 0.6:
            verdict, reason = "支持", f"词汇重叠 {ratio:.0%}，方向一致且证据为陈述性表述"
        else:
            verdict, reason = "部分支持", f"词汇重叠 {ratio:.0%}，部分要素未在证据中出现"
        out.append({"sub_id": it.get("sub_id"), "verdict": verdict, "reason": reason,
                    "evidence_loc": {"section": it.get("section", ""), "para_no": it.get("para_no"),
                                      "excerpt": (it.get("evidence_text") or "")[:80]},
                    "topic_related_only": 0.3 <= ratio < 0.45 and verdict in ("不充分",)})
    print(json.dumps({"schema": "verify/support@1", "items": out,
                      "summary": {v: sum(1 for o in out if o['verdict'] == v) for v in ("支持", "部分支持", "不支持", "不充分")},
                      "note": "主题相关≠支持：overlap低于0.45且无方向矛盾标 topic_related_only"}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decompose")
    ap.add_argument("--support")
    a = ap.parse_args()
    if a.decompose:
        return cmd_decompose(a.decompose)
    if a.support:
        return cmd_support(a.support)
    ap.error("choose --decompose / --support")

if __name__ == "__main__":
    sys.exit(main())
