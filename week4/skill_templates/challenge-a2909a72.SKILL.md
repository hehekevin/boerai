---
name: scholarly-search-planner
description: "Plan and execute multi-round scholarly searches with query planning, dedupe, source logging and stop criteria. Use when: a case asks to plan and run multi-round keyword searches on open scholarly databases with dedupe and source logging. NOT for: single-paper reading, full-text parsing, writing polish, or library management."
---

# 学术文献检索：找到文献，也保留筛选依据

面向"开放库检索的规划、召回、去重与来源记录"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出检索主题与开放库快照，要求多轮查询、候选召回与排序。
* 判定标准：查询规划有依据、结果去重、每条记录来源可溯。

**不适用**：单篇阅读、全文解析、写作润色、资料库整理。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、参考集、查询日志、引文图、PDF/表格等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/<主交付物> --artifact data=$WORK/<数据文件>
```

**第 1 步 查询规划。** qplan 拆检索目标，规划多轮查询（先宽后窄），每轮查询式与意图落盘。

**第 2 步 执行与账本。** 每轮结果记录进 iterloop 账本；快照结果逐条标来源库。

**第 3 步 去重合并。** 全部轮次结果过 identity.dedupe，合并日志随交付。

**第 4 步 排序与交付。** 按 rubric 排序（screen rank），交付候选清单+每条来源+账本；停止条件用 iterloop 判据说明。

## 本题判据对齐（题面原文的"三件事"）
1. **查询规划有依据** → qplan 子目标与查询式对应表。
2. **结果去重且来源可溯** → dedupe 审计 + _sources。
3. **过程可复跑** → iterloop 账本全字段非空。

## 交付物
* `plan.json`、`ledger.json`、`merged.json`、`ranking.json`、`report.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 某轮查询返回为空 | 账本如实记录 0 返回与下一步决策 |
| 快照缺关键字段 | 字段缺失清单+对排序的影响写 uncertainty |
| 多轮结果高度重叠 | dedupe 计数单列，说明边际收益 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-a2909a72/v2
