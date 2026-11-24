"""图表选型与一致性检查：数据形态 → 图型规则，带推荐理由与被否决项；轴/单位校验。

本模块不画图（离线标准库环境无绘图后端，也不该让引擎做视觉判断）——它产出
可审计的 chart spec JSON：图型、编码映射、轴与单位、误差表示、被否决的候选
及理由。绘图代码由 Agent 依据 spec 生成，校验器再核对 spec 与数据画像一致。

选型规则（shape → chart），每条给 justification 与 rejected[]：
  intent=distribution: 1 连续 → histogram；分组连续 → boxplot（n≥5/组）
  intent=comparison:   无序分类 × 连续 → bar（均值）或 boxplot（分布）；
                       类别 >12 → 条形横向并警告；构成 ≠ 比较 → 不用饼图
  intent=relation:     连续×连续 → scatter；加分组 → 颜色/形状编码
  intent=trend:        时间×连续 → line（禁止并列柱冒充时间序列）
  intent=composition:  少量类别（≤6）占比 → stacked bar；饼图仅在 ≤5 类且强调份额时可用

一致性检查（chart spec × 数据画像）：
- 轴变量类型与图型匹配（时间轴必须是 date/有序）
- 单位：同轴多系列单位必须一致，不一致拒绝并要求归一化
- 误差表示必须声明 sd/se/ci95，不得裸画均值
- 类别数超限、基线截断、3D/双轴 → 显式警告
"""
from __future__ import annotations

import json
import sys

MAX_BAR_CATEGORIES = 12
MAX_PIE_CATEGORIES = 5


def select_chart(shape: dict) -> dict:
    """shape: {intent, x_type, y_type, n_categories?, n_series?, has_time?}。
    x_type/y_type ∈ numeric|categorical|date|none。"""
    intent = shape.get("intent", "")
    xt, yt = shape.get("x_type"), shape.get("y_type")
    ncat = shape.get("n_categories")
    rejected = []

    def reject(chart, why):
        rejected.append({"chart": chart, "reason": why})

    if intent == "trend" or xt == "date":
        if intent != "trend":
            reject("bar", "time-ordered x as side-by-side bars hides continuity and ordering")
        return {"chart": "line", "encoding": {"x": "time", "y": "value", "group": "series"},
                "justification": "time × numeric → line preserves order and slope perception",
                "rejected": rejected, "checks": _base_checks(shape)}

    if intent == "distribution":
        if xt == "categorical" or shape.get("n_groups"):
            reject("histogram", "pooled histogram mixes groups; distribution differences invisible")
            return {"chart": "boxplot", "encoding": {"x": "group", "y": "value"},
                    "justification": "grouped numeric distribution → boxplot shows median/IQR/outliers per group",
                    "rejected": rejected, "checks": _base_checks(shape)}
        return {"chart": "histogram", "encoding": {"x": "value", "y": "count"},
                "justification": "single numeric variable → histogram for shape/mode/spread",
                "rejected": rejected, "checks": _base_checks(shape)}

    if intent == "relation":
        if xt == "numeric" and yt == "numeric":
            reject("line", "no inherent order on x; connecting points implies a false sequence")
            return {"chart": "scatter", "encoding": {"x": "x", "y": "y", "color": "group?"},
                    "justification": "numeric × numeric → scatter is the only encoding that shows raw relation",
                    "rejected": rejected, "checks": _base_checks(shape)}
        return {"chart": None, "justification": "relation intent needs numeric×numeric",
                "rejected": rejected, "checks": _base_checks(shape),
                "error": "unsupported shape for relation"}

    if intent == "composition":
        if ncat and ncat > MAX_PIE_CATEGORIES:
            reject("pie", f"{ncat} categories > {MAX_PIE_CATEGORIES}: angle/area comparison unreliable")
            return {"chart": "stacked_bar", "encoding": {"x": "group", "y": "share", "fill": "category"},
                    "justification": "many-category composition → stacked bar keeps length comparison",
                    "rejected": rejected, "checks": _base_checks(shape)}
        return {"chart": "pie_or_stacked_bar",
                "encoding": {"angle/length": "share", "fill": "category"},
                "justification": f"≤{MAX_PIE_CATEGORIES} categories, share emphasis → pie acceptable; "
                                 "stacked bar preferred if precise comparison matters",
                "rejected": rejected, "checks": _base_checks(shape)}

    if intent == "comparison":
        if yt != "numeric":
            return {"chart": None, "error": "comparison needs a numeric y",
                    "rejected": rejected, "checks": _base_checks(shape)}
        if ncat and ncat > MAX_BAR_CATEGORIES:
            return {"chart": "barh", "encoding": {"y": "category", "x": "statistic"},
                    "justification": f"{ncat} categories > {MAX_BAR_CATEGORIES}: horizontal bars keep labels readable",
                    "warnings": ["consider aggregating rare categories with an explicit 'other' rule in the cleaning ledger"],
                    "rejected": rejected, "checks": _base_checks(shape)}
        reject("pie", "comparison of unordered categories by angle/area is weaker than by length/position")
        return {"chart": "bar", "encoding": {"x": "category", "y": "statistic", "error": "sd|se|ci95"},
                "justification": "categorical × numeric comparison → bar with declared error representation",
                "rejected": rejected, "checks": _base_checks(shape)}

    return {"chart": None, "error": f"unknown intent {intent!r}; allowed: distribution/comparison/relation/trend/composition",
            "rejected": rejected, "checks": []}


