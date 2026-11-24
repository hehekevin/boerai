"""Research-topic & novelty assessment bookkeeping.

三件事对应机制（题面质量条）：
  1. 研究问题拆成可检验表述 → problem decomposition：对象/变量/基线/
     预期结论/可证伪条件，五项缺一即"不可检验"
  2. 创新点与最近工作逐条划清边界 → novelty claims：每条创新陈述登记
     类型（method/data/scenario/revision），逐条给出 closest work 与
     boundary 判定（covered|distinct|unclear），附证据
  3. 可行性结论的每个前提有来源或标为假设 → feasibility premises：
     premise 必须 source_ref 或 assumption:true，引擎拒绝裸前提
"""
from __future__ import annotations

import json
import sys

from . import locate

NOVELTY_KINDS = {"method", "data", "scenario", "revision"}
BOUNDARIES = {"covered", "distinct", "unclear"}

PROBLEM_PARTS = ["object", "variables", "baseline", "expected_outcome", "falsifiable_condition"]


def validate_problem(problem: dict) -> dict:
    missing = [p for p in PROBLEM_PARTS if not (problem.get(p) or "").strip()]
    return {"testable": not missing, "missing_parts": missing,
            "problem": {p: problem.get(p, "") for p in PROBLEM_PARTS},
            "rule": "对象/关键变量/比较基线/预期结论/可证伪条件，五项缺一即不可检验"}


def validate_novelty_claims(claims: list[dict], blocks: list[dict]) -> dict:
    problems, out = [], []
    for c in claims:
        cid = c.get("claim_id", "?")
        cp = []
        if str(c.get("kind", "")) not in NOVELTY_KINDS:
            cp.append(f"invalid novelty kind (method|data|scenario|revision)")
        b = str(c.get("boundary", ""))
        if b not in BOUNDARIES:
            cp.append("boundary must be covered|distinct|unclear")
        if not (c.get("closest_work") or "").strip():
            cp.append("no closest_work identified (创新点必须与最近工作划界)")
        ev = c.get("evidence") or []
        if b == "distinct" and not ev:
            cp.append("boundary=distinct without evidence of the claimed delta")
        for e in ev:
            r = locate.verify_quote(blocks, str(e.get("loc", "")), e.get("quote", ""))
            if not r["verified"]:
                cp.append(f"evidence unverified: {r['reason']}")
        out.append({"claim_id": cid, "ok": not cp, "problems": cp})
        problems += [f"{cid}: {p}" for p in cp]
    counts = {}
    for c in claims:
        counts[c.get("boundary")] = counts.get(c.get("boundary"), 0) + 1
    return {"per_claim": out, "boundary_counts": counts, "problems": problems,
            "ok": not problems,
            "rule": "每条创新陈述逐条与最近工作划界；distinct 须给差异证据；"
                    "covered 即被已有工作覆盖，不得仍称创新"}


def validate_feasibility(premises: list[dict]) -> dict:
    problems, out = [], []
    for p in premises:
        pid = p.get("premise_id", "?")
        pp = []
        has_source = bool((p.get("source_ref") or "").strip())
        is_assumption = bool(p.get("assumption"))
        if not has_source and not is_assumption:
            pp.append("premise has neither source_ref nor assumption:true (裸前提)")
        if is_assumption and not (p.get("risk") or "").strip():
            pp.append("assumption without risk note (假设须带失败风险)")
        out.append({"premise_id": pid, "kind": "assumption" if is_assumption else "sourced",
                    "ok": not pp, "problems": pp})
        problems += [f"{pid}: {p}" for p in pp]
    n_src = sum(1 for o in out if o["kind"] == "sourced")
    return {"per_premise": out, "sourced": n_src, "assumptions": len(out) - n_src,
            "problems": problems, "ok": not problems,
            "rule": "每个前提要么有来源要么显式标为假设并附风险；结论只能是有条件的可行"}


def _demo() -> int:
    blocks = [{"loc": "S3", "source": "W1",
               "text": "Li et al. applied graph networks to perovskite band-gap prediction, "
                       "achieving MAE 0.21 eV on 5k samples."}]
    prob = {"object": "钙钛矿带隙预测", "variables": "成分特征→带隙",
            "baseline": "Li et al. GNN (MAE 0.21 eV)",
            "expected_outcome": "MAE < 0.15 eV",
            "falsifiable_condition": "同一公开数据集上 MAE 未低于基线即证伪"}
    vp = validate_problem(prob)
    assert vp["testable"]
    assert not validate_problem({"object": "x"})["testable"]
    nc = [{"claim_id": "N1", "kind": "data",
           "text": "首次在 10 万级样本上训练",
           "closest_work": "Li et al. GNN, 5k samples",
           "boundary": "distinct",
           "evidence": [{"source": "W1", "loc": "S3",
                         "quote": "achieving MAE 0.21 eV on 5k samples"}]}]
    vn = validate_novelty_claims(nc, blocks)
    assert vn["ok"], vn
    fb = [{"premise_id": "F1", "text": "公开数据集可获取", "source_ref": "材料 dataset.csv"},
          {"premise_id": "F2", "text": "GPU 显存足够训练 10 万样本", "assumption": True,
           "risk": "显存不足时需改 batch 或蒸馏，时间成本翻倍"},
          {"premise_id": "F3", "text": "团队有 GNN 经验"}]  # 裸前提
    vf = validate_feasibility(fb)
    assert not vf["ok"] and len(vf["problems"]) == 1
    vf_ok = validate_feasibility(fb[:2])
    assert vf_ok["ok"] and vf_ok["assumptions"] == 1
    print(json.dumps({"demo": "novelty", "problem_testable": vp["testable"],
                      "novelty_ok": vn["ok"],
                      "bare_premise_caught": not vf["ok"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "problem":
        rep = validate_problem(json.load(open(sys.argv[2], encoding="utf-8")))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    elif cmd == "novelty":
        claims = json.load(open(sys.argv[2], encoding="utf-8"))
        blocks = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = validate_novelty_claims(claims.get("claims", claims), blocks.get("blocks", blocks))
        out = sys.argv[4] if len(sys.argv) > 4 else None
    elif cmd == "feasibility":
        prem = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = validate_feasibility(prem.get("premises", prem))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        print("usage: novelty.py [problem|novelty|feasibility] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"-> {out}")
    print(f"ok={rep.get('ok', True)}")
    sys.exit(0 if rep.get("ok", True) else 1)
