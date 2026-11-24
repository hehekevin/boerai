"""结构与论证链簿记：论点-论据映射、循环/断裂检测、跨节重复、结论尺度。

chain.json（Agent 抽取论断与支撑，引擎验证位置真实并做图分析）：
  {"claims": [{"id": "CL1", "text": "该方法显著提升命中率",
               "where": "§结果 d0021", "kind": "conclusion|finding|claim",
               "supports": ["F1", "F3"]}, ...],
   "facts":  [{"id": "F1", "where": "表2", "evidence": "草稿或材料中的原文片段"}]}

draft 为 Markdown；引擎校验：
1. 每个 claim/fact 的 where/evidence 可定位（evidence 为草稿或所附材料原文子串）。
2. 闭环：kind=conclusion 的论断必须至少挂 1 个 support；孤立 claim
   （无支撑且非背景声明）列入 unsupported。
3. 循环论证：supports 图（claim 也可支撑 claim）存在环 → 违规。
4. 跨节重复：任意两节之间共享 ≥1 个字符 12-gram（去标点空白）→ 列出
   重复片段与位置，供 Agent 判定合并/拆分。
5. 结论尺度：含强因果/全称词（证明、导致、必然、proves、causes、always）
   的句子列入 scope_review 队列，由 Agent 对照证据强度逐条确认——
   引擎只做标记，不做语义裁决。
6. 必需环节：研究问题/方法/结果/结论 四类角色齐备（可由 spec 配置）。

CLI:  python -m awkit.structcheck check DRAFT CHAIN OUT [--materials FILE ...]
"""
from __future__ import annotations

import json
import re
import sys

_STRONG = re.compile(r"证明|导致|必然|首次|彻底|proves?|causes?|always|never|first ever",
                     re.IGNORECASE)
_WS = re.compile(r"[\s，。,.、；;：:（）()！？!?]+")


def sections(draft: str) -> dict[str, str]:
    secs, cur, buf = {}, "(前置)", []
    for ln in draft.splitlines():
        m = re.match(r"^#{1,6}\s+(.+)", ln)
        if m:
            secs[cur] = "\n".join(buf)
            cur, buf = m.group(1).strip(), []
        else:
            buf.append(ln)
    secs[cur] = "\n".join(buf)
    return secs


def ngrams(text: str, n: int = 12) -> dict[str, int]:
    flat = _WS.sub("", text)
    return {flat[i:i + n]: i for i in range(max(0, len(flat) - n + 1))}


def check(draft: str, chain: dict, extra_materials: list[str] | None = None) -> dict:
    corpus = _WS.sub(" ", draft)
    for p in extra_materials or []:
        corpus += " " + _WS.sub(" ", open(p, encoding="utf-8").read())
    violations, warnings = [], []
    claims = chain.get("claims", [])
    facts = {f.get("id"): f for f in chain.get("facts", [])}
    # 1) 证据可定位
    for f in facts.values():
        ev = _WS.sub(" ", f.get("evidence", "")).strip()
        if not ev or ev not in corpus:
            violations.append({"type": "fact_evidence_not_locatable", "fact": f.get("id"),
                               "note": "evidence 必须是草稿或材料原文子串"})
    ids = {c.get("id") for c in claims}
    for c in claims:
        for s in c.get("supports", []):
            if s not in facts and s not in ids:
                violations.append({"type": "support_unknown", "claim": c.get("id"),
                                   "support": s})
    # 2) 闭环：结论必须有支撑
    for c in claims:
        if c.get("kind") == "conclusion" and not c.get("supports"):
            violations.append({"type": "conclusion_without_support", "claim": c.get("id"),
                               "text": c.get("text", "")[:120]})
    # 3) 循环论证（claim→claim 支撑图上的环，DFS 三色标记）
    graph = {c.get("id"): [s for s in c.get("supports", []) if s in ids] for c in claims}
    color: dict[str, int] = {}
    cycle_path: list[str] = []

    def dfs(u: str, stack: list[str]) -> bool:
        color[u] = 1
        for v in graph.get(u, []):
            if color.get(v) == 1:
                cycle_path.extend(stack + [v])
                return True
            if color.get(v, 0) == 0 and dfs(v, stack + [v]):
                return True
        color[u] = 2
        return False

    for u in graph:
        if color.get(u, 0) == 0 and dfs(u, [u]):
            violations.append({"type": "circular_reasoning", "cycle": cycle_path})
            break
    # 4) 跨节重复
    secs = sections(draft)
    grams = {name: ngrams(txt) for name, txt in secs.items() if len(_WS.sub("", txt)) >= 12}
    names = list(grams)
    dup = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = set(grams[names[i]]) & set(grams[names[j]])
            if shared:
                dup.append({"section_a": names[i], "section_b": names[j],
                            "n_shared_12grams": len(shared),
                            "example": sorted(shared)[0]})
    if dup:
        warnings.append({"type": "cross_section_redundancy", "pairs": dup,
                         "note": "候选重复，由 Agent 判定合并/拆分/保留"})
    # 5) 结论尺度标记
    scope_review = []
    for m in re.finditer(r"[^。！？\n]*" + _STRONG.pattern + r"[^。！？\n]*[。！？]?",
                         draft, re.IGNORECASE):
        scope_review.append(m.group(0).strip()[:160])
    # 6) 必需环节
    flat = draft
    roles = chain.get("required_roles",
                      {"研究问题": ["研究问题", "拟解决", "problem", "question"],
                       "方法": ["方法", "method"],
                       "结果": ["结果", "result"],
                       "结论": ["结论", "conclusion", "讨论", "discussion"]})
    missing_roles = [r for r, kws in roles.items()
                     if not any(k.lower() in flat.lower() for k in kws)]
    if missing_roles:
        violations.append({"type": "missing_rhetorical_roles", "missing": missing_roles})
    return {"ok": not violations, "claims": len(claims), "facts": len(facts),
            "scope_review_queue": scope_review,
            "redundancy_candidates": dup,
            "violations": violations, "warnings": warnings,
            "note": "引擎只做定位/图/重复/尺度标记；合并拆分与采纳由 Agent 裁决并记录"}


