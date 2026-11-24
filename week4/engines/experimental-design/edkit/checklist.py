"""Constraint checklists: six facets, each item with rule + required evidence.

Facets: equipment / material / time / sample / ethics / safety. Every item
declares how to judge (rule) and what must be attached (required_evidence).
Statuses: pass | fail | conditional | needs_review | not_applicable |
unchecked. Items start as unchecked and stay explicit forever: coverage
reports them by id, and the verdict builder refuses to call a plan feasible
while any item is unchecked — nothing the plan omitted is defaulted to pass.
"""
from __future__ import annotations

import json
import sys

ITEM_STATUS = ("pass", "fail", "conditional", "needs_review", "not_applicable", "unchecked")
STATUS_LABELS = {"pass": "通过", "fail": "不满足", "conditional": "有条件通过",
                 "needs_review": "待复核", "not_applicable": "不适用", "unchecked": "未检查"}

DEFAULT_ITEMS = [
    ("eq-presence", "equipment", "方案所需设备是否逐项到位（型号/量程/精度与步骤匹配）",
     "逐台比对设备清单：型号、量程、附件与方案步骤要求一致",
     "设备清单行定位 + 方案步骤定位"),
    ("eq-booking", "equipment", "设备排期/机时是否满足方案时间窗",
     "预约合同 earliest_slot 与方案 needed_by 比较（resources.check_booking）",
     "两个日期 + 机时算式 + 合同定位"),
    ("mat-quantity", "material", "耗材/试剂数量是否够（含损耗）",
     "需求量 vs 库存量精确减法，短缺量不得约去（resources.check_materials）",
     "需求/库存两个数 + 单位 + 双侧定位"),
    ("mat-procurement", "material", "需采购项的货期与价格是否在预算与截止内",
     "采购目录 price*shortfall 精确算价、lead_days 对截止日期",
     "价格与货期来源行定位 + 算式"),
    ("time-estimate", "time", "每步时长是否有依据（设备占用/人工/等待/周转分列）",
     "逐步时长求和（resources.check_schedule），不接受无依据总数",
     "逐步时长表 + 求和行"),
    ("time-window", "time", "总周期（含排期与返工余量）是否落在可用窗口内",
     "总时长 vs 可用窗口比较，两个操作数并列",
     "总时长与窗口两个值 + 来源定位"),
    ("sample-source", "sample", "样本来源、数量、保存条件是否明确且可满足",
     "来源/数量/保存条件三要素逐项在方案或附件中找到定位；缺失即 fail 或 needs_review",
     "三要素各自定位或缺失声明"),
    ("sample-size", "sample", "样本量/重复数是否支撑判读标准",
     "样本量依据（预实验/文献/功效估算）须在方案中有定位",
     "依据片段定位；无依据则 fail"),
    ("ethics-approval", "ethics", "涉及动物/人体样本/个人数据时审批级别与状态是否明确",
     "审批级别、受理机构、当前状态三要素；未定即 needs_review，绝不默认已批",
     "审批表单/规范条目定位或'未提供'声明"),
    ("ethics-consent", "ethics", "知情同意/数据脱敏等伦理材料是否齐备",
     "材料清单逐项核对；缺失列出名称",
     "材料名 + 定位或缺失声明"),
    ("safety-hazard", "safety", "危险试剂/生物安全/高温高压等危险源是否识别并有防护",
     "危险源清单与防护/操作规程对应；SOP 条目作判定依据",
     "危险源行 + SOP 条目定位"),
    ("safety-waste", "safety", "废弃物处置与应急预案是否符合安全规范",
     "处置路径与预案步骤在方案或 SOP 中有定位",
     "处置/预案片段定位"),
]


def default_checklist(name: str = "six-facet-constraints") -> dict:
    return {"name": name,
            "items": [{"id": i, "facet": f, "question": q, "rule": r,
                       "required_evidence": ev, "status": "unchecked",
                       "evidence": [], "condition": "", "note": ""}
                      for i, f, q, r, ev in DEFAULT_ITEMS]}


