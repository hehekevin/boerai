---
name: research-data-analysis-core
description: "General-track research data analysis: profile → field alignment → ledgered cleaning → assumption-checked statistics → chart selection → report backfill, with every intermediate saved as recomputable JSON. Use when: a fixed research case asks for cleaning, statistics, visualization, code execution, multi-step analysis or database querying on real snapshots. NOT for: experimental design, mechanistic claims, or deliverables whose numbers cannot be traced to saved stats JSON."
---

# 科研数据分析总课题：给出结果，也保留计算依据

本技能覆盖总课题的核心链：数据导入与字段对齐、清洗与异常处理、统计分析与假设校验、可视化选型、报告数字回填。确定性簿记全部在 dakit 引擎（纯标准库）；语义判断由 Agent 完成并落盘。3 个固定案例（UCI Concrete 1030 / Iris 150 bezdek 变体 / Wine 178 快照与 SQLite 库）按同一条流水线处理，不预制答案。

## 何时使用
* 固定案例要求对真实数据快照完成清洗、统计、可视化、代码执行、多步骤分析或数据库查询。
* 判定标准：核心任务完成且成果可用；事实/计算/操作结果准确；关键对象、字段、证据、输出格式覆盖；结果可追溯到原始材料与实际执行过程。

**不适用**：实验设计、机理解释、论文写作；无法回算的数字与"截图式"结论。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（CSV 快照、SQLite 数据库、数据字典、约束说明）。

## 输出（写入 /app/output）
`result.json`（case_id + output_contract 全字段 + status/sources/uncertainty/changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" tables  --work "$WORK"
```

1. **画像** `python -m dakit.profile $WORK/tables.json $WORK/profile.json`——类型、缺失率、单位提示、候选主键、跨表连接候选；数据库案例先 `python -m dakit.dbrun introspect <db> $WORK/schema.json`。
2. **对齐** `python -m dakit.align spec.json $WORK/align.json`——多来源列映射带置信度，未解析字段显式列出。
3. **清洗** 规则写 `$WORK/rules.json` 后 `python -m dakit.clean table.json rules.json $WORK/clean.json`——账本含受影响行 id、前后行数、分布影响。
4. **统计** `python -m dakit.stats stats_spec.json $WORK/stats.json`——先假设检查（偏度/峰度规则、Brown–Forsythe、样本量、多重比较提示）再选检验，输出效应量与 CI。
5. **图表** `python -m dakit.charts shape.json - $WORK/chart_spec.json`——图型+理由+被否决项；`validate_spec` 核对轴/单位/误差表示。
6. **报告** `python -m dakit.report tpl.md stats.json report.md mapping.json`——占位符只许来自 stats.json。
7. **收尾**：

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact stats_json=$WORK/stats.json \
    --artifact data=$WORK/clean_ledger.json
```

## 本题判据对齐
1. **任务完成度** → 五段流水线在同一标准库引擎上串通，逐步落盘可重跑。
2. **结果正确性** → 统计为精确实现（不完全 β/γ），demo 断言教科书值（配对 t=4.0621/p=0.002833；Welch t=-5.4349/df=21.982；χ²=6.6516/p=0.00991）。
3. **结果完整性** → profile→clean→stats→chart→report 全链产物 + result.json 覆盖 output_contract 全键。
4. **结果可核验性** → 账本行 id、SQL 原文、占位符→JSON 路径映射，第三方可复算。

## 交付物
* `report.md`、`stats.json`、`clean_ledger.json`、`cleaned.csv`、`rules.json`、`profile.json`（数据库案例加 `schema.json`、`q*.csv`）。

## 证据与审计规则
* 清洗不静默丢行；报告数字必须可回算；近似方法随结果披露。
* 材料缺失、无法判断、运行失败分别写入 uncertainty 并降级 status，不混为一谈。
* 正式案例答案不预制：本仓库只含引擎与合成示例，案例中出现的数字全部当场计算。

## 方法与近似
正态性=偏度/峰度经验规则（非正式检验，n<20 功效低，建议 Q-Q 图确认）；方差齐性=Brown–Forsythe 近似；Welch df=Satterthwaite 近似；t 分位数=二分反解 CDF。以上限度在代码注释与本文件同时声明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 输入结构未知 | probe 先读真实键与文件清单，不猜 schema |
| 空表/缺列/类型不符 | profile warnings + 引擎拒绝运行并给原因，status=partial |
| 除零/方差为 0/样本不足 | stats 显式报错而非产出伪 p 值 |
| 数据库连接失败 | dbrun 保留原始错误，不建空库，不静默换库 |
| 报告占位符无法追溯 | report.fill 直接失败并列出缺失路径 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：7 模块 demo + 端到端（合成 CSV → probe/extract/tables/profile/clean/stats/charts/report/emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-95620c56/v2