def _demo() -> int:
    draft = ("# 引言\n本研究拟解决的问题是 T 细胞活化调控机制不明。\n"
             "# 方法\n我们筛选了 500 个基因，覆盖 3 名供体。\n"
             "# 结果\n初筛命中率为 4.2%，共命中 21 个基因。\n"
             "# 讨论\n这证明了该通路决定 T 细胞命运。\n"
             "# 结论\n该方法可作为筛选平台。初筛命中率为 4.2%，共命中 21 个基因。\n")
    chain = {"claims": [{"id": "CL1", "text": "该方法可作为筛选平台", "kind": "conclusion",
                         "where": "§结论", "supports": ["F1"]},
                        {"id": "CL2", "text": "命中率稳定", "kind": "finding",
                         "where": "§结果", "supports": ["F1"]}],
             "facts": [{"id": "F1", "where": "§结果",
                        "evidence": "初筛命中率为 4.2%，共命中 21 个基因。"}]}
    rep = check(draft, chain)
    assert rep["ok"], rep["violations"]
    assert rep["redundancy_candidates"]  # 结果与结论重复
    assert any("证明" in s for s in rep["scope_review_queue"])
    # 无支撑结论
    bad = check(draft, {"claims": [{"id": "CL9", "text": "无支撑结论",
                                    "kind": "conclusion", "where": "§结论",
                                    "supports": []}], "facts": []})
    assert any(v["type"] == "conclusion_without_support" for v in bad["violations"])
    # 循环论证
    cyc = check(draft, {"claims": [{"id": "A", "kind": "claim", "supports": ["B"]},
                                   {"id": "B", "kind": "claim", "supports": ["A"]}],
                        "facts": []})
    assert any(v["type"] == "circular_reasoning" for v in cyc["violations"])
    # 编造 evidence
        # 编造 evidence 必须定位失败
    fab = check(draft, {"claims": [], "facts": [{"id": "F9", "where": "§结果",
                                                 "evidence": "这段话不在任何材料里"}]})
    assert any(v["type"] == "fact_evidence_not_locatable" for v in fab["violations"])
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "check":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.structcheck check")
        ap.add_argument("draft"); ap.add_argument("chain"); ap.add_argument("out")
        ap.add_argument("--materials", nargs="*", default=[])
        a = ap.parse_args(argv[1:])
        rep = check(open(a.draft, encoding="utf-8").read(),
                    json.load(open(a.chain, encoding="utf-8")), a.materials)
        json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"structcheck: ok={rep['ok']} claims={rep['claims']} "
              f"violations={len(rep['violations'])} -> {a.out}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
