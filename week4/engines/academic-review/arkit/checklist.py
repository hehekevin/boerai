"""Facet checklists: what must be checked, with what evidence, and coverage.

A checklist is a list of items grouped by the six review facets
(fact/citation/method/stats/logic/norm). Each item declares:
  id, facet, question, rule (how to judge), required_evidence (what must be
  attached), and after the run: status in
  pass | issue | needs_review(待复核) | not_applicable | unchecked.
Coverage is computed only over checked items; unchecked items are reported
explicitly — a report may never imply full coverage when items were skipped.
"""
from __future__ import annotations

import json
import sys

FACETS = ("fact", "citation", "method", "stats", "logic", "norm")
ITEM_STATUS = ("pass", "issue", "needs_review", "not_applicable", "unchecked")

# Default six-facet checklist shared by the academic-review challenges.
DEFAULT_ITEMS = [
    ("fact-numbers", "fact", "正文/摘要/图表中的数字是否前后一致",
     "extract numeric claims and compare across sections",
     "两处以上原文数字摘录+定位"),
    ("fact-terms", "fact", "术语与定义是否前后统一",
     "compare term usage; flag redefinitions", "术语出现位置摘录"),
    ("cit-support", "citation", "引用是否支持所在句的论断",
     "compare in-text claim with cited-source snippet (crosscheck)",
     "本文论断+被引片段并列"),
    ("cit-metadata", "citation", "参考文献条目是否完整、正文引用是否有对应条目",
     "match [n] or (Author, year) keys against reference list",
     "引用键与条目对照"),
    ("meth-design", "method", "研究设计是否回答研究问题、对照/分组是否合理",
     "design-vs-question match; control presence", "方法段摘录+判定依据"),
    ("meth-report", "method", "方法报告是否完整(抽样/盲法/缺失值处理)",
     "presence of sampling/blinding/missing-data statements",
     "存在或缺失的原文位置"),
    ("stat-methods", "stats", "统计方法与数据结构/分布假设是否匹配",
     "test-vs-data-type plausibility, multiple-comparison handling",
     "统计方法句摘录"),
    ("stat-report", "stats", "是否报告效应量、CI、精确 p、n",
     "stats.detect observations: presence of n/CI/p near numeric claims",
     "数值主张+伴随量观察记录"),
    ("logic-chain", "logic", "前提→结论推理是否有跳跃、因果与相关是否混用",
     "claims.extract: causal vs correlational markers per claim",
     "主张句+证据句定位"),
    ("logic-scope", "logic", "结论强度是否超出数据可支撑范围",
     "compare claim strength vs evidence type", "结论句+数据句并列"),
    ("norm-ethics", "norm", "伦理/知情同意/利益冲突/数据可用性声明是否齐备",
     "norms.scan presence detectors", "声明句摘录或缺失说明"),
    ("norm-format", "norm", "图表来源、引用格式、署名与基金信息是否一致",
     "presence/consistency of declarations", "相关声明位置"),
]

ITEM_STATUS_LABELS = {"pass": "通过", "issue": "问题", "needs_review": "待复核",
                      "not_applicable": "不适用", "unchecked": "未检查"}


def default_checklist() -> dict:
    return {"name": "six-facet-default",
            "items": [{"id": i, "facet": f, "question": q, "rule": r,
                       "required_evidence": ev, "status": "unchecked",
                       "evidence": [], "finding_ids": [], "note": ""}
                      for i, f, q, r, ev in DEFAULT_ITEMS]}


def load(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def save(cl: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cl, fh, ensure_ascii=False, indent=1)


def set_status(cl: dict, item_id: str, status: str, *, evidence: list | None = None,
               finding_ids: list | None = None, note: str = "") -> dict:
    assert status in ITEM_STATUS, status
    for it in cl["items"]:
        if it["id"] == item_id:
            it["status"] = status
            if evidence is not None:
                it["evidence"] = evidence
            if finding_ids is not None:
                it["finding_ids"] = finding_ids
            it["note"] = note
            return it
    raise KeyError(item_id)


def coverage(cl: dict) -> dict:
    """Per-facet and overall coverage; issue items need finding_ids or evidence."""
    probs = []
    for it in cl["items"]:
        if it["status"] not in ITEM_STATUS:
            probs.append(f"{it['id']}: bad status")
        if it["status"] == "issue" and not it["finding_ids"] and not it["evidence"]:
            probs.append(f"{it['id']}: marked issue without evidence/finding link")
    per_facet = {}
    for f in FACETS:
        items = [i for i in cl["items"] if i["facet"] == f]
        per_facet[f] = {s: sum(1 for i in items if i["status"] == s) for s in ITEM_STATUS}
    n = len(cl["items"])
    checked = sum(1 for i in cl["items"] if i["status"] != "unchecked")
    return {"n_items": n, "checked": checked, "unchecked": n - checked,
            "coverage": round(checked / n, 4) if n else None,
            "per_facet": per_facet, "problems": probs,
            "labels": ITEM_STATUS_LABELS,
            "note": "unchecked items are reported, never hidden"}


def _demo() -> int:
    cl = default_checklist()
    assert len(cl["items"]) == 12
    set_status(cl, "stat-report", "issue",
               evidence=[{"quote": "Recall improved by 18.5% (p = 0.032).",
                          "locator": "§Results ¶2 s1"}], finding_ids=["F001"])
    set_status(cl, "fact-numbers", "pass", evidence=[])
    set_status(cl, "cit-support", "needs_review", note="cited full text unavailable offline")
    cov = coverage(cl)
    assert cov["checked"] == 3 and cov["unchecked"] == 9
    assert not cov["problems"], cov["problems"]
    bad = default_checklist()
    set_status(bad, "logic-chain", "issue")  # no evidence -> problem
    assert coverage(bad)["problems"], "issue without evidence must be flagged"
    print(json.dumps({"demo": "checklist.coverage", "items": cov["n_items"],
                      "checked": cov["checked"], "problems_flagged": bool(coverage(bad)["problems"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.checklist <init|coverage> [path]
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        out = sys.argv[2] if len(sys.argv) > 2 else "checklist.json"
        save(default_checklist(), out)
        print(f"default checklist -> {out}")
    elif len(sys.argv) > 2 and sys.argv[1] == "coverage":
        print(json.dumps(coverage(load(sys.argv[2])), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