def load(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def save(cl: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cl, fh, ensure_ascii=False, indent=1)


def set_status(cl: dict, item_id: str, status: str, *, evidence: list | None = None,
               condition: str = "", note: str = "") -> dict:
    """fail/conditional/needs_review require evidence or note; conditional
    additionally requires an explicit, executable condition string."""
    assert status in ITEM_STATUS, status
    for it in cl["items"]:
        if it["id"] != item_id:
            continue
        if status in ("fail", "conditional", "needs_review") and not (evidence or note):
            raise ValueError(f"{item_id}: status={status} requires evidence or note")
        if status == "conditional" and not condition.strip():
            raise ValueError(f"{item_id}: conditional requires an explicit condition")
        it["status"] = status
        if evidence is not None:
            it["evidence"] = evidence
        it["condition"] = condition
        it["note"] = note
        return it
    raise KeyError(item_id)


def coverage(cl: dict) -> dict:
    """Per-facet and overall coverage. Unchecked items are listed by id —
    a report may never imply full coverage when items were skipped."""
    probs = []
    for it in cl["items"]:
        if it["status"] not in ITEM_STATUS:
            probs.append(f"{it['id']}: bad status '{it['status']}'")
        if it["status"] in ("fail", "conditional") and not (it["evidence"] or it["note"]):
            probs.append(f"{it['id']}: {it['status']} without evidence/note")
        if it["status"] == "conditional" and not it.get("condition"):
            probs.append(f"{it['id']}: conditional without condition text")
    facets = sorted({it["facet"] for it in cl["items"]})
    per_facet = {f: {s: sum(1 for i in cl["items"] if i["facet"] == f and i["status"] == s)
                     for s in ITEM_STATUS} for f in facets}
    n = len(cl["items"])
    unchecked = [i["id"] for i in cl["items"] if i["status"] == "unchecked"]
    return {"n_items": n, "checked": n - len(unchecked), "unchecked_items": unchecked,
            "coverage": round((n - len(unchecked)) / n, 4) if n else None,
            "per_facet": per_facet, "problems": probs, "labels": STATUS_LABELS,
            "note": "unchecked items are reported by id, never hidden or defaulted to pass"}


def _demo() -> int:
    cl = default_checklist()
    assert len(cl["items"]) == 12
    assert all(i["status"] == "unchecked" for i in cl["items"])
    set_status(cl, "mat-quantity", "fail",
               evidence=[{"quote": "库存 1000 mL，需求 1500 mL，短缺 500 mL",
                          "locator": "inventory.csv L4 / plan.md L18"}],
               note="数量不满足")
    set_status(cl, "eq-booking", "conditional",
               condition="盐雾箱须改约到 2026-03-01 之前的机时档",
               evidence=[{"quote": "earliest_slot=2026-03-10 > needed_by=2026-03-05",
                          "locator": "booking.json L7"}])
    try:
        set_status(cl, "safety-hazard", "conditional")  # no condition -> must raise
        raise AssertionError("conditional without condition was accepted")
    except ValueError:
        pass
    cov = coverage(cl)
    assert cov["checked"] == 2 and len(cov["unchecked_items"]) == 10, cov
    assert not cov["problems"], cov["problems"]
    print(json.dumps({"demo": "checklist", "items": cov["n_items"],
                      "checked": cov["checked"],
                      "unchecked_listed": len(cov["unchecked_items"])}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "init":
        out = argv[1]
        save(default_checklist(), out)
        print(f"default checklist (12 items, all unchecked) -> {out}")
        return 0
    if len(argv) >= 2 and argv[0] == "coverage":
        print(json.dumps(coverage(load(argv[1])), ensure_ascii=False, indent=1))
        return 0
    if len(argv) >= 4 and argv[0] == "set":
        cl = load(argv[1])
        set_status(cl, argv[2], argv[3],
                   note=argv[4] if len(argv) > 4 else "",
                   condition=argv[5] if len(argv) > 5 else "")
        save(cl, argv[1])
        print(f"{argv[2]} -> {argv[3]}")
        return 0
    print("usage: checklist init <out.json> | coverage <cl.json> | set <cl.json> <id> <status> [note] [condition]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
