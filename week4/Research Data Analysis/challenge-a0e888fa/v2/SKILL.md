---
name: cleaning-ledger
description: "Rule-file-driven data cleaning with a row-level ledger: missing sentinels, outlier fences, real-key deduplication, per-rule affected row ids, before/after counts and distribution impact, plus a field-level quality report whose numbers must match the cleaned table. Use when: a case gives dirty research tables (missing coded as blanks/-999, near-duplicate records, unit/encoding faults) plus a dictionary and cleaning workorder. NOT for: imputing missing source values on aggregate transcription tables, inferring population statistics, or any cleaning step that cannot list exactly which rows it touched."
---

# 科研数据清洗与处理：每条规则留账，每个字段可核对，零静默丢数

判断清洗做对不看代码行数，而看：每个字段的处理是否有明确规则和依据、清洗后的数据能否直接支撑下游统计、整个过程能否按记录复跑并逐字段核对。本技能把清洗规则外置为 JSON 配置（数据不是代码），dakit.clean 逐条记录受影响行 id、前后行数与分布影响；Agent 负责依据数据字典决定规则与优先级。

**特别约束（对应本题修订版案例形态）**：案例为已发表聚合表的转录件 + 显式注入的存储/编码故障，附数据字典、单位/QC 规则与清洗工单。对此类数据：只做规则化处置与标记（修正存储/编码故障、按工单执行），**不填补来源缺失/无效值，不做总体统计推断**；没有承诺的 quality-gold 运行时文件，不预设金标准文件名。

## 何时使用
* 用例给出脏表（缺失写成空格/-999、近似重复、单位写法不一、编码故障）与数据字典/清洗工单。
* 判定标准：字段级规则与依据；清洗结果可直接支撑下游；报告数字与结果表一致。

**不适用**：统计建模与假设检验、图表美化、数据库运维、实验设计、论文写作；对聚合转录表做插补或总体推断。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（脏表 CSV/表格、数据字典、单位/QC 规则、清洗工单）。

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
```

**第 1 步 字段诊断。** profile 给出每列类型/缺失率/单位提示/候选主键与 warnings（mixed 列、>50% 缺失列）；多表时 join_candidates 验证主键是否真对得上。全部问题先列字段级清单，再定规则。

**第 2 步 写规则文件 `$WORK/rules.json`（核心交付之一）。** 按数据字典与工单逐字段声明：
- missing：哨兵值显式列出（""、"NA"、"-999"…），strategy ∈ drop_rows/fill_value/fill_mean/fill_median/flag；**"未检测"与"真值 0"必须分开编码**，聚合转录表默认 flag 而非填补；
- outlier：method=iqr（1.5×IQR 栅栏）或 zscore（|z|>k），strategy ∈ drop/cap/flag，判据基于清洗前分布并写进账本；
- duplicate：keys=真实主键（样品编号/时间戳/受试者标识），大小写空格归一化后判重，keep=first/last。

**第 3 步 执行与账本。** `python -m dakit.clean table.json rules.json $WORK/clean.json`：每条规则输出 affected_row_ids、before_n/after_n、distribution_before/after（n/mean/sd）、fill_value/criterion。清洗结果另存 `cleaned.csv`；原始文件不动，故障行可回溯。

**第 4 步 数据质量报告。** 由账本生成字段级问题清单：每字段缺失率、异常条数、重复组、处置动作与影响范围；报告中的每个数字必须等于账本/cleaned.csv 的对应计数（report.validate strict 模式机检手改数字）。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact data=$WORK/clean_ledger.json \
    --artifact cleaned_csv=$WORK/cleaned.csv
```

## 本题判据对齐（题面"三件事" → 机制）
1. **"每个字段的处理是否有明确规则和依据"** → rules.json 逐字段声明 + 账本 criterion（如 IQR 栅栏数值、哨兵清单）+ 依据引用数据字典条目。
2. **"清洗后的数据能否直接支撑下游统计"** → cleaned.csv 与账本分布影响（前后 mean/sd）同时交付；mixed 列、未解析单位在 profile warnings 显式遗留，不让脏口径进统计。
3. **"整个过程能否按记录复跑并逐字段核对"** → 输入 sha256 + 规则文件 + 账本行 id + 输出 CSV 行数一致性，第三方可从原始文件复算出同一张 cleaned.csv。
4. **"报告数字与结果表对不上"（题面典型失败）** → 报告由账本回填，validate strict 列出手改数字。

## 交付物
* `rules.json`（规则即数据）、`clean_ledger.json`、`cleaned.csv`、`profile.json`、字段级质量报告 `report.md`（数字全部回填）。

## 证据与审计规则
* 任何 drop 的行必须出现在 affected_row_ids；填补值与判据写入账本；近似重复写明归一化规则与保留依据。
* 单位/编码转换必须可逆或留映射表（如 mg/L ↔ μg/mL 换算系数写入规则 params）。
* 失败不覆盖原文件；所有输出写 $WORK。
* 聚合转录表：不插补、不推断总体；工单未覆盖的字段问题写入 uncertainty 而不是自行处置。

## 方法与近似
异常判据（IQR 栅栏、z 界）是分布经验规则，对重尾分布会多标——账本同时给出受影响行清单供人工复核；n<4 时引擎拒绝出栅栏（样本太少判据不可靠）。

## 异常处理
| 情况 | 处置 |
|---|---|
| 空表/全列缺失 | profile 如实报告；规则对全缺失列跳过并说明 |
| 编码乱码 | extract errors=replace 保底；受影响单元格进 uncertainty |
| 主键冲突/近似重复 | 归一化判重 + 账本列出保留/删除行 id 与依据 |
| 单位不明 | 不换算，flag 并写 uncertainty；禁止猜系数 |
| 规则与工单冲突 | 停工在 uncertainty 列冲突点，人工确认后再跑 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：clean demo 用 12 行已知答案数据集断言三条规则的行 id 与前后行数、fill_median 口径；另有 6 个模块 demo + 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-a0e888fa/v2
