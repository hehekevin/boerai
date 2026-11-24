#!/usr/bin/env python3
"""qa-engine: literature QA with evidence anchor (paragraph-numbered papers).

Deterministic subcommands (0 model requests):
  --index DOC_JSON           build paragraph index from numbered-paragraph paper
  --retrieve DOC_JSON Q      retrieve top-k relevant paragraphs (keyword scoring, evidence anchors)
  --scaffold DOC_JSON Q      answer scaffold: candidate evidence + sub-question checklist
  --uncertainty ANSWER_JSON  uncertainty audit: unreported/partial/conflict markers
Stdlib only. Paper format: {"paper_id":..., "paragraphs":[{"no":1,"text":...,"section":...}]}
"""
import argparse
import json
import re
import sys
import unicodedata

STOP = set("the a an of in on for to and or is are was were be been with by from as at that this these those it its their our we they 论文 本文 研究 的 了 在 是 与 和 对".split())


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()


# cross-language expansion: zh question terms -> en paper terms (科研常见对照)
ZH_EN_MAP = {
    "准确率": ["accuracy", "accurate"], "精确": ["precision"], "召回": ["recall"],
    "模型": ["model", "models"], "方法": ["method", "approach"], "结果": ["result", "results"],
    "样本": ["sample", "samples"], "数据集": ["dataset", "data"], "训练": ["train", "training", "trained"],
    "基线": ["baseline"], "提升": ["improve", "improvement", "outperform"],
    "结论": ["conclusion"], "讨论": ["discussion"], "实验": ["experiment"],
    "条件": ["condition", "setting"], "对比": ["comparison", "compared", "compared"],
    "未报告": ["not reported", "not available"], "误差": ["error", "uncertainty"],
    "单位": ["unit"], "显著性": ["significant", "significance"],
}


def expand_tokens(tokens, raw_text=""):
    """Expand zh terms (matched against RAW text) with en equivalents; return token set."""
    out = set(tokens)
    joined = raw_text or " ".join(tokens)
    for zh, ens in ZH_EN_MAP.items():
        if zh in joined:
            for e in ens:
                out.add(e)
                out.update(e.split())
    return out


def tokenize(q):
    """CJK bigrams + latin words, minus stopwords."""
    q = norm(q)
    latin = [w for w in re.findall(r"[a-z][\w-]{2,}", q) if w not in STOP]
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{2,}", q)
    bigrams = set()
    for run in cjk_runs:
        for i in range(len(run) - 1):
            bigrams.add(run[i:i + 2])
    return latin + list(bigrams)


