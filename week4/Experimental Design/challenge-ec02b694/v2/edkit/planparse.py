"""Plan-structure extraction: typed items with mandatory locators.

The engine splits a plan document into anchored units — sections, parameter
lines (name: value unit), numbered steps, resource mentions — each carrying a
locator ("L12", "§2", "§2 ¶3"). Downstream bookkeeping (checklist / resources /
verdict) only accepts items whose locator resolves back into the source text:
an item without a resolvable locator is rejected and kept in the ledger with
its rejection reason. Anything the plan does not state stays explicitly
"not stated", never silently satisfied.
"""
from __future__ import annotations

import json
import re
import sys

MD_SECTION_RE = re.compile(r"^\s*(#{1,6})\s*(\S.*)$")
NUM_SECTION_RE = re.compile(r"^\s*((?:第\s*\d+\s*[章节部分]|\d+(?:\.\d+)+))\s*[、.．]?\s*(\S.{0,40})$")
STEP_RE = re.compile(r"^\s*(?:步骤\s*)?(\d{1,2})\s*[.、)）]\s*(\S.{3,200})$")
SENTENCE_END = ("。", "；", ";", "，", ",")
PARAM_RE = re.compile(
    r"^\s*[-*•·]?\s*([\w一-鿿（）()\-/％%]{1,40}?)\s*[:：=]\s*"
    r"(-?\d+(?:\.\d+)?(?:/\d+)?)\s*([a-zA-Zµμ℃°%/\u4e00-\u9fff·²³^-]{0,12})\s*$")
RESOURCE_HINTS = ("设备", "仪器", "耗材", "试剂", "型号", "采购", "库存", "机时",
                  "排期", "预约", "预算", "经费", "报价", "货期", "样本", "伦理")
LOC_RE = re.compile(r"^(?:(?:p\.\d+)\s*)?(?:§\d+(?:\s*¶\d+)?|L\d+)$")


def _line_loc(i: int) -> str:
    return f"L{i + 1}"


def parse_text(text: str, source: str = "plan") -> dict:
    """Deterministic candidate extraction. Candidates are leads for the agent,
    not conclusions; each keeps its locator so the agent can confirm in place."""
    lines = text.splitlines()
    sections, params, steps, resources = [], [], [], []
    sec_no = 0
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        if not line.strip():
            continue
        m = MD_SECTION_RE.match(line)
        if m:
            sec_no += 1
            sections.append({"id": f"S{sec_no}", "title": m.group(2).strip()[:80],
                             "level": len(m.group(1)), "locator": _line_loc(i)})
            continue
        m = NUM_SECTION_RE.match(line)
        # numbered header: multi-level number or 第N章 style, short title, no
        # sentence punctuation — a numbered *step* sentence is not a section
        if m and not m.group(2).rstrip().endswith(SENTENCE_END):
            sec_no += 1
            sections.append({"id": f"S{sec_no}", "title": m.group(2).strip()[:80],
                             "level": 1, "locator": _line_loc(i)})
            continue
        m = STEP_RE.match(line)
        if m:
            steps.append({"id": f"ST{len(steps) + 1}", "index": int(m.group(1)),
                          "text": m.group(2).strip(), "locator": _line_loc(i)})
        m = PARAM_RE.match(line)
        if m and any(u in (m.group(3) or "") for u in
                     ("°", "℃", "%", "m", "g", "L", "h", "s", "元", "n", "x", "µ", "μ",
                      "天", "小时", "分钟", "次", "个", "例", "管", "批", "V", "W", "Pa")):
            params.append({"id": f"P{len(params) + 1}", "name": m.group(1).strip(),
                           "value": m.group(2), "unit": (m.group(3) or "").strip(),
                           "locator": _line_loc(i)})
        if any(h in line for h in RESOURCE_HINTS):
            kind = next(h for h in RESOURCE_HINTS if h in line)
            resources.append({"id": f"R{len(resources) + 1}", "hint_kind": kind,
                              "text": line.strip()[:200], "locator": _line_loc(i)})
    return {"source": source, "n_lines": len(lines), "sections": sections,
            "candidates": {"parameters": params, "steps": steps, "resources": resources},
            "note": "candidates are engine leads; agent confirms each against the located line"}


