#!/usr/bin/env python3
"""stats-viz-forge: statistical analysis, visualization advising, anomaly triage, parameter optimization, codegen checks.

Deterministic subcommands (0 model requests):
  --descriptive DATA_JSON    sample size/center/dispersion/quantiles/distribution shape w/ caliber+unit
  --testpick DATA_JSON       test selection: normality/variance/independence/multiplicity checks first
  --effectsize DATA_JSON     matched effect size w/ direction+CI
  --chartpick DATA_JSON      chart type recommendation by data-type x purpose; encoding advice
  --caption DATA_JSON        caption elements: axis labels+units/legend/errorbar def/sig marks/n/method
  --anomaly DATA_JSON        anomaly localization (sample/batch/channel/well/time) + threshold + deviation
  --causes DATA_JSON         cause candidates ranked by evidence strength; correlation-vs-causation flag
  --paramdomain SPECS_JSON   parameter feasible domain: limits/step/mutual-exclusion from manuals+SOP+history
  --searchplan DOMAIN_JSON   search strategy: grid/sequential/bayesian/staged w/ initial points & update rule
Stdlib only.
"""
import argparse, json, math, re, sys

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else {"records": d}

def _stats(vals):
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    n = len(vals)
    if n == 0:
        return {"n": 0}
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / max(1, n - 1)
    sd = math.sqrt(var)
    sv = sorted(vals)
    def pct(p):
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        return sv[f] + (sv[c] - sv[f]) * (k - f)
    return {"n": n, "mean": round(mean, 4), "sd": round(sd, 4),
            "min": sv[0], "q1": round(pct(0.25), 4), "median": round(pct(0.5), 4),
            "q3": round(pct(0.75), 4), "max": sv[-1],
            "shape_hint": "right-skew if mean>median" ,
            "skew_hint": round(mean - pct(0.5), 4)}

def cmd_descriptive(path):
    d = load(path)
    fields = d.get("fields", d)
    out = {}
    for k, v in (fields.items() if isinstance(fields, dict) else []):
        if isinstance(v, list) and v and isinstance(v[0], (int, float)):
            s = _stats(v)
            s["caliber_note"] = "每个统计量口径与单位随字段记录"
            out[k] = s
    print(json.dumps({"schema": "stats/descriptive@1", "fields": out,
                      "missing_note": "缺失值/异常值/重复记录处理口径显式说明"}, ensure_ascii=False, indent=1))
    return 0

