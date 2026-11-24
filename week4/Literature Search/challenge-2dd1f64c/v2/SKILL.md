---
name: screening-rank-audit
description: "Screen and rank candidate papers against a documented rubric with stable, explainable ordering and auditable decisions. Use when: a case asks to screen and rank candidate papers against a documented rubric with auditable per-record decisions. NOT for: database access, full-text reading, writing, or formal review inclusion pipelines."
---

# 文献筛选与智能排序：找到文献，也保留筛选依据

面向"用可复核的量表做筛选与排序"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出候选文献集，要求按相关性筛选/排序并说明每条决定。
* 判定标准：判断与可复核标准一致、关键文献排在用户会看的位置、每条决定可复核。

**不适用**：底层数据库接入、全文阅读、写作、系统综述纳排。

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

**第 1 步 冻结量表。** 先写 `rubric.json`：3–5 个可判定判据，每个 0/1/2 分并给打分锚点；量表随结果交付。

**第 2 步 逐条打分。** 按量表打分并写 notes（依据片段）；`python -m lskit.screen rank scored.json` 稳定排序，每个位次可用分数解释。

**第 3 步 决定校验。** 保留/待定/排除三档决定过 `screen validate`：无理由码、无依据片段、漏判都会被点名。

**第 4 步 顶部解释。** 报告说明 top-k 为什么在这个位置（各判据得分），及高分候选被压后的原因。

**第 5 步 冲突队列。** 量表边缘（总分差 ≤1 或判据冲突）的记录进 review 队列，写明核对点。

## 本题判据对齐（题面原文的"三件事"）
1. **判断与可复核标准一致** → rubric.json 锚点 + 逐条分数与依据片段。
2. **关键文献在用户会看的位置** → 稳定排序 + top-k 逐条位次解释。
3. **每条决定可复核** → validate 问题清单为零，或问题已逐条处置。

## 交付物
* `rubric.json`、`ranking.json`、`decisions.json`（三档+理由码+依据）、`review_queue.json`、`report.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 判据对某记录不适用 | 记 n/a 并在 notes 说明，不随意给 0 或 2 |
| 总分并列 | 按 record_id 稳定次序，报告说明规则 |
| 元数据缺失影响打分 | 相应判据降档并写 uncertainty |
| 高分被排除 | 必须给量表内理由码，否则 validate 报警 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-2dd1f64c/v2
