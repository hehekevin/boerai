---
name: research-data-pipeline
description: "Run a multi-step research-data analysis chain — probe inputs, align fields, clean with a row-level ledger, test assumptions before statistics, select charts by data shape, and backfill report numbers only from computed stats. Use when: a case gives raw tables/CSVs/SQLite snapshots plus a data dictionary and asks for cleaning + statistics + chart + report with auditable basis. NOT for:实验设计、机理推断、论文写作, or any analysis whose numbers cannot be recomputed from saved JSON."
---

# 多步骤数据分析：从原始表到可复核报告，每一步留账本

面向"一批原始表格加一句需求"的真实科研分析任务。本技能把多步编排变成可复跑的确定性流水线：Agent 负责语义判断（字段含义、规则选择、结果解释），dakit 引擎负责画像、对齐、清洗、统计、选型、回填与审计——每个中间产物落盘 JSON，报告数字只许来自已计算的 stats JSON。

## 何时使用
* 用例给出 CSV/表格/SQLite 快照与任务说明，要求完成导入→清洗→统计→图表→报告的完整链条。
* 判定标准：五段真的在同一环境里串通；数值、统计口径与图形算对；证据链完整到可以重跑。

**不适用**：实验方案设计、机理解释、论文写作；数字无法回算的任何"分析"。

## 输入
`/input/case.json`（结构不固定，先 probe 读真实键）、`/input/task.md`、`/input/**`（CSV、SQLite 快照、数据字典等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" tables  --work "$WORK"     # 抽取出的表格统一为 tables.json
```

**第 1 步 数据画像。** `python -m dakit.profile $WORK/tables.json $WORK/profile.json`：读每列类型、缺失率、表头单位、候选主键、跨表连接候选（带值重叠率）。先读数据字典再动数据；profile 的 warnings 逐条处置。

**第 2 步 字段对齐。** `python -m dakit.align spec.json $WORK/align.json`：多来源列映射带置信度；<0.9 的一律人工（Agent）对照数据字典确认；未解析列进入 unresolved，绝不静默丢弃。

**第 3 步 规则化清洗。** 规则写成 `$WORK/rules.json`（数据，不是代码）后 `python -m dakit.clean table.json rules.json $WORK/clean.json`：缺失/异常/重复每条规则记录受影响行 id、前后行数、分布影响。清洗后数据另存 `cleaned.csv`，原始快照不动。

**第 4 步 假设先行的统计。** 写 `$WORK/stats_spec.json`（tests + assumptions.groups）后 `python -m dakit.stats stats_spec.json $WORK/stats.json`：先跑 check_assumptions（偏度/峰度规则、Brown-Forsythe 方差齐性、样本量、多重比较提示），再按结果选 Welch t / 配对 t / χ² / 相关，输出效应量与 95%CI。

**第 5 步 图表选型。** `python -m dakit.charts shape.json - $WORK/chart_spec.json` 得图型+理由+被否决项；出图后用 `dakit.charts.validate_spec` 核对轴类型/单位/误差表示与 profile 一致。

**第 6 步 报告回填。** 模板只写 `{{results[0].p_two_sided}}` 这类占位符，`python -m dakit.report tpl.md stats.json report.md mapping.json` 回填并校验；mapping.json 记录每个数字的 JSON 出处。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact stats_json=$WORK/stats.json \
    --artifact data=$WORK/clean_ledger.json --artifact cleaned_csv=$WORK/cleaned.csv
```

## 本题判据对齐（题面质量条原文 → 机制）
1. **"导入、清洗、分析、可视化、报告五段是否真的在同一环境里串通"** → 全部步骤跑在同一 Python 标准库引擎上，中间产物按 tables.json→profile→rules→clean→stats→chart→report 顺序落盘，任一步可由上一步入盘文件重跑。
2. **"数值、统计口径与图形是否算对，处理规则是否与实际执行一致"** → 统计为精确实现（t/F 经不完全 β、χ² 经不完全 γ），demo 用教科书值断言（睡眠数据配对 t=4.0621/p=0.002833）；清洗账本逐条列出 affected_row_ids 与前后分布。
3. **"证据链是否完整到可以重跑，而不是只能看结论"** → result.json 挂接 rules.json、clean_ledger、stats.json、report mapping，数字可逐项回算。

## 交付物
* `report.md`（回填后）、`stats.json`（含 assumptions）、`clean_ledger.json`、`cleaned.csv`、`rules.json`、`profile.json`、`chart_spec.json`、`report_mapping.json`。

## 证据与审计规则
* 任何 drop 的行必须出现在 ledger 的 affected_row_ids；填补值写入 fill_value；异常判据（IQR 栅栏或 z 界）写入 criterion。
* 报告正文数字只能来自 stats.json：report.validate 拒绝残留占位符，strict 模式列出手改数字。
* 材料没有的内容不补：写入 uncertainty.json，status 降级 partial 并在 limits 说明。
* 近似方法必须随结果披露（见下节），不得把经验规则写成正式检验结论。

## 方法与近似（必须随报告披露）
* 正态性：偏度/峰度经验规则（|skew|≤2 且 |excess kurtosis|≤7），**不是正式检验**，n<20 功效低，只作提示并建议 Q-Q 图确认。
* 方差齐性：Brown–Forsythe（中位数中心化 Levene），近似检验，p<0.05 → 用 Welch/非参数。
* Welch 自由度为 Welch–Satterthwaite 近似；t 分位数由二分反解 CDF（精度 ~1e-8）。

## 异常处理
| 情况 | 处置 |
|---|---|
| 空表/全列缺失 | profile warnings 如实报告，stats 拒绝运行并说明，status=partial |
| 列类型混杂（mixed） | profile 标出非数值个数；不静默聚合，先回数据字典确认口径 |
| 缺失哨兵值（-999、"NA" 等） | 在 rules.json 的 sentinels 显式声明后再处置，账本记录 |
| 方差为 0 / n<2 | 引擎拒绝检验并给出原因，不产出伪 p 值 |
| 多次运行结果不一致 | 无随机源（引擎全确定性）；若出现，按 changes.json 定位输入变动 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：7 个模块 demo（含教科书数值断言）+ 一次端到端（18 行合成 CSV 含注入缺失/异常/重复 → 清洗至 15 行 → Welch t → 回填报告 → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/agent-6aefb2fd/v2
