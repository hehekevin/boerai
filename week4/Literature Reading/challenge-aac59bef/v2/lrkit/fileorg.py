"""File organization: 盘点、命名、去重/版本区分、可回滚的批量整理。

原则：引擎产"操作计划"，Agent/用户审阅后才 apply；apply 逐条记录，
生成 undo 脚本；重复运行幂等（目标已存在且内容相同 → skip）。

清单项（inventory.json）：[{path, sha256, bytes, kind, metadata: {title,
authors, year, doi, venue, doc_type}, notes}]

操作计划：[{op: move|rename|skip|conflict, src, dst?, reason, rule_id?}]
  - 目标冲突（dst 已存在且哈希不同）→ op=conflict，绝不覆盖
  - 元数据缺失字段 → 文件名占位 "unknown"，并在 notes 如实标注
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys

MAX_NAME = 120

VERSION_PAT = [
    (re.compile(r"preprint|arxiv|biorxiv|manuscript", re.I), "preprint"),
    (re.compile(r"accepted|final|published|version.?of.?record|vor", re.I), "published"),
    (re.compile(r"supp|supporting|si[_\-. ]", re.I), "supplement"),
    (re.compile(r"rev(?:ised|ision)?[_\-. ]?v?\d", re.I), "revision"),
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def guess_version(path: str, metadata: dict | None = None) -> dict:
    md = metadata or {}
    for rx, label in VERSION_PAT:
        if rx.search(os.path.basename(path)) or rx.search(str(md.get("venue", ""))):
            return {"version": label, "basis": "filename/venue pattern", "pattern": rx.pattern}
    if md.get("doi"):
        return {"version": "published", "basis": "has DOI"}
    return {"version": "unknown", "basis": "no version signal"}


def sanitize(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", " ", (s or "")).strip()
    s = re.sub(r"[^\w\s.,()\-]+", "", s, flags=re.UNICODE)
    return s[:maxlen].strip(" .") or "unknown"


def make_name(metadata: dict, template: str = "{authors}-{year}-{title}") -> dict:
    """按模板生成文件名；缺字段降级为 unknown 并记录。"""
    md = dict(metadata or {})
    missing = [k for k in ("authors", "year", "title") if not md.get(k)]
    if isinstance(md.get("authors"), list):
        first = md["authors"][0] if md["authors"] else "unknown"
        md["authors"] = first + (" et al" if len(md["authors"]) > 1 else "")
    name = template.format(**{k: sanitize(str(v)) for k, v in md.items()}
                           | {k: "unknown" for k in missing})
    name = name[:MAX_NAME]
    return {"name": name, "missing_fields": missing,
            "rule": "缺失元数据字段降级为 unknown，绝不凭空编造"}


def plan_operations(inventory: list[dict], dest_root: str,
                    category_of: dict | None = None) -> dict:
    """生成操作计划。category_of: path -> 目录类别（Agent 语义判定后传入）。"""
    category_of = category_of or {}
    seen_dst = {}
    plan = []
    for item in inventory:
        src = item["path"]
        cat = category_of.get(src, "uncategorized")
        nm = make_name(item.get("metadata") or {})
        ext = os.path.splitext(src)[1]
        dst = os.path.join(dest_root, cat, nm["name"] + ext)
        ver = guess_version(src, item.get("metadata"))
        entry = {"src": src, "dst": dst, "category": cat, "version": ver,
                 "sha256": item.get("sha256"), "missing_fields": nm["missing_fields"]}
        if dst in seen_dst and seen_dst[dst]["sha256"] != item.get("sha256"):
            entry.update(op="conflict",
                         reason=f"目标名冲突（与 {seen_dst[dst]['src']} 内容不同），不覆盖")
        elif dst in seen_dst:
            entry.update(op="skip", reason="内容与已计划项完全相同（重复下载）")
        else:
            entry.update(op="move", reason=f"命名规则+分类 '{cat}'")
            seen_dst[dst] = {"src": src, "sha256": item.get("sha256")}
        plan.append(entry)
    counts = {}
    for e in plan:
        counts[e["op"]] = counts.get(e["op"], 0) + 1
    return {"plan": plan, "counts": counts,
            "rule": "同名不同内容 → conflict 不覆盖；同名同内容 → skip；缺失字段 → unknown"}


def apply_plan(plan: list[dict], log_path: str) -> dict:
    """执行 move 操作并写可回滚日志。幂等：dst 已存在且同哈希 → skip。"""
    done, problems = [], []
    for e in plan:
        if e.get("op") != "move":
            continue
        src, dst = e["src"], e["dst"]
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                if os.path.isfile(dst) and sha256_file(dst) == e.get("sha256"):
                    done.append({"src": src, "dst": dst, "result": "already_done"})
                    continue
                problems.append({"src": src, "dst": dst,
                                 "problem": "dst exists with different content; not overwriting"})
                continue
            shutil.copy2(src, dst)  # 复制而非移动：回滚=删除 dst，源永不丢失
            done.append({"src": src, "dst": dst, "result": "copied"})
        except OSError as exc:
            problems.append({"src": src, "dst": dst, "problem": str(exc)})
    log = {"ops": done, "problems": problems,
           "undo": "删除 log.ops 中所有 dst 即回滚；源文件从未被移动或删除",
           "idempotent": True}
    os.makedirs(os.path.dirname(os.path.abspath(log_path)) or ".", exist_ok=True)
    json.dump(log, open(log_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return log


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="fileorg-demo-")
    f1 = os.path.join(tmp, "smith2020 preprint.pdf")
    f2 = os.path.join(tmp, "copy of smith2020 preprint.pdf")
    f3 = os.path.join(tmp, "zhang-final-vor.pdf")
    for f, content in ((f1, b"AAA"), (f2, b"AAA"), (f3, b"BBB")):
        open(f, "wb").write(content)
    inv = [{"path": f, "sha256": sha256_file(f), "bytes": 3, "kind": "pdf",
            "metadata": md} for f, md in [
        (f1, {"authors": ["Smith"], "year": 2020, "title": "Alloy Design"}),
        (f2, {"authors": ["Smith"], "year": 2020, "title": "Alloy Design"}),
        (f3, {"title": "Photocatalysis"})]]  # 缺 authors/year → unknown
    rep = plan_operations(inv, os.path.join(tmp, "lib"),
                          category_of={f1: "alloys", f2: "alloys", f3: "catalysis"})
    assert rep["counts"].get("move") == 2 and rep["counts"].get("skip") == 1, rep["counts"]
    assert "unknown" in next(e["dst"] for e in rep["plan"] if e["src"] == f3)
    log = apply_plan(rep["plan"], os.path.join(tmp, "ops_log.json"))
    assert not log["problems"] and len(log["ops"]) == 2
    log2 = apply_plan(rep["plan"], os.path.join(tmp, "ops_log2.json"))  # 幂等重跑
    assert all(o["result"] == "already_done" for o in log2["ops"])
    v = guess_version(f1, inv[0]["metadata"])
    assert v["version"] == "preprint"
    print(json.dumps({"demo": "fileorg", "plan_counts": rep["counts"],
                      "applied": len(log["ops"]), "idempotent": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "plan":
        inv = json.load(open(sys.argv[2], encoding="utf-8"))
        cat = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else {}
        rep = plan_operations(inv.get("files", inv), sys.argv[3],
                              cat.get("categories", cat))
        json.dump(rep, open(sys.argv[5], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"counts={rep['counts']} -> {sys.argv[5]}")
    elif cmd == "apply":
        plan = json.load(open(sys.argv[2], encoding="utf-8"))
        log = apply_plan(plan.get("plan", plan), sys.argv[3])
        print(f"applied={len(log['ops'])} problems={len(log['problems'])}")
        sys.exit(0 if not log["problems"] else 1)
    else:
        print("usage: fileorg.py [plan|apply] ...")
        sys.exit(2)
