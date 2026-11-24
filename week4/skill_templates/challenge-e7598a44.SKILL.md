---
name: question-driven-search
description: "Decompose a research question into retrievable subquestions, plan searches and stop on evidence sufficiency with a replayable trail. Use when: a case asks to decompose a research question into retrievable subquestions, plan searches, and stop on evidence sufficiency. NOT for: single-paper close reading, full-text translation, writing polish, or open-ended QA."
---

# 科研问题驱动检索：找到文献，也保留筛选依据

面向"问题拆成可检索子问题，证据充分才停止"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出一个科研问题与检索快照，要求拆解、规划、多轮检索并回答。
* 判定标准：子问题可独立检索、每个子问题有足够证据支撑、过程可解释可复现。

**不适用**：单篇精读、全文翻译、写作润色、开放式问答。

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

**第 1 步 拆解。** 问题拆成 `plan.json`：`{subquestions:[{id,text,searchable_terms,depends_on,evidence_required}]}`；`python -m lskit.qplan validate plan.json $WORK/plan_check.json` 校验可检索性与依赖无环。

**第 2 步 检索规划。** 按 suggested_order 安排顺序；每个子问题查询式来自 searchable_terms。

**第 3 步 多轮检索与账本。** 每轮进 iterloop 账本；证据按子问题归集：`evidence.json` `[{subq_id, record_ids, quotes}]`。

**第 4 步 充分性判定。** `qplan sufficiency plan.json $WORK/suf.json evidence.json`：达到 evidence_required 且有引文片段才算充分；不充分就补检或显式标注缺口。

**第 5 步 回答与边界。** 结论逐句回链子问题与证据；无法覆盖的子问题写 uncertainty。

## 本题判据对齐（题面原文的"三件事"）
1. **子问题可独立检索** → validate 零问题（searchable_terms 非空、依赖无环）。
2. **每个子问题证据充分** → sufficiency 逐条达标或显式缺口。
3. **过程可解释复现** → plan + ledger + evidence 全套 JSON。

## 交付物
* `plan.json`、`plan_check.json`、`ledger.json`、`evidence.json`、`suf.json`、`answer.md`（带回链）。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 拆解过粗 | validate 拒绝；继续拆到 searchable_terms 可写 |
| 某子问题检索不到证据 | 标缺口并说明已尝试的查询，不编造 |
| 子问题间结论冲突 | 双方证据并列，写明采纳依据 |
| 依赖成环 | validate 拒绝；重新组织层级 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-e7598a44/v2
