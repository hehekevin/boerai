"""统计：描述统计 + 推断统计 + 假设检查。仅标准库（math/statistics），无 pandas/numpy。

分布函数实现（Numerical Recipes 标准算法，精确实现，非查表）：
- t 分布 CDF：经正则化不完全 β 函数 I_x(a,b)（连分式 betacf 求值）
- F 分布 CDF：同为不完全 β 函数
- χ² 分布 CDF：经正则化下不完全 γ 函数 P(a,x)（级数/连分式分段）

近似及其限度（与 SKILL.md 一致，必须披露）：
- 正态性：偏度/峰度经验规则（|skew|>2 或 |excess kurtosis|>7 判非正态，
  参照 West, Finch & Curran 1995 常用阈值）。这是经验规则不是正式检验；
  小样本（n<20）功效低，结果只作"提示"，结论写入 assumptions[].note。
- 方差齐性：Brown–Forsythe（中位数中心化 Levene）——对非正态比经典
  Levene 稳健，但仍是近似检验，p 值经 F 分布求得。
- Welch t 的自由度用 Welch–Satterthwaite 近似。
"""
from __future__ import annotations

import json
import math
import statistics
import sys

# ------------------------------------------------------------- 特殊函数
def _betacf(a: float, b: float, x: float) -> float:
    """不完全 β 函数的连分式部分（Numerical Recipes §6.4）。"""
    MAXIT, EPS, FPMIN = 200, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """正则化不完全 β 函数 I_x(a,b)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """Student t 分布 CDF。"""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    ib = betai(df / 2.0, 0.5, x)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def f_cdf(f: float, d1: float, d2: float) -> float:
    """F 分布 CDF。"""
    if f <= 0:
        return 0.0
    return betai(d1 / 2.0, d2 / 2.0, (d1 * f) / (d1 * f + d2))


def _gammaincc(a: float, x: float) -> float:
    """正则化上不完全 γ 函数 Q(a,x)（NR §6.2：x<a+1 用级数求 P 取补，否则连分式）。"""
    if x <= 0:
        return 1.0
    EPS, MAXIT, FPMIN = 3e-14, 200, 1e-300
    if x < a + 1.0:
        ap, s, delta = a, 1.0 / a, 1.0 / a
        for _ in range(MAXIT):
            ap += 1.0
            delta *= x / ap
            s += delta
            if abs(delta) < abs(s) * EPS:
                break
        p = s * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return 1.0 - p
    b, c, d = x + 1.0 - a, 1.0 / FPMIN, 1.0 / (x + 1.0 - a if abs(x + 1.0 - a) > FPMIN else FPMIN)
    h = d
    for i in range(1, MAXIT + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_cdf(x: float, df: float) -> float:
    """χ² 分布 CDF。"""
    return 1.0 - _gammaincc(df / 2.0, x / 2.0)


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ------------------------------------------------------------- 描述统计
def describe(values: list[float], label: str = "") -> dict:
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return {"label": label, "n": 0, "error": "no numeric values"}
    out = {"label": label, "n": n, "mean": statistics.fmean(vals)}
    if n > 1:
        out["sd"] = statistics.stdev(vals)
        out["se"] = out["sd"] / math.sqrt(n)
    out["median"] = statistics.median(vals)
    if n >= 4:
        q = statistics.quantiles(vals, n=4)
        out["q1"], out["q3"] = q[0], q[2]
        out["iqr"] = q[2] - q[0]
    out["min"], out["max"] = min(vals), max(vals)
    if n > 2 and out.get("sd"):
        m = out["mean"]
        s = out["sd"]
        out["skew"] = sum((v - m) ** 3 for v in vals) / n / s ** 3
        out["kurtosis_excess"] = sum((v - m) ** 4 for v in vals) / n / s ** 4 - 3.0
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}


# ------------------------------------------------------------- 推断统计
def t_test_one_sample(values: list[float], mu0: float = 0.0) -> dict:
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    assert n >= 2, "one-sample t needs n>=2"
    mean, sd = statistics.fmean(vals), statistics.stdev(vals)
    assert sd > 0, "zero variance: t undefined"
    t = (mean - mu0) / (sd / math.sqrt(n))
    df = n - 1
    p = 2 * (1 - t_cdf(abs(t), df))
    return {"test": "one_sample_t", "n": n, "mean": round(mean, 6), "sd": round(sd, 6),
            "mu0": mu0, "t": round(t, 6), "df": df, "p_two_sided": round(p, 6)}


def t_test_welch(x: list[float], y: list[float]) -> dict:
    """Welch 两样本 t（不假设方差齐）；df 用 Welch–Satterthwaite 近似。"""
    xa = [float(v) for v in x if v is not None]
    ya = [float(v) for v in y if v is not None]
    assert len(xa) >= 2 and len(ya) >= 2, "Welch t needs n>=2 per group"
    m1, m2 = statistics.fmean(xa), statistics.fmean(ya)
    v1, v2 = statistics.variance(xa), statistics.variance(ya)
    n1, n2 = len(xa), len(ya)
    assert v1 + v2 > 0, "zero variance in both groups: t undefined"
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (m1 - m2) / se
    num = (v1 / n1 + v2 / n2) ** 2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = num / den
    p = 2 * (1 - t_cdf(abs(t), df))
    # Cohen's d（合并 SD）与均值差 CI
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)) if n1 + n2 > 2 else float("nan")
    d = (m1 - m2) / sp if sp else float("nan")
    tcrit = _t_ppf(0.975, df)
    diff = m1 - m2
    return {"test": "welch_two_sample_t", "n1": n1, "n2": n2,
            "mean1": round(m1, 6), "mean2": round(m2, 6), "diff": round(diff, 6),
            "t": round(t, 6), "df": round(df, 3), "p_two_sided": round(p, 6),
            "cohens_d": round(d, 6),
            "ci95_diff": [round(diff - tcrit * se, 6), round(diff + tcrit * se, 6)]}


def t_test_paired(x: list[float], y: list[float]) -> dict:
    assert len(x) == len(y), "paired t requires equal lengths"
    diffs = [float(a) - float(b) for a, b in zip(x, y) if a is not None and b is not None]
    rep = t_test_one_sample(diffs, 0.0)
    rep["test"] = "paired_t"
    rep["n_pairs"] = rep.pop("n")
    return rep


def _t_ppf(p: float, df: float) -> float:
    """t 分布分位数：二分法反解 CDF（单调，足够稳健；精度 ~1e-8）。"""
    lo, hi = -1e6, 1e6
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ci_mean(values: list[float], conf: float = 0.95) -> dict:
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    assert n >= 2, "CI needs n>=2"
    mean, sd = statistics.fmean(vals), statistics.stdev(vals)
    tcrit = _t_ppf(1 - (1 - conf) / 2, n - 1)
    half = tcrit * sd / math.sqrt(n)
    return {"estimate": round(mean, 6), "conf": conf,
            "ci": [round(mean - half, 6), round(mean + half, 6)], "n": n,
            "note": "CI 是估计量的不确定区间，不是个体取值范围"}


def chi2_independence(table: list[list[int]]) -> dict:
    """χ² 独立性检验。期望 <5 的格子超过 20% 时给出 Fisher/合并类别提示。"""
    r, c = len(table), len(table[0])
    assert r >= 2 and c >= 2 and all(len(row) == c for row in table)
    rowsum = [sum(row) for row in table]
    colsum = [sum(table[i][j] for i in range(r)) for j in range(c)]
    n = sum(rowsum)
    assert n > 0
    chi2, n_small = 0.0, 0
    for i in range(r):
        for j in range(c):
            e = rowsum[i] * colsum[j] / n
            if e < 5:
                n_small += 1
            if e > 0:
                chi2 += (table[i][j] - e) ** 2 / e
    df = (r - 1) * (c - 1)
    p = 1 - chi2_cdf(chi2, df)
    warn = ""
    if n_small / (r * c) > 0.2:
        warn = f"{n_small}/{r * c} cells have expected <5: χ² approximation unreliable; use exact test or merge categories"
    return {"test": "chi2_independence", "table_shape": [r, c], "n": n,
            "chi2": round(chi2, 6), "df": df, "p": round(p, 6),
            "expected_lt5_cells": n_small, "warning": warn}


def pearson(x: list[float], y: list[float]) -> dict:
    pairs = [(float(a), float(b)) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    assert n >= 3, "correlation needs n>=3"
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    assert sxx > 0 and syy > 0, "zero variance: r undefined"
    r = sxy / math.sqrt(sxx * syy)
    t = r * math.sqrt((n - 2) / max(1e-300, 1 - r * r))
    p = 2 * (1 - t_cdf(abs(t), n - 2))
    return {"test": "pearson", "n": n, "r": round(r, 6), "t": round(t, 6),
            "df": n - 2, "p_two_sided": round(p, 6),
            "note": "pearson assumes linearity & bivariate normality; inspect scatter first"}


# ------------------------------------------------------------- 假设检查
def normality_rule(values: list[float]) -> dict:
    """偏度/峰度经验规则（近似，限度见模块 docstring）。|skew|>2 或 |exkurt|>7 → 非正态提示。"""
    d = describe(values)
    n = d.get("n", 0)
    if n < 3:
        return {"method": "skew_kurtosis_rule", "n": n, "verdict": "undetermined",
                "note": "n<3: cannot assess"}
    sk, ku = abs(d.get("skew", 0.0)), abs(d.get("kurtosis_excess", 0.0))
    ok = sk <= 2.0 and ku <= 7.0
    note = ("rule-of-thumb (|skew|<=2, |excess kurtosis|<=7); NOT a formal test; "
            "low power for n<20 — treat as a hint, confirm with Q-Q plot")
    if n < 20:
        note = "n<20, low power. " + note
    return {"method": "skew_kurtosis_rule", "n": n, "skew": d.get("skew"),
            "kurtosis_excess": d.get("kurtosis_excess"),
            "verdict": "plausibly_normal" if ok else "non_normal_flag", "note": note}


def levene_brown_forsythe(groups: list[list[float]]) -> dict:
    """方差齐性：中位数中心化 Levene（Brown–Forsythe），对非正态稳健；p 经 F 分布（近似）。"""
    gs = [[float(v) for v in g if v is not None] for g in groups]
    assert len(gs) >= 2 and all(len(g) >= 2 for g in gs), "need >=2 groups with n>=2"
    z = [[abs(v - statistics.median(g)) for v in g] for g in gs]
    allz = [v for g in z for v in g]
    k, n = len(gs), len(allz)
    grand = statistics.fmean(allz)
    ss_between = sum(len(g) * (statistics.fmean(g) - grand) ** 2 for g in z)
    ss_within = sum((v - statistics.fmean(g)) ** 2 for g in z for v in g)
    if ss_within <= 0:
        return {"test": "levene_brown_forsythe", "verdict": "undetermined",
                "note": "zero within-group deviation variance"}
    f = (ss_between / (k - 1)) / (ss_within / (n - k))
    p = 1 - f_cdf(f, k - 1, n - k)
    return {"test": "levene_brown_forsythe", "k": k, "n": n, "F": round(f, 6),
            "df": [k - 1, n - k], "p": round(p, 6),
            "verdict": "equal_var_plausible" if p >= 0.05 else "unequal_var_flag",
            "note": "approximate test; p<0.05 → prefer Welch/nonparametric over pooled methods"}


def check_assumptions(groups: dict[str, list[float]], n_tests_planned: int = 1) -> dict:
    """汇总假设检查：各组正态性提示、方差齐性、样本量、多重比较。"""
    out = {"groups": {}, "variance": None, "sample_size": [], "multiple_comparison": None}
    for name, vals in groups.items():
        out["groups"][name] = normality_rule(vals)
        n = len([v for v in vals if v is not None])
        if n < 8:
            out["sample_size"].append(f"{name}: n={n} < 8, any test has very low power")
        elif n < 20:
            out["sample_size"].append(f"{name}: n={n} < 20, normality checks unreliable; report exact n")
    if len(groups) >= 2:
        out["variance"] = levene_brown_forsythe(list(groups.values()))
    if n_tests_planned > 1:
        out["multiple_comparison"] = {
            "n_tests": n_tests_planned,
            "bonferroni_alpha": round(0.05 / n_tests_planned, 6),
            "note": "multiple testing inflates family-wise error; pre-declare primary endpoint "
                    "or adjust alpha (Bonferroni shown); never pick the method post-hoc by p value"}
    return out


def _demo() -> int:
    # —— 分布函数自检（对照已知值）——
    assert abs(normal_cdf(1.959964) - 0.975) < 1e-5
    assert abs(t_cdf(1.96, 100000) - 0.975) < 5e-4          # 大 df 时 t→N(0,1)
    assert abs(t_cdf(2.2281, 10) - 0.975) < 5e-4            # t(10) 双侧 0.05 临界 2.2281
    assert abs(chi2_cdf(3.8414588, 1) - 0.95) < 1e-5        # χ²(1) 0.95 临界 3.8415
    assert abs(f_cdf(4.2565, 5, 10) - 0.975) < 1e-3         # F(5,10) 0.975 临界 4.2565
    # —— 教科书数值：Student(1908) 睡眠数据配对 t —— R: t=4.0621, df=9, p=0.002833
    extra = [1.2, 2.4, 1.3, 1.3, 0.0, 1.0, 1.8, 0.8, 4.6, 1.4]
    rep = t_test_one_sample(extra, 0.0)
    assert abs(rep["t"] - 4.0621) < 1e-3, rep
    assert 0.0025 < rep["p_two_sided"] < 0.0032, rep
    # —— Welch t 已知值（R 文档示例 t.test(1:10, y=c(7:20))）：
    #    Welch t = -5.4349, df = 21.982, p = 1.855e-05
    x = list(range(1, 11))
    y = list(range(7, 21))
    w = t_test_welch(x, y)
    assert abs(w["t"] - (-5.4349)) < 1e-3, w
    assert abs(w["df"] - 21.982) < 0.01, w
    assert abs(w["p_two_sided"] - 1.855e-05) < 5e-7, w
    # —— χ² 2x2 手工核算：[[10,5],[3,12]]，期望全为 6.5/8.5，
    #    χ² = 2×(12.25/6.5 + 12.25/8.5) = 6.6516，df=1，p ≈ 0.00991
    c = chi2_independence([[10, 5], [3, 12]])
    assert abs(c["chi2"] - 6.6516) < 1e-3, c
    assert abs(c["p"] - 0.009907) < 5e-4, c
    # —— Pearson：完全线性 r=1；已知数据 r≈0.9945
    r1 = pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert abs(r1["r"] - 1.0) < 1e-9
    r2 = pearson([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                 [1.1, 1.9, 3.2, 3.8, 5.1, 5.9, 7.2, 7.8, 9.1, 9.9])
    assert 0.99 < r2["r"] < 1.0 and r2["p_two_sided"] < 1e-6, r2
    # —— 假设检查：方差悬殊的两组应被 Levene 标出
    g_small_var = [10.0 + 0.1 * ((i * 7) % 3 - 1) for i in range(30)]
    g_big_var = [10.0 + 3.0 * ((i * 13) % 5 - 2) for i in range(30)]
    lv = levene_brown_forsythe([g_small_var, g_big_var])
    assert lv["p"] < 0.01 and lv["verdict"] == "unequal_var_flag", lv
    lv2 = levene_brown_forsythe([g_small_var, [v + 50 for v in g_small_var]])
    assert lv2["p"] > 0.5, lv2
    nm = normality_rule([1.0] * 3 + [2.0] * 30 + [3.0] * 3)
    assert nm["verdict"] in ("plausibly_normal", "non_normal_flag")
    nm2 = normality_rule([1, 1, 1, 1, 1, 1, 1, 1, 1, 50.0])
    assert nm2["verdict"] == "non_normal_flag", nm2
    asm = check_assumptions({"A": x, "B": y}, n_tests_planned=3)
    assert asm["multiple_comparison"]["bonferroni_alpha"] == round(0.05 / 3, 6)
    ci = ci_mean(extra)
    # 配对睡眠数据 95%CI R: [0.7001, 2.4599]
    assert abs(ci["ci"][0] - 0.70) < 0.02 and abs(ci["ci"][1] - 2.46) < 0.02, ci
    print(json.dumps({"demo": "stats", "sleep_paired_t": rep["t"], "sleep_p": rep["p_two_sided"],
                      "welch_t": w["t"], "welch_p": w["p_two_sided"],
                      "chi2": c["chi2"], "chi2_p": c["p"],
                      "levene_p_unequal": lv["p"], "ci95_sleep": ci["ci"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.stats spec.json out.json
    # spec: {"tests":[{"kind":"welch_t","x":[..],"y":[..]} | {"kind":"chi2","table":[[..]]} |
    #        {"kind":"pearson","x":[..],"y":[..]} | {"kind":"describe","values":[..],"label":..}],
    #        "assumptions": {"groups": {"A":[..],"B":[..]}, "n_tests_planned": k}?}
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    results = []
    for t in spec.get("tests", []):
        kind = t["kind"]
        if kind == "describe":
            results.append(describe(t["values"], t.get("label", "")))
        elif kind == "one_sample_t":
            results.append(t_test_one_sample(t["values"], t.get("mu0", 0.0)))
        elif kind == "welch_t":
            results.append(t_test_welch(t["x"], t["y"]))
        elif kind == "paired_t":
            results.append(t_test_paired(t["x"], t["y"]))
        elif kind == "chi2":
            results.append(chi2_independence(t["table"]))
        elif kind == "pearson":
            results.append(pearson(t["x"], t["y"]))
        else:
            results.append({"error": f"unknown test kind {kind!r}"})
    out = {"results": results}
    if spec.get("assumptions"):
        a = spec["assumptions"]
        out["assumptions"] = check_assumptions(a["groups"], a.get("n_tests_planned", len(results)))
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ran {len(results)} analyses -> {sys.argv[2]}")