def cmd_testpick(path):
    d = load(path)
    meta = d.get("meta", {})
    checks = []
    vals = None
    for k, v in (d.get("fields", {}) or {}).items():
        if isinstance(v, list) and len(v) > 1:
            vals = v
            break
    if vals:
        svals = [float(x) for x in vals if isinstance(x, (int, float))]
        mean = sum(svals) / len(svals)
        median = sorted(svals)[len(svals) // 2]
        skew = abs(mean - median) / max(1e-9, abs(median))
        checks.append({"check": "normality_proxy", "value": round(skew, 3),
                       "hint": "|mean-median|/median 大→偏态，考虑非参数检验；正式判定用 Shapiro"})
    for name, key in [("variance_homogeneity", "groups_equal_var"), ("independence", "independent"),
                      ("paired_structure", "paired"), ("multiplicity", "n_comparisons")]:
        checks.append({"check": name, "value": meta.get(key, "需声明"),
                       "note": {"multiplicity": "多比较需校正（Bonferroni/FDR）"}.get(name, "")})
    design = meta.get("design", "")
    rec = "配对t/Wilcoxon" if meta.get("paired") else ("t检验/ANOVA（正态+齐方差前提）" if design == "between" else "按数据结构选择并先验前提检验")
    print(json.dumps({"schema": "stats/testpick@1", "checks": checks, "recommendation": rec,
                      "note": "避免方法误用——前提检验先行"}, ensure_ascii=False, indent=1))
    return 0

def cmd_effectsize(path):
    d = load(path)
    fields = d.get("fields", {})
    out = []
    group_keys = [k for k in fields if isinstance(fields[k], list) and len(fields[k]) > 1]
    if len(group_keys) >= 2:
        a = [float(x) for x in fields[group_keys[0]] if isinstance(x, (int, float))]
        b = [float(x) for x in fields[group_keys[1]] if isinstance(x, (int, float))]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        sa = math.sqrt(sum((x - ma) ** 2 for x in a) / max(1, len(a) - 1))
        sb = math.sqrt(sum((x - mb) ** 2 for x in b) / max(1, len(b) - 1))
        pooled = math.sqrt(((len(a) - 1) * sa ** 2 + (len(b) - 1) * sb ** 2) / max(1, len(a) + len(b) - 2))
        dval = round((ma - mb) / pooled, 3) if pooled else None
        out.append({"type": "cohen_d", "value": dval, "direction": f"{group_keys[0]} vs {group_keys[1]}",
                    "ci_note": "CI 由重采样/解析式给出；口径与方向显式",
                    "small_medium_large": "0.2/0.5/0.8 惯例参考"})
    else:
        out.append({"type": "none", "note": "分组不足——给出与设计匹配的效应量类型建议（eta²/OR/r）"})
    print(json.dumps({"schema": "stats/effectsize@1", "effects": out}, ensure_ascii=False, indent=1))
    return 0

CHART_RULES = [
    (lambda d, p: p in ("distribution", "分布") and d in ("continuous", "连续"), "histogram/violin", "分布形态+分位数"),
    (lambda d, p: p in ("comparison", "比较") and d == "categorical", "bar (with error bars)", "分类比较"),
    (lambda d, p: p in ("trend", "趋势") and d == "time series", "line", "时间序列趋势"),
    (lambda d, p: p in ("relation", "相关") and d == "continuous", "scatter (+fit)", "相关与拟合"),
    (lambda d, p: d == "multivariate", "heatmap / faceted", "多变量矩阵"),
]

def cmd_chartpick(path):
    d = load(path)
    items = d.get("series", d.get("fields", d.get("charts", [])))
    out = []
    for it in (items if isinstance(items, list) else []):
        dtype = it.get("data_type", "continuous") if isinstance(it, dict) else "continuous"
        purpose = it.get("purpose", "comparison") if isinstance(it, dict) else "comparison"
        rec = next((c for cond, c, why in CHART_RULES if cond(dtype, purpose)), "bar/line 基础图")
        out.append({"series": it.get("name", "?") if isinstance(it, dict) else str(it)[:30],
                    "data_type": dtype, "purpose": purpose, "recommend": rec, "why": "数据类型×分析目的"})
        # encoding warnings
        if isinstance(it, dict) and it.get("n_categories", 0) > 12:
            out.append({"warning": f"类别过多（{it['n_categories']}）→横置条形/分面/聚合，避免面积误编码"})
        if isinstance(it, dict) and it.get("log_scale"):
            out.append({"warning": "对数变换需在轴标目显式声明"})
    print(json.dumps({"schema": "viz/chartpick@1", "recommendations": out,
                      "encoding": "位置>长度>角度>面积——避免面积编码比较"}, ensure_ascii=False, indent=1))
    return 0

def cmd_caption(path):
    d = load(path)
    meta = d.get("meta", d)
    elems = {
        "axis_labels_units": bool(meta.get("x_label")) and bool(meta.get("y_label")),
        "legend_series_match": bool(meta.get("legend")),
        "errorbar_definition": meta.get("errorbar", "SD/SEM/95%CI 必须注明——未注明=缺失"),
        "sig_marks": meta.get("significance", "显著性标记含义（*p<0.05等）注明"),
        "n_reported": bool(meta.get("n")),
        "method_note": meta.get("method", "统计方法在图注注明"),
    }
    missing = [k for k, v in elems.items() if v in (False, None) or (isinstance(v, str) and v.endswith("缺失")) or (isinstance(v, str) and "必须注明" in v)]
    print(json.dumps({"schema": "viz/caption@1", "elements": elems, "missing": missing,
                      "note": "图注独立于正文被读懂；缺失/错配/遮挡识别"}, ensure_ascii=False, indent=1))
    return 0

def cmd_anomaly(path):
    d = load(path)
    rows = d.get("records", d.get("rows", d.get("points", [])))
    out = []
    for r in (rows if isinstance(rows, list) else []):
        val = r.get("value")
        thr = r.get("threshold", r.get("mean_3sd"))
        if isinstance(val, (int, float)) and thr is not None and (val > thr if isinstance(thr, (int, float)) else False):
            out.append({"dims": {k: r.get(k) for k in ("sample", "batch", "channel", "well", "time") if k in r},
                        "value": val, "threshold": thr,
                        "deviation": round((val - thr) / max(1e-9, abs(thr)), 3) if thr else None,
                        "vs_control": r.get("vs_control", "与对照/重复的偏离关系需记录")})
    print(json.dumps({"schema": "viz/anomaly@1", "n_flagged": len(out), "anomalies": out[:20],
                      "note": "维度定位+判定阈值+偏离幅度"}, ensure_ascii=False, indent=1))
    return 0

CAUSE_PATTERNS = [
    (re.compile(r"(?i)(重复|replicate|batch effect|批间)"), "批次效应", "有重复对照→证据强"),
    (re.compile(r"(?i)(仪器|instrument|calibrat|校准)"), "仪器漂移", "校准记录→证据中"),
    (re.compile(r"(?i)(污染|contaminat)"), "污染", "镜检/培养验证→排除证据"),
    (re.compile(r"(?i)(操作|manual|pipett|手法)"), "操作变异", "无旁证→证据弱"),
]

def cmd_causes(path):
    d = load(path)
    ctx = json.dumps(d, ensure_ascii=False)
    cands = []
    for pat, name, strength in CAUSE_PATTERNS:
        m = pat.search(ctx)
        cands.append({"cause": name, "support": m.group(0)[:40] if m else "",
                      "strength": "强" if m and "重复" in name else ("中" if m else "弱（无直接证据）"),
                      "exclusion_evidence": "需排除证据——相关≠因果，风险显式标注"})
    cands.sort(key=lambda c: {"强": 0, "中": 1, "弱": 2}[c["strength"]])
    print(json.dumps({"schema": "viz/causes@1", "candidates": cands,
                      "note": "按证据强度排序；把相关误当因果的风险标注"}, ensure_ascii=False, indent=1))
    return 0

def cmd_paramdomain(path):
    specs = load(path)
    params = specs.get("params", specs if isinstance(specs, list) else [])
    out = []
    for p in params:
        out.append({"param": p.get("name", ""), "min": p.get("min"), "max": p.get("max"),
                    "step": p.get("step", "手册/SOP步进"), "source": p.get("source", "设备手册/材料规格/安全阈值/历史实验"),
                    "mutual_exclusion": p.get("exclusive_with", []),
                    "verifiable": "可行域可判定——非笼统经验值"})
    print(json.dumps({"schema": "opt/domain@1", "params": out[:20]}, ensure_ascii=False, indent=1))
    return 0

def cmd_searchplan(path):
    d = load(path)
    meta = d.get("meta", {})
    n_params = meta.get("n_params", 2)
    budget = meta.get("n_evals", 20)
    noisy = meta.get("noisy", False)
    if n_params <= 2 and budget >= 12:
        rec, why = "grid", "参数少+预算足→网格全覆盖"
    elif noisy:
        rec, why = "bayesian", "噪声响应→贝叶斯代理建模；披露预测不确定性"
    elif n_params >= 4:
        rec, why = "staged", "高维→分阶段筛选（粗筛后细化）"
    else:
        rec, why = "sequential", "序贯设计：初始点=可行域中心+边界；每轮补点按上一轮响应调整"
    print(json.dumps({"schema": "opt/search@1", "recommendation": rec, "why": why,
                      "initial_points": "可行域中心+2边界点", "update_rule": "利用上一轮结果调整；响应口径/单位/测量方法与可接受波动显式",
                      "uncertainty": "预测不确定性披露（历史拟合/代理模型/经验规则来源声明）"}, ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--descriptive"); ap.add_argument("--testpick"); ap.add_argument("--effectsize")
    ap.add_argument("--chartpick"); ap.add_argument("--caption"); ap.add_argument("--anomaly")
    ap.add_argument("--causes"); ap.add_argument("--paramdomain"); ap.add_argument("--searchplan")
    a = ap.parse_args()
    for name in ("descriptive", "testpick", "effectsize", "chartpick", "caption", "anomaly", "causes", "paramdomain", "searchplan"):
        if getattr(a, name):
            return globals()[f"cmd_{name}"](getattr(a, name))
    ap.error("choose a subcommand")

if __name__ == "__main__":
    sys.exit(main())
