#!/usr/bin/env python3
"""extraction-engine: conclusions/conditions/values extraction with evidence anchors.

Deterministic subcommands (0 model requests):
  --conclusions DOC_JSON   extract conclusion sentences, classify 明确结论/限制/推测
  --conditions DOC_JSON    extract experimental conditions (sample/setting/baseline)
  --values DOC_JSON        extract numeric values with units/error/stat-sig + bound conditions
  --locate EXTRACT_JSON    verify each extraction has paragraph anchor (locatable by a second person)
Stdlib only. Doc format: {"paper_id":..., "paragraphs":[{"no":N,"section":S,"text":...}]}
"""
import argparse
import json
import re
import sys

CONCL_PATTERNS = [
    ("明确结论", re.compile(r"(?i)(we show|we demonstrate|in conclusion|our results (show|indicate)|achieved|outperform|we find)|本文(表明|发现|证实)|(结果表明|实验表明|我们证明)")),
    ("限制条件", re.compile(r"(?i)limitation|however|only|constraint|caution|caveat|局限|然而|仅|受限于|样本量(小|有限)")),
    ("推测表述", re.compile(r"(?i)(may|might|could|suggest|speculate|potential)|可能|或许|提示|有望|推测")),
]

COND_PATTERNS = [
    ("样本", re.compile(r"(?i)(n\s*=\s*\d+|\d+\s+(samples?|patients?|subjects?|images?))|(\d+\s*(个|名)?\s*(样本|患者|受试者|图片))")),
    ("实验设置", re.compile(r"(?i)(batch size|learning rate|epochs?|epochs|train(ed|ing) (on|with))|(学习率|批大小|训练轮数|训练于)")),
    ("数据来源", re.compile(r"(?i)(dataset|corpus|cohort|collected from)|(数据集|来自|采集于)")),
    ("比较基线", re.compile(r"(?i)(baseline|compared (to|with)|against)|(基线|相比|对照)")),
    ("时间点", re.compile(r"(20\d{2})|(\d+\s*(days?|weeks?|months?|years?))")),
]

VALUE_RE = re.compile(
    r"(?<![\w])(\d+\.?\d*)\s*(%|percent|mg|mL|kg|mm|cm|μm|nm|ms|s|min|h|hours?|days?|points?|×|-fold|dB|epochs?|GB|MB)?"
    r"(\s*[±±]\s*(\d+\.?\d*)\s*(%|percent|mg|mL|kg|mm|cm|μm|nm|ms|s|min|h|points?)?)?"
    r"(\s*\((p\s*[<=]\s*0?\.\d+[^)]*)\))?", re.I)

SIG_RE = re.compile(r"(?i)p\s*[<=]\s*0?\.\d+|significant|显著")


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else {"paper_id": "?", "paragraphs": d}


def cmd_conclusions(path):
    p = load(path)
    out = []
    for para in p.get("paragraphs", []):
        text = para.get("text", "")
        for sent in re.split(r"(?<=[.。])\s+", text):
            for label, pat in CONCL_PATTERNS:
                m = pat.search(sent)
                if m and len(sent) > 20:
                    out.append({"type": label, "para_no": para.get("no"), "section": para.get("section", ""),
                                "sentence": sent.strip()[:200], "trigger": m.group(0)[:40]})
                    break
    print(json.dumps({"schema": "extract/conclusions@1", "n_found": len(out), "items": out[:40],
                      "note": "推测表述（may/suggest/可能）不得改写为确定事实"}, ensure_ascii=False, indent=1))
    return 0


def cmd_conditions(path):
    p = load(path)
    out = []
    for para in p.get("paragraphs", []):
        text = para.get("text", "")
        for label, pat in COND_PATTERNS:
            for m in pat.finditer(text):
                out.append({"type": label, "para_no": para.get("no"), "section": para.get("section", ""),
                            "match": m.group(0)[:80], "context": text[max(0, m.start() - 30):m.end() + 30][:110]})
    print(json.dumps({"schema": "extract/conditions@1", "n_found": len(out), "items": out[:40],
                      "note": "每条数值必须带其成立条件，不脱离语境单独成行"}, ensure_ascii=False, indent=1))
    return 0


def cmd_values(path):
    p = load(path)
    out = []
    for para in p.get("paragraphs", []):
        text = para.get("text", "")
        for m in VALUE_RE.finditer(text):
            val, unit = m.group(1), m.group(2) or ""
            err = m.group(4) or ""
            err_unit = m.group(5) or ""
            sig = m.group(6) or ""
            if not unit and not err and not sig and float(val) < 10:
                continue  # likely plain number, skip to avoid noise
            has_sig = bool(SIG_RE.search(text[max(0, m.start() - 120):m.end() + 120]))
            out.append({"value": val, "unit": unit or "missing_unit", "error": (err + " " + err_unit).strip(),
                        "stat_sig": ("p-value/significant in context" if has_sig or sig else "not_in_context"),
                        "para_no": para.get("no"), "section": para.get("section", ""),
                        "context": text[max(0, m.start() - 40):m.end() + 40][:120],
                        "raw": m.group(0)[:80]})
    print(json.dumps({"schema": "extract/values@1", "n_found": len(out), "items": out[:40],
                      "note": "missing_unit 显式标记；范围值/未报告按原文记录"}, ensure_ascii=False, indent=1))
    return 0


def cmd_locate(extract_path):
    data = json.load(open(extract_path, encoding="utf-8"))
    problems = []
    checked = 0
    for kind in ("items", "records", "conclusions"):
        items = data.get(kind) or []
        for it in items:
            checked += 1
            if not it.get("para_no") and "para_no" not in it:
                problems.append({"kind": kind, "issue": "缺少段落锚点", "item": str(it)[:80]})
    print(json.dumps({"schema": "extract/locate@1", "n_checked": checked, "n_problems": len(problems),
                      "problems": problems[:20],
                      "note": "定位粒度=段落编号；第二人可按锚点独立抽查"}, ensure_ascii=False, indent=1))
    return 0 if not problems else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conclusions")
    ap.add_argument("--conditions")
    ap.add_argument("--values")
    ap.add_argument("--locate")
    a = ap.parse_args()
    if a.conclusions:
        return cmd_conclusions(a.conclusions)
    if a.conditions:
        return cmd_conditions(a.conditions)
    if a.values:
        return cmd_values(a.values)
    if a.locate:
        return cmd_locate(a.locate)
    ap.error("choose --conclusions / --conditions / --values / --locate")


if __name__ == "__main__":
    sys.exit(main())
