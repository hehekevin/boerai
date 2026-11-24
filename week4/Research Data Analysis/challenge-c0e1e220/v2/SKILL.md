---
name: assumption-first-statistics
description: "Statistics with assumptions checked before tests: descriptive stats with explicit units, skew/kurtosis normality rule and Brown-Forsythe variance check, Welch/paired t, chi-square, correlation, effect sizes and 95% CIs, multiple-comparison notes, and plain-language interpretation that separates statistical from practical significance. Use when: a case asks whether groups differ, how large the effect is and how certain, on data with missing/outliers/duplicates. NOT for: experimental design, sample-size planning, p-hacking across methods, or reporting p values without effect size, CI and assumption evidence."
---

# 统计分析与结果解读：先校验前提，再谈 p 值；效应量与区间必须同行

数字之外才是本题：缺失不当 0、异常先进诊断、重复先去重、三组不塞两样本 t、非正态小样本不套参数法、报告不只有 p。本技能强制"清洗账本 → 假设检查 → 检验选择 → 效应量+CI → 解释"的顺序：dakit.stats 精确计算（t/F 经不完全 β、χ² 经不完全 γ，demo 对教科书值断言），方法选择与解释由 Agent 依据 assumptions 段完成并写明依据。

## 何时使用
* 用例给出实验测量/随访/问卷/数据库导出数据，问"两组有没有差异、差异多大、多确定"。
* 判定标准：统计量/自由度/p/效应量/区间数值正确；方法与分布、样本结构、设计匹配；覆盖缺失/异常/重复/统计假设/图表选择/代码运行/数据库字段七类检查点；可复跑。

**不适用**：实验方案设计、样本量估算、论文写作；用反复换方法凑显著性。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（数据表/SQLite、数据字典、设计说明）。

## 输出（写入 /app/output）
`result.json`（case_id + output_contract 全字段 + status/sources/uncertainty/changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" tables  --work "$WORK"
python -m dakit.profile "$WORK/tables.json" "$WORK/profile.json"
python -m dakit.clean   "$WORK/tables_0.json" "$WORK/rules.json" "$WORK/clean.json"
```

**第 1 步 统计前置。** 清洗账本（缺失/异常/重复）必须先于任何统计；进入统计的 n 必须等于账本 after_n，样本量凭空变大是最典型的失败。

**第 2 步 假设检查（先于检验）。** 在 `stats_spec.json` 的 `assumptions.groups` 放入各组数据、`n_tests_planned` 填计划检验数：`python -m dakit.stats stats_spec.json $WORK/stats.json` 输出每组正态性提示（偏度/峰度规则）、方差齐性（Brown–Forsythe）、样本量警告、多重比较（Bonferroni α）。

**第 3 步 按前提选检验。** 方差齐性可疑 → Welch（默认就是 Welch，不 pooled）；配对结构 → paired_t；分类关联 → χ²（期望 <5 格子 >20% 时引擎警告改用精确检验/合并类别）；相关 → pearson 并提示先看散点。三组及以上不塞两样本 t——先在 assumptions 写明设计，需要时按多组设计另述（本引擎聚焦两组/配对/列联/相关，超出部分写 uncertainty）。

**第 4 步 效应量与区间。** Welch t 自动附 Cohen's d 与均值差 95%CI；ci_mean 给单组 CI；解释必须区分统计显著与实际意义（p 小 ≠ 效应大），CI 不读作个体取值范围（引擎 note 强制声明）。

**第 5 步 报告回填与解释。** 模板占位符只许来自 stats.json；解释段由 Agent 写，必须引用 assumptions 结果（如"Brown–Forsythe p=0.32，方差齐性可接受，故报告 Welch 结果"），标注剩余不确定性与需人工确认环节。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact stats_json=$WORK/stats.json \
    --artifact data=$WORK/clean_ledger.json
```

## 本题判据对齐（题面原文 → 机制）
1. **"正态性和方差齐性从未检验，非正态的小样本照样套参数方法"** → assumptions 段强制先跑；偏度/峰度规则与 Brown–Forsythe 结果随 stats.json 交付。
2. **"报告里只有 p 值，没有效应量、没有置信区间"** → 检验输出结构自带 cohens_d 与 ci95_diff；报告模板校验拒绝无出处的数字。
3. **"多重比较没有校正"** → n_tests_planned 触发 Bonferroni α 与"不得按 p 值事后选方法"提示。
4. **"缺失值被当成 0、重复记录没有去重，样本量凭空变大"** → 统计输入必须来自 clean 账本输出，n 与账本 after_n 一致（e2e 机检）。

## 交付物
* `stats.json`（describe + tests + assumptions）、`clean_ledger.json`、`report.md`（含解释段与近似披露）、`report_mapping.json`。

## 证据与审计规则
* 统计数值为精确实现并对教科书值断言：Student 睡眠数据配对 t=4.0621、df=9、p=0.002833；R 文档 Welch 例 t=-5.4349、df=21.982、p=1.855e-05；95%CI [0.7001, 2.4599]——复算可对照。
* 方法选择依据必须引用 assumptions 的具体数值，不接受"按惯例"。
* 数据不足（n<2、零方差、期望格过小）时引擎拒绝或警告，如实报告而不是硬算。
* 解释超出证据范围（因果、机理）视为违规；拿不准写 uncertainty 并降级 partial。

## 方法与近似（报告方法节必须复述）
* 正态性：偏度/峰度经验规则（|skew|≤2、|excess kurtosis|≤7），**非正式检验**，n<20 功效低，仅作提示并建议 Q-Q 图；正式结论需更大样本或精确检验。
* 方差齐性：Brown–Forsythe（中位数中心化 Levene），近似检验。
* Welch 自由度：Welch–Satterthwaite 近似；t 分位数：二分反解 CDF（精度 ~1e-8）。
* 多重比较：Bonferroni 偏保守；预声明主要终点优先。

## 异常处理
| 情况 | 处置 |
|---|---|
| 样本量不足（n<8） | 警告检验功效极低；结果标注或降级 partial |
| 组内方差为零 | 引擎拒绝检验并说明（t 无定义） |
| 缺失比例过高 | 回清洗环节重估口径；不在高缺失列上硬算 |
| 假设不成立 | 换 Welch/非参数路线并写明依据；不得默默套参数法 |
| 字段单位不明 | 先回数据字典；单位未明前不出效应量解释 |
| 数据库连接失败 | dbrun 保留原始错误；partial + uncertainty |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：stats demo 断言教科书数值与两类假设检查行为；另有 6 个模块 demo + 一次端到端（含"n 必须等于账本 after_n"机检）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-c0e1e220/v2
