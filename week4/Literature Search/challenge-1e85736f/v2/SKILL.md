---
name: literature-increment-tracker
description: "Track newly appeared literature between frozen snapshots with replayable per-item evidence, dedupe and alert logging. Use when: a case asks to track newly appeared literature between snapshots, dedupe against history, and justify every increment. NOT for: full-text reading, automatic review writing, or unauthorized scheduled crawling."
---

# 最新文献发现与追踪：找到文献，也保留筛选依据

面向"对冻结快照做增量识别，压住重复与误报"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出上一次冻结快照与本次检索快照，要求给出新增文献清单与判定依据。
* 判定标准：时间窗内真增量、重复与误报被压住、增量判定可回放。

**不适用**：全文阅读、自动写综述、未经授权的定时抓取。

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

**第 1 步 冻结基线。** 确认材料中哪份是上次快照（prev）、哪份是本次（curr），原样落盘并记录来源与时间。

**第 2 步 快照比对。** `python -m lskit.increment prev.json curr.json $WORK/diff.json`：每条 new/removed 给出与冻结快照的 identity 比对依据（规则与分数）。

**第 3 步 误报压制。** new 集合再过 identity.dedupe；与历史提醒记录比对，已提醒的标 `already_alerted`，不重复提醒。

**第 4 步 提醒记录。** 每条提醒写：record、判定 basis、时间窗、来源库；无新增时明确写"本窗口无新增"。

**第 5 步 失败与重试。** 快照缺失或损坏时保留上次可用状态并写入 uncertainty，不伪造增量。

## 本题判据对齐（题面原文的"三件事"）
1. **时间窗内真增量** → diff.json 逐条 basis（与冻结快照比对，不是日期猜测）。
2. **重复与误报被压住** → dedupe 合并日志 + already_alerted 标记。
3. **增量判定可回放** → 每条 new 可重算（规则+分数+双方记录）。

## 交付物
* `diff.json`、`alerts.md`（逐条提醒与依据）、`dedupe_audit.json`、快照副本。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 记录元数据变化 | identity 判 matched，变化字段进冲突日志，不算新文献 |
| 快照缺时间戳 | 以文件清单确定先后；无法确定写 uncertainty |
| 全量重复 | 明确写"本窗口无新增"，不编造 |
| 新记录身份模糊 | 进 review 队列，给出两种可能及核对点 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-1e85736f/v2
