---
name: reading-bench-runner
description: "Literature-reading benchmark and evaluation toolchain: complete item cards (task/materials/reference/0-1-2 rubric) with snapshot hashes, a fixed-budget run record, score validation requiring rationale and run_id, per-question-type aggregation dashboards, run-to-run consistency checks with fluctuation registration, and failure attribution that turns score-0 items into next-version drill items. Use when: a case asks to build or run a reading benchmark, score outputs reproducibly, aggregate results, or analyze evaluation failures. NOT for: replacing human judgement on open-ended answers, leaderboard scraping, or benchmarks without frozen snapshots."
---

# 文献阅读 Benchmark 与评测工具：判得动、跑得一致、查得回、改得动

聚焦方向：**评分表 + 结果面板 + 失败归因**（题面允许只选一个方向）。从真实评测失败出发：题目判不了（缺参考答案/评分规则）、分数对不上（重复运行波动无记录）、结果找不回（分数追不到原始输出）。引擎把这三件事变成强制校验；Agent 负责按 rubric 判分与写判分依据。

## 何时使用
* 用例给出题集/候选输出/评分要求，要建题、跑评测、出逐题得分与失败分析。
* 判定标准：题卡齐备可判、同配置重复运行分数稳定且波动被记录、每个分数可回溯、失败可归因到题型。

**不适用**：替代开放式答案的人工终审、无冻结快照的评测、爬榜。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（题集/任务说明、待评输出、评分规则、材料快照）。

## 输出（写入 /app/output）
`result.json` + `itemset.json`（题卡+快照哈希）+ `scores.json`（逐题 0/1/2 分+依据）+ `dashboard.json`（按题型×运行聚合）+ `consistency.json`（复跑一致性）+ `failures.json`（失败归因+专项题种子）+ `report.md`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
```

**第 1 步 建题/验题。** 整理 `itemset.json`：`{version, items: [{item_id, qtype, task, materials, reference, rubric: {score_points: {0,1,2}}}]}`，校验：
```bash
python -m lrkit.bench validate-itemset "$WORK/itemset.json" "$WORK/itemset_report.json"
```
缺 task/reference/rubric 的题被标"判不动"并阻止进入评测——不给同情分。版本快照哈希随题集落盘。

**第 2 步 固定配置运行。** 记录 run 配置（工具权限、提示、预算、题集快照哈希、Agent 版本）为 `run_config.json`；原始输出存 `runs/<run_id>/raw_output.*`——分数必须能顺着 item_id 追回这里。

**第 3 步 逐题评分。** Agent 按 rubric 的 0/1/2 锚点判分，写 `scores.json`：`[{item_id, run_id, score, rationale, scorer, dispute?}]`。校验：
```bash
python -m lrkit.bench validate-scores "$WORK/itemset.json" "$WORK/scores.json" "$WORK/scores_report.json"
```
分数非 0/1/2、无 rationale、无 run_id 一律拒绝；争议写 dispute 字段不覆盖原分。

**第 4 步 结果面板。**
```bash
python -m lrkit.bench aggregate "$WORK/itemset.json" "$WORK/scores.json" "$WORK/dashboard.json"
```
按题型×运行聚合（n、总分、均分、0/1/2 分布），看得见优势与短板，不只是一个总分。

**第 5 步 复跑一致性。** 同配置跑第二次，分数合并为 runs 列表：
```bash
python -m lrkit.bench consistency "$WORK/runs.json" "$WORK/consistency.json"
```
同 config_hash 下分数不一致的题列入 fluctuations，**必须人工复核并解释，禁止只报平均分**。

**第 6 步 失败归因与交付。**
```bash
python -m lrkit.bench failures "$WORK/itemset.json" "$WORK/scores.json" "$WORK/failures.json"
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/dashboard.json" --artifact report="$WORK/report.md"
```
score=0 的题归到具体 qtype，生成下一版专项题种子；只重算受影响题型的分数。

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **判得动** → `validate_itemset`：task/reference/rubric 缺一即 unusable 并阻止进评测；不同人看同一份 rubric 锚点给同一结论。
2. **跑得一致** → `consistency_check`：同 config_hash 复跑的分数波动逐题登记并要求解释；run_config 固定工具权限与预算。
3. **查得回** → `validate_scores` 强制 run_id；题集快照哈希贯穿 itemset/scores/dashboard；原始输出按 run_id 归档。
4. **改得动** → `failure_attribution`：失败归到 qtype、产出专项题种子，版本迭代只重算受影响题型。

## 交付物
* `itemset.json`、`scores.json`、`dashboard.json`、`consistency.json`、`failures.json`、`runs/`（原始输出+run_config）、`report.md`。

## 证据与审计规则
* 评分只能 0/1/2 且带 rationale；人工复核改分写 dispute 不改原记录。
* 分母分子用冻结题集快照，不从结果反推。
* 波动不平均、不隐藏；解释不了的在 uncertainty 写明。
* 缺参考答案是题集缺陷，登记 unusable，不让 Agent 现场编答案再评分。
* 自动评分与人工结论不一致时，以人工结论为准并在 dispute 中记录差异。

## 异常处理
| 情况 | 处置 |
|---|---|
| 题目缺参考答案/评分规则 | validate-itemset 标 unusable，阻止进评测 |
| 待评输出为空或超长 | 该题记 0 分 + rationale 说明，或单独登记格式问题 |
| 输出格式不合规 | 登记为运行配置问题，不计入题难度 |
| 复跑分数波动 | consistency 登记，人工复核解释后再出报告 |
| 题集版本变化 | 新版本新快照哈希；report 说明哪些历史分数仍可比 |
| 权限/文件损坏 | probe 报告，status 降 partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：bench demo 演示题卡校验、0/1/2 评分聚合、复跑波动抓出（Q2 两次运行 1 分 vs 2 分）、失败归因生成专项题。示例题卡均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/benchmark-a1d81ca4/v2
