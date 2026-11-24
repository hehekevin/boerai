"""Review-report builder: counts by type/severity, checklist coverage, 待复核.

Builds the final audit report (JSON + Markdown) from a validated findings
ledger and a checklist. Status rule:
  - 'no_findings' with everything checked    -> clean audit, honest pass
  - findings present                         -> itemized report
  - any unchecked checklist items            -> coverage explicitly partial
The report always lists rejected findings (false-positive control audit trail)
and needs_review items; it never hides them to look complete.
"""
from __future__ import annotations

import json
import sys

from . import checklist as _cl
from . import findings as _fd

SEV_ORDER = {"critical": 0, "major": 1, "minor": 2}
KIND_LABEL = {"error": "错误", "insufficient_evidence": "证据不足",
              "norm_issue": "规范问题", "suggestion": "建议"}
STATUS_LABEL = {"open": "待确认", "confirmed": "已确认", "rejected": "已驳回",
                "needs_review": "待复核"}


def build(ledger: dict, cl: dict | None = None, *, title: str = "",
          case_id: str = "") -> dict:
    live = [f for f in ledger["findings"] if f["status"] != "rejected"]
    rejected = [f for f in ledger["findings"] if f["status"] == "rejected"]
    live.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["id"]))
    cov = _cl.coverage(cl) if cl else None
    counts = {"by_type": _fd.by({"findings": live}, "type"),
              "by_severity": _fd.by({"findings": live}, "severity"),
              "by_kind": _fd.by({"findings": live}, "kind"),
              "by_status": _fd.by({"findings": live}, "status")}
    needs_review = [f["id"] for f in live if f["status"] == "needs_review"]
    unchecked = [i["id"] for i in (cl["items"] if cl else []) if i["status"] == "unchecked"]
    outcome = ("no_findings" if not live else
               "critical_findings" if any(f["severity"] == "critical" for f in live) else
               "findings_present")
    coverage_complete = (cov is None) or (cov["unchecked"] == 0)
    rep = {"title": title, "case_id": case_id, "outcome": outcome,
           "n_findings": len(live), "n_rejected": len(rejected),
           "counts": counts, "findings": live,
           "rejected_findings": [{"id": f["id"], "reason": f["reject_reason"],
                                  "quote": f["quote"][:80]} for f in rejected],
           "needs_review": needs_review,
           "checklist_coverage": cov, "unchecked_items": unchecked,
           "coverage_complete": coverage_complete,
           "status_suggestion": ("success" if coverage_complete else "partial"),
           "honesty": ("empty ledger = no defect found; rejected findings kept for audit; "
                       "unchecked items listed, never implied as checked")}
    return rep


def to_markdown(rep: dict) -> str:
    L = []
    L.append(f"# 审查报告 {rep.get('title') or ''}".rstrip())
    L.append(f"\ncase_id: {rep.get('case_id') or '(unknown)'}  ")
    L.append(f"结论概览: {rep['outcome']} | 有效问题 {rep['n_findings']} 条 | "
             f"驳回 {rep['n_rejected']} 条 | 待复核 {len(rep['needs_review'])} 条")
    if rep["outcome"] == "no_findings":
        L.append("\n**未发现可证实的问题**（空清单是合法结论；未检查项见下，绝不含糊）。")
    cov = rep.get("checklist_coverage")
    if cov:
        L.append(f"\n检查覆盖: {cov['checked']}/{cov['n_items']} 项 "
                 f"({cov['coverage']})；未检查: {', '.join(rep['unchecked_items']) or '无'}")
    L.append("\n## 问题清单（按严重度排序）\n")
    L.append("| id | 类型 | 性质 | 严重度 | 状态 | 定位 | 原文摘录 | 依据 | 修改建议 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for f in rep["findings"]:
        L.append("| {id} | {type} | {kind} | {sev} | {st} | {loc} | {q} | {j} | {s} |".format(
            id=f["id"], type=f["type"], kind=KIND_LABEL.get(f["kind"], f["kind"]),
            sev=f["severity"], st=STATUS_LABEL.get(f["status"], f["status"]),
            loc=f["locator"], q=f["quote"].replace("|", "\\|")[:60],
            j=f["justification"].replace("|", "\\|")[:60],
            s=f.get("suggestion", "").replace("|", "\\|")[:60]))
    if rep["rejected_findings"]:
        L.append("\n## 驳回记录（误报控制审计轨迹）\n")
        for r in rep["rejected_findings"]:
            L.append(f"- {r['id']}: {r['reason']} — 摘录“{r['quote']}…”")
    if rep["needs_review"]:
        L.append("\n## 待复核\n")
        for i in rep["needs_review"]:
            L.append(f"- {i}")
    return "\n".join(L) + "\n"


def _demo() -> int:
    from . import checklist as clmod
    src = ("# Methods\n\nWe recruited n = 42 adults.\n\n"
           "# Results\n\nRecall improved by 18.5% (p = 0.032).")
    led = _fd.new_ledger("demo.md")
    _fd.add(led, type="stats", kind="insufficient_evidence", severity="minor",
            quote="Recall improved by 18.5% (p = 0.032).", locator="§Results ¶2 s1",
            justification="p without CI", suggestion="add 95% CI",
            severity_basis="minor: reporting gap")
    _fd.add(led, type="fact", kind="error", severity="critical",
            quote="This sentence was never written anywhere.", locator="§Methods ¶1 s1",
            justification="fabricated on purpose for demo")
    _fd.validate(led, src)
    cl = clmod.default_checklist()
    clmod.set_status(cl, "stat-report", "issue", finding_ids=["F001"],
                     evidence=[{"quote": "Recall improved by 18.5% (p = 0.032).",
                                "locator": "§Results ¶2 s1"}])
    rep = build(led, cl, title="demo", case_id="demo-case")
    assert rep["n_findings"] == 1 and rep["n_rejected"] == 1
    assert rep["status_suggestion"] == "partial" and len(rep["unchecked_items"]) == 11
    md = to_markdown(rep)
    assert "驳回记录" in md and "F002" in md
    # honest clean report: full checklist pass, zero findings
    led2 = _fd.new_ledger("clean.md")
    cl2 = clmod.default_checklist()
    for it in cl2["items"]:
        clmod.set_status(cl2, it["id"], "pass", evidence=[])
    rep2 = build(led2, cl2, case_id="clean-case")
    assert rep2["outcome"] == "no_findings" and rep2["status_suggestion"] == "success"
    assert "未发现可证实的问题" in to_markdown(rep2)
    print(json.dumps({"demo": "report.build", "outcome": rep["outcome"],
                      "status": rep["status_suggestion"],
                      "clean_case": rep2["outcome"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.report <ledger.json> <checklist.json|-> <out.json> [out.md]
    led = _fd.load(sys.argv[1])
    cl = _cl.load(sys.argv[2]) if sys.argv[2] != "-" else None
    rep = build(led, cl)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if len(sys.argv) > 4:
        open(sys.argv[4], "w", encoding="utf-8").write(to_markdown(rep))
    print(json.dumps({"outcome": rep["outcome"], "n_findings": rep["n_findings"],
                      "status_suggestion": rep["status_suggestion"]}, ensure_ascii=False))