def load_paper(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else d.get("paper", d)


def cmd_index(path):
    p = load_paper(path)
    paras = p.get("paragraphs", p.get("paragraphs", []))
    idx = {"schema": "qa/index@1", "paper_id": p.get("paper_id", ""), "n_paragraphs": len(paras),
           "sections": {}, "index": []}
    for para in paras:
        toks = tokenize(para.get("text", ""))
        idx["index"].append({"no": para.get("no"), "section": para.get("section", ""), "tokens": toks[:40],
                             "n_chars": len(para.get("text", ""))})
        sec = para.get("section", "unknown")
        idx["sections"][sec] = idx["sections"].get(sec, 0) + 1
    print(json.dumps(idx, ensure_ascii=False, indent=1))
    return 0


def cmd_retrieve(path, question, topk=5):
    p = load_paper(path)
    paras = p.get("paragraphs", [])
    qtoks = expand_tokens(set(tokenize(question)), question)
    scored = []
    for para in paras:
        toks = set(tokenize(para.get("text", "")))
        overlap = len(qtoks & toks)
        bonus = 0.15 * (1 if norm(para.get("section", "")).find("result") >= 0 or "结果" in para.get("section", "") else 0)
        score = overlap + bonus
        if overlap > 0:
            # evidence: short quote containing a hit term
            text = para.get("text", "")
            anchor = ""
            for t in list(qtoks)[:8]:
                m = re.search(re.escape(t), text, re.I)
                if m:
                    anchor = text[max(0, m.start() - 20):m.end() + 30]
                    break
            scored.append({"no": para.get("no"), "section": para.get("section", ""), "score": score,
                           "excerpt": anchor, "n_chars": len(text)})
    scored.sort(key=lambda x: -x["score"])
    print(json.dumps({"schema": "qa/retrieve@1", "question": question, "topk": scored[:topk],
                      "note": "证据锚点=段落编号+短引文；覆盖不足时升级检索（同义词扩展）"}, ensure_ascii=False, indent=1))
    return 0


def cmd_scaffold(path, question):
    p = load_paper(path)
    paras = p.get("paragraphs", [])
    qtoks = expand_tokens(set(tokenize(question)), question)
    # sub-question detection: split on ；/？/and/以及
    subqs = [s for s in re.split(r"[；;？?]|(?:以及|并且|同时)", question) if norm(s)]
    evidence = []
    for para in paras:
        toks = set(tokenize(para.get("text", "")))
        if len(qtoks & toks) >= max(1, len(qtoks) // 8):
            evidence.append({"no": para.get("no"), "section": para.get("section", ""),
                             "excerpt": para.get("text", "")[:120]})
    evidence.sort(key=lambda e: 0 if "result" in norm(e.get("section", "")) or "结果" in e.get("section", "") else 1)
    print(json.dumps({"schema": "qa/scaffold@1", "question": question,
                      "subquestions": [s[:80] for s in subqs[:6]],
                      "must_cover": ["每个子问独立作答", "每条论断附段落编号+短引文", "数值带单位/条件/比较对象",
                                      "区分实测/作者解释/推断"],
                      "candidate_evidence": evidence[:8],
                      "sections_to_integrate": sorted({e["section"] for e in evidence})}, ensure_ascii=False, indent=1))
    return 0


UNCERT_PATTERNS = [
    ("unreported", re.compile(r"(?i)not reported|未报告|无法确定|not available|N/A|未提供"), "材料未报告——如实说明无法确定"),
    ("partial", re.compile(r"(?i)部分回答|only partially|仅部分|缺口"), "只能部分回答——列出缺口"),
    ("conflict", re.compile(r"(?i)conflict|冲突|inconsistent|不一致|矛盾"), "原文冲突——指出冲突及出处"),
    ("infer", re.compile(r"(?i)推断|推测|infer|speculate"), "推断性内容——标记为推断，与实测区分"),
]


def cmd_uncertainty(answer_path):
    ans = json.load(open(answer_path, encoding="utf-8"))
    if isinstance(ans, dict):
        ans = ans.get("answers", [ans])
    audit = []
    for a in ans:
        text = norm(str(a.get("answer", a.get("text", ""))))
        flags = []
        for label, pat, note in UNCERT_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append({"flag": label, "evidence": m.group(0)[:60], "handling": note})
        # missing evidence check: claims without paragraph anchor
        if "para" not in text and "段落" not in text and "no" not in text:
            flags.append({"flag": "missing_anchor", "evidence": "答案未引用段落编号", "handling": "补锚点或标记为推断"})
        audit.append({"qid": a.get("qid", a.get("question", ""))[:40], "flags": flags,
                      "ok": len(flags) == 0})
    print(json.dumps({"schema": "qa/uncertainty@1", "n_answers": len(audit),
                      "n_clean": sum(1 for x in audit if x['ok']), "audit": audit[:30]},
                     ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index")
    ap.add_argument("--retrieve", nargs=2, metavar=("DOC", "QUESTION"))
    ap.add_argument("--scaffold", nargs=2, metavar=("DOC", "QUESTION"))
    ap.add_argument("--uncertainty")
    a = ap.parse_args()
    if a.index:
        return cmd_index(a.index)
    if a.retrieve:
        return cmd_retrieve(a.retrieve[0], a.retrieve[1])
    if a.scaffold:
        return cmd_scaffold(a.scaffold[0], a.scaffold[1])
    if a.uncertainty:
        return cmd_uncertainty(a.uncertainty)
    ap.error("choose --index / --retrieve / --scaffold / --uncertainty")


if __name__ == "__main__":
    sys.exit(main())
