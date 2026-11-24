"""Claim verification: 论断拆解 + 四级支持度核验。

输入（claims.json）：[{claim_id, text, subclaims: [{sub_id, text, kind,
  verdict: support|partial|contradict|not_found, evidence: [{source, loc, quote}],
  rationale}]}]

四级判定定义（写入交付物，供复核）：
  support      证据逐字支持子判断的全部要素（数值/方向/条件一致）
  partial      证据只覆盖部分要素，或条件范围比论断窄
  contradict   证据与论断方向相反或数值矛盾
  not_found    材料中没有可核验的证据（主题相关 ≠ 支持）

引擎职责：
  - verdict 合法性与强制字段（rationale 必填；非 not_found 必须有证据）
  - 证据逐字核验（locate.verify_quote）
  - 父论断状态由子判断聚合：全 support → supported；有 contradict → contradicted；
    有 not_found/partial → partially_verified / unverifiable
  - 冲突登记：conflicts[] 保留冲突双方原话
"""
from __future__ import annotations

import json
import sys

from . import locate

VERDICTS = {"support", "partial", "contradict", "not_found"}
VERDICT_DEFINITIONS = {
    "support": "证据逐字支持子判断的全部要素（数值、方向、条件一致）",
    "partial": "证据只覆盖部分要素，或证据条件范围比论断窄",
    "contradict": "证据与论断方向相反或数值矛盾",
    "not_found": "材料中没有可核验证据；主题相关不等于支持",
}


def aggregate(verdicts: list[str]) -> str:
    if not verdicts:
        return "unverifiable"
    if "contradict" in verdicts:
        return "contradicted"
    if all(v == "support" for v in verdicts):
        return "supported"
    if any(v == "support" for v in verdicts):
        return "partially_verified"
    return "unverifiable"


def validate_claim(claim: dict, blocks: list[dict]) -> dict:
    problems = []
    subs = claim.get("subclaims") or []
    if not subs:
        problems.append("claim has no subclaims (split first)")
    for s in subs:
        sid = s.get("sub_id", "?")
        v = str(s.get("verdict", ""))
        if v not in VERDICTS:
            problems.append(f"{sid}: invalid verdict '{v}'")
            continue
        if not (s.get("rationale") or "").strip():
            problems.append(f"{sid}: verdict without rationale")
        evs = s.get("evidence") or []
        if v != "not_found" and not evs:
            problems.append(f"{sid}: verdict={v} but no evidence")
        if v == "not_found" and evs:
            problems.append(f"{sid}: verdict=not_found must not carry evidence")
        for ev in evs:
            r = locate.verify_quote(blocks, str(ev.get("loc", "")), ev.get("quote", ""))
            if not r["verified"]:
                problems.append(f"{sid}: evidence unverified ({r['reason']})")
    agg = aggregate([str(s.get("verdict", "")) for s in subs])
    declared = claim.get("status")
    status_ok = declared in (None, agg)
    if declared and declared != agg:
        problems.append(f"declared status '{declared}' != aggregated '{agg}'")
    return {"claim_id": claim.get("claim_id", "?"), "problems": problems,
            "aggregated_status": agg, "ok": not problems}


def validate_claims(claims: list[dict], blocks: list[dict]) -> dict:
    results = [validate_claim(c, blocks) for c in claims]
    counts = {}
    for r in results:
        counts[r["aggregated_status"]] = counts.get(r["aggregated_status"], 0) + 1
    return {"per_claim": results, "status_counts": counts,
            "ok": all(r["ok"] for r in results),
            "verdict_definitions": VERDICT_DEFINITIONS,
            "chain": "论断→子判断→证据片段→原文定位→支持度判定→判定理由"}


def register_conflicts(entries: list[dict]) -> dict:
    """entries: [{topic, side_a: {source, loc, quote}, side_b: {...}, note}]
    冲突双方原话都必须保留，且引文可核验性由调用方先跑 verify。"""
    out = []
    for e in entries:
        ok = all(e.get(k, {}).get("quote") for k in ("side_a", "side_b"))
        out.append({"topic": e.get("topic", ""), "complete": ok,
                    "side_a": e.get("side_a"), "side_b": e.get("side_b"),
                    "note": e.get("note", ""),
                    "problem": None if ok else "conflict registered without both quotes"})
    return {"conflicts": out, "ok": all(o["complete"] for o in out),
            "rule": "冲突双方原话并列保留，不得只报告支持性证据"}


def _demo() -> int:
    blocks = [
        {"loc": "P2", "source": "S1", "text": "Method X reduces latency by 30% on "
         "dataset D1 compared with baseline Y."},
        {"loc": "P5", "source": "S1", "text": "On dataset D2 the gain drops to 5%, "
         "which is not significant (p=0.31)."},
    ]
    claims = [{
        "claim_id": "C1", "text": "方法 X 比基线 Y 快 30%，且在所有数据集上都显著。",
        "subclaims": [
            {"sub_id": "C1-s1", "kind": "comparison", "text": "X 在 D1 上快 30%",
             "verdict": "support",
             "evidence": [{"source": "S1", "loc": "P2",
                           "quote": "reduces latency by 30% on dataset D1"}],
             "rationale": "数值、比较对象、数据集与引文一致"},
            {"sub_id": "C1-s2", "kind": "scope", "text": "在所有数据集上显著",
             "verdict": "contradict",
             "evidence": [{"source": "S1", "loc": "P5",
                           "quote": "not significant (p=0.31)"}],
             "rationale": "D2 上不显著，范围论断被反例推翻"},
        ]}]
    rep = validate_claims(claims, blocks)
    assert rep["ok"] and rep["status_counts"]["contradicted"] == 1, rep
    conf = register_conflicts([{
        "topic": "X 的加速是否普遍显著",
        "side_a": {"source": "S1", "loc": "P2", "quote": "reduces latency by 30%"},
        "side_b": {"source": "S1", "loc": "P5", "quote": "the gain drops to 5%"},
        "note": "差异来自数据集：D1 显著、D2 不显著"}])
    assert conf["ok"]
    bad = [{"claim_id": "C2", "subclaims": [
        {"sub_id": "s1", "verdict": "support", "rationale": "主题相关",
         "evidence": [{"loc": "P2", "quote": "not in the text at all"}]}]}]
    rep2 = validate_claims(bad, blocks)
    assert not rep2["ok"]
    print(json.dumps({"demo": "claims", "ok": rep["ok"],
                      "agg": rep["status_counts"], "fake_evidence_caught": not rep2["ok"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "validate":
        claims = json.load(open(sys.argv[2], encoding="utf-8"))
        blocks = json.load(open(sys.argv[3], encoding="utf-8"))
        rep = validate_claims(claims.get("claims", claims), blocks.get("blocks", blocks))
        if len(sys.argv) > 4:
            json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"ok={rep['ok']} statuses={rep['status_counts']}")
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "conflicts":
        ent = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = register_conflicts(ent.get("entries", ent))
        out = sys.argv[3] if len(sys.argv) > 3 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"ok={rep['ok']} conflicts={len(rep['conflicts'])}")
        sys.exit(0 if rep["ok"] else 1)
    else:
        print("usage: claims.py [validate|conflicts] ...")
        sys.exit(2)
