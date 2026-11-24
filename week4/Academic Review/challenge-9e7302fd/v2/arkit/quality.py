"""Literature quality-appraisal scale: dimension - judgment - evidence - grade.

For single-paper research-quality evaluation. Each dimension judgment must
carry evidence (quote+locator) or be marked 'insufficient_evidence' (弃权) —
filling in a plausible judgment without evidence is exactly the failure mode
this module refuses. Grades aggregate from dimension levels via explicit,
inspectable thresholds, never a bare label.

Levels per dimension: low_risk | some_concerns | high_risk | insufficient_evidence
Overall grade: derived by AGGREGATION_RULE (see below), with a human-readable
derivation line so a second reviewer can recompute it.
"""
from __future__ import annotations

import json
import sys

from . import locate

DIMENSIONS = ("design", "sample", "measurement", "statistics", "reporting")
LEVELS = ("low_risk", "some_concerns", "high_risk", "insufficient_evidence")

DEFAULT_DIMENSIONS = [
    ("design", "研究设计是否支撑其结论(设计类型与研究问题匹配、对照与偏倚控制)"),
    ("sample", "样本与抽样是否交代清楚(来源、纳入排除、样本量依据)"),
    ("measurement", "测量与结局定义是否一致、有效(指标、工具、时间点)"),
    ("statistics", "统计分析是否匹配数据结构与分布假设、报告是否完整"),
    ("reporting", "报告完整性(关键章节、数字一致性、利益冲突与伦理声明)"),
]

AGGREGATION_RULE = ("high if any dimension=high_risk (a known high risk outranks unknowns); "
                    "elif >= half of dimensions are insufficient_evidence, overall=undetermined "
                    "(evidence insufficient, NOT a defect verdict); "
                    "low if all dimensions=low_risk; otherwise moderate")


def new_scale(paper_id: str = "", paper_type: str = "") -> dict:
    return {"paper_id": paper_id, "paper_type": paper_type,
            "dimensions": [{"id": d, "question": q, "level": "insufficient_evidence",
                            "assessed": False, "evidence": [], "rationale": ""}
                           for d, q in DEFAULT_DIMENSIONS],
            "overall": None, "derivation": "",
            "rule": AGGREGATION_RULE}


def judge(scale: dict, dim_id: str, level: str, *, evidence: list, rationale: str) -> dict:
    """Set a dimension level. Evidence items: {quote, locator}. Empty evidence
    forces level='insufficient_evidence' (honest abstention), regardless of
    the requested level."""
    assert level in LEVELS, level
    for d in scale["dimensions"]:
        if d["id"] == dim_id:
            ok_ev = [e for e in evidence
                     if locate.norm_text(e.get("quote", "")) and
                     locate.parse_locator(e.get("locator", ""))]
            if not ok_ev:
                d["level"] = "insufficient_evidence"
                d["assessed"] = False
                d["rationale"] = rationale or "no verifiable evidence supplied -> abstain"
                d["evidence"] = []
            else:
                d["level"] = level
                d["assessed"] = True
                d["evidence"] = ok_ev
                d["rationale"] = rationale
            return d
    raise KeyError(dim_id)


def grade(scale: dict) -> dict:
    ds = scale["dimensions"]
    lv = {d["id"]: d["level"] for d in ds}
    n = len(ds)
    n_ins = sum(1 for d in ds if d["level"] == "insufficient_evidence")
    if any(d["level"] == "high_risk" for d in ds):
        overall = "high"
    elif n_ins * 2 >= n:
        overall = "undetermined"
    elif all(d["level"] == "low_risk" for d in ds):
        overall = "low"
    else:
        overall = "moderate"
    scale["overall"] = overall
    scale["derivation"] = (f"levels={lv}; n_insufficient={n_ins}/{n}; "
                           f"rule -> {overall}")
    return {"overall": overall, "derivation": scale["derivation"], "rule": AGGREGATION_RULE,
            "abstained": [d["id"] for d in ds if not d["assessed"]]}


def _demo() -> int:
    sc = new_scale("P1", "RCT")
    judge(sc, "design", "low_risk",
          evidence=[{"quote": "Patients were randomly assigned (1:1) to groups.",
                     "locator": "§Methods ¶1 s2"}],
          rationale="randomized with allocation described")
    judge(sc, "statistics", "high_risk",
          evidence=[{"quote": "We compared 12 secondary outcomes (p < 0.05).",
                     "locator": "§Results ¶2 s1"}],
          rationale="multiple comparisons without correction stated")
    # request a level without evidence -> forced abstention, NOT the requested level
    d = judge(sc, "sample", "low_risk", evidence=[], rationale="looks fine")
    assert d["level"] == "insufficient_evidence" and not d["assessed"]
    g = grade(sc)
    assert g["overall"] == "high" and "statistics" in sc["derivation"], g
    # honest undetermined: mostly insufficient evidence
    sc2 = new_scale("P2", "abstract-only")
    g2 = grade(sc2)
    assert g2["overall"] == "undetermined" and len(g2["abstained"]) == 5
    print(json.dumps({"demo": "quality.grade", "overall": g["overall"],
                      "abstention_forced": d["level"] == "insufficient_evidence",
                      "undetermined_case": g2["overall"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.quality <scale.json> [out.json]  (compute grade)
    sc = json.load(open(sys.argv[1], encoding="utf-8"))
    g = grade(sc)
    out = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    json.dump(sc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(g, ensure_ascii=False, indent=1))
