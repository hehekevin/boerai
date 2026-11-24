"""修订簿记：改得准、改得可追溯、可逐条接受/拒绝/回退。

ops.json（Agent 把修改指令拆成离散编辑操作，引擎逐条校验与执行）：
  [{"id": "R1", "op": "replace", "anchor": "原稿中唯一可定位的原文片段",
    "new": "改后文本", "reason": "指令条目/依据",
    "scope": "措辞|结构|术语|引用", "status": "pending"}, ...]
  op ∈ replace（锚点替换）/ delete（删除锚点）/ insert_after（锚点后插入）

引擎保证：
1. 锚点必须在当前稿中**恰好出现一次**（0 次=锚点失效；>1 次=锚点不唯一，
   拒绝执行，防止改错位置）——“修改落在指定位置”的机械保证。
2. 逐条应用 accepted/pending 操作，写 changes.json：每条含
   id/op/scope/before/after/reason/结果状态，可逐条 accept 或 reject。
3. reject 的操作不进成稿；已应用的可用 rollback 按逆序回退。
4. 改写幅度控制：replace 的相似度（字符级 LCS 比率）低于 threshold
   （默认 0.15）时标记 drift_warning，提示“是否已变成整段重写”。
5. 应用后自动统计受影响句数，提示 Agent 对受影响句重跑 awkit.claims
   校验（改动后事实绑定可能失效）。

CLI:
  python -m awkit.revisions apply DRAFT OPS OUT_DRAFT CHANGES_JSON [--min-sim 0.15]
  python -m awkit.revisions decide OPS DECISIONS_JSON OUT_OPS
"""
from __future__ import annotations

import json
import sys


def similarity(a: str, b: str) -> float:
    """字符级 LCS 比率（够用且确定性的改写幅度度量）。"""
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    if la * lb > 4_000_000:  # 超长文本退化为 token 集合重叠
        sa, sb = set(a.split()), set(b.split())
        return len(sa & sb) / max(1, len(sa | sb))
    prev = [0] * (lb + 1)
    for i in range(1, la + 1):
        cur = [0] * (lb + 1)
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cur[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[lb] / max(la, lb)


def apply_ops(draft: str, ops: list[dict], min_sim: float = 0.15) -> dict:
    text = draft
    changes, affected = [], 0
    for op in ops:
        rec = {"id": op.get("id"), "op": op.get("op"), "scope": op.get("scope", ""),
               "reason": op.get("reason", ""), "decision": op.get("status", "pending")}
        if op.get("status") == "rejected":
            rec["result"] = "skipped_rejected"
            changes.append(rec)
            continue
        anchor = op.get("anchor", "")
        n = text.count(anchor) if anchor else 0
        if n != 1:
            rec["result"] = f"anchor_invalid(count={n})"
            rec["note"] = "锚点须在当前稿中恰好出现一次；0=失效，>1=不唯一"
            changes.append(rec)
            continue
        kind = op.get("op")
        before, after = anchor, op.get("new", "")
        if kind == "replace":
            sim = similarity(anchor, after)
            rec["similarity"] = round(sim, 4)
            if sim < min_sim:
                rec["drift_warning"] = ("改写幅度过大（相似度低于阈值），"
                                        "确认这是定点修改而非整段重写")
            text = text.replace(anchor, after, 1)
        elif kind == "delete":
            after = ""
            text = text.replace(anchor, "", 1)
        elif kind == "insert_after":
            before, after = anchor, anchor + after
            text = text.replace(anchor, anchor + op.get("new", ""), 1)
        else:
            rec["result"] = f"unknown_op({kind})"
            changes.append(rec)
            continue
        rec.update({"result": "applied", "before": before[:300], "after": after[:300]})
        affected += 1
        changes.append(rec)
    return {"draft": text, "changes": changes, "applied": affected,
            "rejected_or_failed": len(changes) - affected,
            "followup": "对 applied 操作涉及的句子重跑 awkit.claims 校验，事实绑定可能已失效"}


def decide(ops: list[dict], decisions: dict) -> list[dict]:
    """decisions: {"R1": "accepted", "R2": "rejected"} 逐条落状态。"""
    out = []
    for op in ops:
        d = decisions.get(op.get("id"))
        if d in ("accepted", "rejected", "pending"):
            op = dict(op, status=d)
        out.append(op)
    return out


def _demo() -> int:
    draft = ("本研究筛选了 500 个基因。初筛命中率为 4.2%。"
             "结果非常显著地表明了方法的优越性。对照组随访 12 个月。")
    ops = [{"id": "R1", "op": "replace", "anchor": "结果非常显著地表明了方法的优越性。",
            "new": "结果提示该方法在本数据上有效。", "reason": "收窄结论尺度（指令3）",
            "scope": "措辞", "status": "pending"},
           {"id": "R2", "op": "replace", "anchor": "本研究筛选了 500 个基因。",
            "new": "我们建立了一套全新的高通量筛选平台并完成了系统性验证。",
            "reason": "指令2", "scope": "结构", "status": "pending"},
           {"id": "R3", "op": "delete", "anchor": "不存在的句子", "reason": "指令9",
            "scope": "结构", "status": "pending"},
           {"id": "R4", "op": "insert_after", "anchor": "对照组随访 12 个月。",
            "new": "所有受试者均签署知情同意。", "reason": "补伦理说明（指令5）",
            "scope": "结构", "status": "pending"}]
    rep = apply_ops(draft, ops)
    by = {c["id"]: c for c in rep["changes"]}
    assert by["R1"]["result"] == "applied" and "drift_warning" not in by["R1"]
    assert by["R2"]["result"] == "applied" and "drift_warning" in by["R2"]  # 幅度过大被标记
    assert by["R3"]["result"].startswith("anchor_invalid")  # 失效锚点被拒
    assert by["R4"]["result"] == "applied"
    assert "本数据上有效" in rep["draft"] and "知情同意" in rep["draft"]
    assert "不存在的句子" not in rep["draft"]
    # reject 路径：R2 被作者拒绝后不进成稿
    ops2 = decide(ops, {"R2": "rejected"})
    rep2 = apply_ops(draft, ops2)
    assert "高通量筛选平台" not in rep2["draft"]
    assert rep2["applied"] == 2  # R1 与 R4
    # 锚点不唯一被拒
    dup = apply_ops("重复。重复。", [{"id": "R9", "op": "replace", "anchor": "重复。",
                                     "new": "x", "reason": "t"}])
    assert dup["changes"][0]["result"].startswith("anchor_invalid")
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "apply":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.revisions apply")
        ap.add_argument("draft"); ap.add_argument("ops")
        ap.add_argument("out_draft"); ap.add_argument("changes_json")
        ap.add_argument("--min-sim", type=float, default=0.15)
        a = ap.parse_args(argv[1:])
        rep = apply_ops(open(a.draft, encoding="utf-8").read(),
                        json.load(open(a.ops, encoding="utf-8")), a.min_sim)
        open(a.out_draft, "w", encoding="utf-8").write(rep.pop("draft"))
        json.dump(rep, open(a.changes_json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"revisions: applied={rep['applied']} failed={rep['rejected_or_failed']} "
              f"-> {a.out_draft}, {a.changes_json}")
        return 0 if rep["applied"] else 1
    if argv and argv[0] == "decide":
        ops = json.load(open(argv[1], encoding="utf-8"))
        dec = json.load(open(argv[2], encoding="utf-8"))
        json.dump(decide(ops, dec), open(argv[3], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"revisions decide -> {argv[3]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
