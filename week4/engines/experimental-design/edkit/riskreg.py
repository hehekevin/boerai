"""Risk register: risks with likelihood/impact/mitigation, validated.

Rules enforced by the validator (deterministic, no semantic guessing):
- every risk must name a CONCRETE failure_mode (generic phrases rejected);
- high-severity risks (score >= 6 on the 1-3 x 1-3 matrix, or high impact
  with at-least-medium likelihood) MUST carry both mitigation and contingency
  (降级路径/替代方案); missing ones are problems, not suggestions;
- mitigation/contingency text must be concrete too (generic filler rejected);
- plan steps that mention exception handling (异常/故障/污染/止损/如果…则)
  must map to a register entry via addresses_step; unmapped ones are listed
  explicitly — an exception step without a failure mode is a review gap.
"""
from __future__ import annotations

import json
import re
import sys

LEVELS = ("low", "medium", "high")
SCORE = {"low": 1, "medium": 2, "high": 3}
GENERIC_FAILURE = ("注意安全", "可能失败", "出现问题", "意外情况", "其他风险", "未知风险", "异常情况")
GENERIC_MITIGATION = ("注意安全", "加强管理", "仔细检查", "及时处理", "及时止损", "提高警惕", "按规范操作")
EXCEPTION_STEP_RE = re.compile(r"异常|故障|污染|止损|失败|失效|越界|偏差|如果.*则|若.*则")


def new_register(source: str = "") -> dict:
    return {"source": source, "risks": []}


def severity(likelihood: str, impact: str) -> dict:
    assert likelihood in SCORE and impact in SCORE, (likelihood, impact)
    s = SCORE[likelihood] * SCORE[impact]
    level = "high" if s >= 6 or (impact == "high" and SCORE[likelihood] >= 2) else \
        "medium" if s >= 3 else "low"
    return {"score": s, "level": level}


def add_risk(reg: dict, *, risk_id: str, title: str, failure_mode: str,
             likelihood: str, impact: str, mitigation: str = "",
             contingency: str = "", locator: str = "", addresses_step: str = "") -> dict:
    risk = {"id": risk_id, "title": title, "failure_mode": failure_mode,
            "likelihood": likelihood, "impact": impact,
            "severity": severity(likelihood, impact),
            "mitigation": mitigation, "contingency": contingency,
            "locator": locator, "addresses_step": addresses_step}
    reg["risks"].append(risk)
    return risk


def _is_generic(text: str, bank: tuple) -> bool:
    t = (text or "").strip()
    return (not t) or any(t == g or (len(t) <= len(g) + 2 and g in t) for g in bank)


def validate_register(reg: dict, plan_steps: list | None = None) -> dict:
    problems = []
    for r in reg["risks"]:
        rid = r.get("id", "?")
        if _is_generic(r.get("failure_mode", ""), GENERIC_FAILURE):
            problems.append(f"{rid}: failure_mode missing or generic ('{r.get('failure_mode', '')}') — must name a concrete failure mode")
        if r.get("severity", {}).get("level") == "high":
            if _is_generic(r.get("mitigation", ""), GENERIC_MITIGATION):
                problems.append(f"{rid}: HIGH risk without concrete mitigation — rejected until provided")
            if _is_generic(r.get("contingency", ""), GENERIC_MITIGATION):
                problems.append(f"{rid}: HIGH risk without concrete contingency (降级/替代路径)")
        elif not (r.get("mitigation") or "").strip():
            problems.append(f"{rid}: non-high risk without mitigation — still required for the register to be actionable")
    unmapped = []
    if plan_steps:
        addressed = {r.get("addresses_step") for r in reg["risks"] if r.get("addresses_step")}
        for st in plan_steps:
            if EXCEPTION_STEP_RE.search(st.get("text", "")) and st.get("id") not in addressed:
                unmapped.append({"step_id": st.get("id"), "text": st.get("text", "")[:120],
                                 "locator": st.get("locator", "")})
                problems.append(f"step {st.get('id')}: exception-handling step not mapped to any failure mode")
    return {"ok": not problems, "n_risks": len(reg["risks"]), "problems": problems,
            "unmapped_exception_steps": unmapped,
            "note": "high risks without mitigation/contingency block the register; "
                    "exception steps must map to concrete failure modes"}


def _demo() -> int:
    reg = new_register("demo-plan")
    add_risk(reg, risk_id="K1", title="样本量不足", failure_mode="样本采集量低于统计功效所需 12 例",
             likelihood="medium", impact="high",
             mitigation="预先筛查 20 例候选，入组前复核纳入标准",
             contingency="降级为探索性研究并改写判读标准；转 PI 确认",
             locator="plan.md L16", addresses_step="ST2")
    good = validate_register(reg, plan_steps=[{"id": "ST2", "text": "若样本不足则启动补采", "locator": "L16"}])
    assert good["ok"], good
    bad = new_register("demo-plan")
    add_risk(bad, risk_id="K2", title="安全", failure_mode="注意安全",
             likelihood="high", impact="high", mitigation="加强管理")
    add_risk(bad, risk_id="K3", title="设备", failure_mode="盐雾箱加热管烧毁",
             likelihood="low", impact="medium")
    rep = validate_register(bad, plan_steps=[{"id": "ST7", "text": "设备故障时启用备用机", "locator": "L22"}])
    assert not rep["ok"] and len(rep["problems"]) >= 4, rep
    assert rep["unmapped_exception_steps"] and rep["unmapped_exception_steps"][0]["step_id"] == "ST7"
    print(json.dumps({"demo": "riskreg", "clean_register_ok": good["ok"],
                      "problems_flagged": len(rep["problems"]),
                      "unmapped_steps": len(rep["unmapped_exception_steps"])}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "init":
        out = argv[1]
        json.dump(new_register(), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"empty risk register -> {out}")
        return 0
    if len(argv) >= 2 and argv[0] == "validate":
        reg = json.load(open(argv[1], encoding="utf-8"))
        steps = None
        if len(argv) > 2:
            steps = json.load(open(argv[2], encoding="utf-8")).get("steps")
        rep = validate_register(reg, steps)
        out = argv[3] if len(argv) > 3 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"ok": rep["ok"], "problems": rep["problems"]}, ensure_ascii=False))
        return 0 if rep["ok"] else 1
    print("usage: riskreg init <out.json> | validate <reg.json> [plan_struct.json] [out.json]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