def _base_checks(shape: dict) -> list[str]:
    c = ["axis types must match profile column types",
         "error bars must declare sd / se / ci95 explicitly",
         "n per group must be annotated when < 20"]
    if shape.get("has_time"):
        c.append("time axis must be true date scale, not categorical positions")
    return c


def validate_spec(spec: dict, profile: dict) -> dict:
    """核对 chart spec 与数据画像/口径一致。返回 {ok, problems[], warnings[]}。
    spec: {chart, axes: {x: {column, unit?}, y: {column, unit?}}, error?: "sd|se|ci95",
           series_units?: [...], baseline_truncated?: bool, uses_dual_axis?: bool, uses_3d?: bool}"""
    problems, warnings = [], []
    cols = profile.get("columns", {})
    hints = profile.get("unit_hints", {})
    for axis in ("x", "y"):
        ax = (spec.get("axes") or {}).get(axis)
        if not ax:
            problems.append(f"axis {axis} missing from spec")
            continue
        col = ax.get("column")
        if col and col not in cols:
            problems.append(f"axis {axis} column {col!r} not in data profile")
            continue
        if col:
            ctype = cols[col]["type"]
            if spec.get("chart") == "line" and axis == "x" and ctype not in ("date", "integer", "float"):
                problems.append(f"line chart x must be date/ordered numeric, got {ctype}")
            declared = ax.get("unit")
            hinted = hints.get(col)
            if declared and hinted and declared != hinted:
                problems.append(f"axis {axis} unit {declared!r} conflicts with header hint {hinted!r}")
    units = spec.get("series_units") or []
    if len({u for u in units if u}) > 1:
        problems.append(f"series share one axis but units differ {sorted(set(units))}: normalize or facet")
    chart = spec.get("chart")
    if chart in ("bar", "barh", "boxplot") and not spec.get("error") and chart != "boxplot":
        warnings.append("bar of means without declared error representation (sd/se/ci95) is not report-grade")
    if spec.get("error") not in (None, "sd", "se", "ci95"):
        problems.append(f"error representation {spec.get('error')!r} must be one of sd/se/ci95")
    if spec.get("baseline_truncated") and chart in ("bar", "barh"):
        problems.append("truncated baseline on bar chart exaggerates differences — bars must start at 0")
    if spec.get("uses_dual_axis"):
        warnings.append("dual axis invites spurious correlation reading; prefer faceting")
    if spec.get("uses_3d"):
        problems.append("3D encoding distorts values; not allowed for report-grade output")
    ncat = spec.get("n_categories")
    if chart == "bar" and ncat and ncat > MAX_BAR_CATEGORIES:
        warnings.append(f"{ncat} categories on a bar chart: switch to barh or aggregate")
    return {"ok": not problems, "problems": problems, "warnings": warnings,
            "rule": "every visual element must be traceable to a profile column and a declared unit"}


def _demo() -> int:
    # 选型规则
    s = select_chart({"intent": "trend", "x_type": "date", "y_type": "numeric"})
    assert s["chart"] == "line"
    s = select_chart({"intent": "comparison", "x_type": "categorical", "y_type": "numeric",
                      "n_categories": 3})
    assert s["chart"] == "bar" and any(r["chart"] == "pie" for r in s["rejected"])
    s = select_chart({"intent": "comparison", "x_type": "categorical", "y_type": "numeric",
                      "n_categories": 30})
    assert s["chart"] == "barh" and s["warnings"]
    s = select_chart({"intent": "composition", "n_categories": 9})
    assert s["chart"] == "stacked_bar"
    s = select_chart({"intent": "relation", "x_type": "numeric", "y_type": "numeric"})
    assert s["chart"] == "scatter"
    s = select_chart({"intent": "bogus"})
    assert s["chart"] is None and "error" in s
    # 一致性校验
    prof = {"columns": {"dose (mg)": {"type": "float"}, "group": {"type": "text"},
                        "day": {"type": "text"}},
            "unit_hints": {"dose (mg)": "mg"}}
    ok = validate_spec({"chart": "bar",
                        "axes": {"x": {"column": "group"}, "y": {"column": "dose (mg)", "unit": "mg"}},
                        "error": "se"}, prof)
    assert ok["ok"], ok
    bad = validate_spec({"chart": "bar",
                         "axes": {"x": {"column": "group"}, "y": {"column": "dose (mg)", "unit": "g"}},
                         "baseline_truncated": True}, prof)
    assert not bad["ok"] and any("unit" in p for p in bad["problems"])
    assert any("truncated" in p for p in bad["problems"])
    bad2 = validate_spec({"chart": "line",
                          "axes": {"x": {"column": "day"}, "y": {"column": "dose (mg)"}}},
                         prof)  # day 是 text，不是 date
    assert not bad2["ok"] and any("line chart x" in p for p in bad2["problems"])
    print(json.dumps({"demo": "charts", "trend": "line", "cmp3": "bar",
                      "cmp30": "barh", "comp9": "stacked_bar", "rel": "scatter",
                      "unit_conflict_detected": True, "text_x_line_rejected": True},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.chart shape.json profile.json out.json
    shape = json.load(open(sys.argv[1], encoding="utf-8"))
    selection = select_chart(shape)
    out = {"selection": selection}
    if len(sys.argv) > 3 and sys.argv[2] != "-":
        prof = json.load(open(sys.argv[2], encoding="utf-8"))
        if selection.get("chart") and selection.get("spec"):
            out["validation"] = validate_spec(selection["spec"], prof)
    json.dump(out, open(sys.argv[-1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"chart selection: {selection.get('chart')} -> {sys.argv[-1]}")