def new_structure(source: str) -> dict:
    return {"source": source, "sections": [], "parameters": [], "steps": [],
            "resources": [], "controls": [], "variables": [], "risks_stated": []}


def resolve_locator(locator: str, text: str) -> str | None:
    """Return the referenced source line for L<n> locators, else None."""
    m = re.search(r"L(\d+)", locator or "")
    if not m or not LOC_RE.match((locator or "").strip()):
        return None
    lines = text.splitlines()
    n = int(m.group(1))
    if 1 <= n <= len(lines):
        return lines[n - 1].strip()
    return None


def validate_structure(struct: dict, text: str) -> dict:
    """Every item in every list must carry a locator that resolves into the
    source text. Rejected items are kept with reasons — never dropped silently."""
    problems, rejected, n_items = [], [], 0
    for lst in ("sections", "parameters", "steps", "resources", "controls",
                "variables", "risks_stated"):
        for item in struct.get(lst) or []:
            n_items += 1
            iid = item.get("id") or item.get("name") or f"{lst}[{n_items}]"
            loc = (item.get("locator") or "").strip()
            if not loc:
                rejected.append({"list": lst, "id": iid, "reason": "missing locator"})
                problems.append(f"{lst}/{iid}: missing locator")
                continue
            ref = resolve_locator(loc, text)
            if ref is None:
                rejected.append({"list": lst, "id": iid, "reason": f"locator '{loc}' does not resolve"})
                problems.append(f"{lst}/{iid}: locator '{loc}' unresolvable")
    return {"ok": not problems, "n_items": n_items, "problems": problems,
            "rejected": rejected,
            "note": "items without a resolvable locator are rejected and kept, not deleted"}


def _demo() -> int:
    plan = ("# 实验方案 v1\n## 1 研究目标\n验证涂层对腐蚀的抑制效果。\n"
            "## 2 参数\n温度: 37 ℃\n时长: 48 h\n样本量: 12 例\n"
            "## 3 步骤\n1. 准备样品并分组。\n2. 设置对照并记录基线。\n"
            "## 4 资源\n设备：盐雾试验箱（型号 SY-9），需预约排期。\n耗材：培养液 500 mL。\n")
    rep = parse_text(plan, "demo-plan")
    assert len(rep["sections"]) == 5, rep["sections"]
    vals = {(p["name"], p["value"], p["unit"]) for p in rep["candidates"]["parameters"]}
    assert ("温度", "37", "℃") in vals, vals
    assert len(rep["candidates"]["steps"]) == 2
    texts = [s["text"] for s in rep["candidates"]["steps"]]
    assert any("准备样品" in t for t in texts) and not any(t.startswith("研究目标") for t in texts)
    struct = new_structure("demo-plan")
    struct["parameters"].append({"id": "P1", "name": "温度", "value": "37", "unit": "℃", "locator": "L5"})
    ok = validate_structure(struct, plan)
    assert ok["ok"], ok
    struct["steps"].append({"id": "ST9", "index": 9, "text": "phantom step"})  # no locator
    struct["resources"].append({"id": "R9", "text": "phantom", "locator": "L999"})
    bad = validate_structure(struct, plan)
    assert not bad["ok"] and len(bad["rejected"]) == 2, bad
    print(json.dumps({"demo": "planparse", "sections": len(rep["sections"]),
                      "params": len(rep["candidates"]["parameters"]),
                      "rejected_without_locator": len(bad["rejected"])}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "parse":
        text = open(argv[1], encoding="utf-8").read()
        rep = parse_text(text, argv[1])
        json.dump(rep, open(argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"sections={len(rep['sections'])} params={len(rep['candidates']['parameters'])} "
              f"steps={len(rep['candidates']['steps'])} -> {argv[2]}")
        return 0
    if len(argv) >= 3 and argv[0] == "validate":
        struct = json.load(open(argv[1], encoding="utf-8"))
        text = open(argv[2], encoding="utf-8").read()
        rep = validate_structure(struct, text)
        if len(argv) > 3:
            json.dump(rep, open(argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"ok": rep["ok"], "n_items": rep["n_items"],
                          "problems": len(rep["problems"])}, ensure_ascii=False))
        return 0 if rep["ok"] else 1
    print("usage: planparse parse <plan.txt> <out.json> | planparse validate <struct.json> <plan.txt> [out.json]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
