---
name: systematic-screening-prisma
description: "Systematic-review screening with dedupe, reason-coded decisions, dual-screen conflict handling and PRISMA-style recountable counts. Use when: a case asks to run systematic search screening with dedupe, dual decisions, conflict adjudication and PRISMA-style counts. NOT for: database access itself, full-text reading, or writing the review."
---

# 系统性文献检索与纳排筛选：找到文献，也保留筛选依据

面向"PRISMA 式纳排：判据落到可判定规则，计数可复核"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例要求系统性筛选：去重、标题摘要筛选、（模拟）双人判断、冲突仲裁、流程审计。
* 判定标准：标准逐条可判定、每条判断有理由码与依据片段、计数与日志支撑独立复核。

**不适用**：数据库接入本身、全文阅读、综述写作。

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

**第 1 步 检索协议与判据。** 纳入/排除标准写成 `criteria.json`：每条判据给可观察规则与理由码。

**第 2 步 去重。** `python -m lskit.identity records.json $WORK/dedup.json`：合并日志含规则与字段冲突。

**第 3 步 筛选。** 逐条决定（include/exclude/maybe + 理由码 + 依据片段）；`screen validate` 校验完整性；双人模拟时两份决定分别落盘，`screen conflicts` 输出一致率与冲突清单，冲突写仲裁记录。

**第 4 步 PRISMA 计数。** identified → deduped → screened → included 逐级计数，全部可从 decisions.json 重算。

**第 5 步 审计。** 交付 criteria/decisions/conflicts/counts 全套 JSON；改动记 changes。

## 本题判据对齐（题面原文的"三件事"）
1. **标准逐条可判定** → criteria.json 每条判据有可观察规则与理由码。
2. **每条判断有理由码+依据片段** → validate 强制；缺失即问题清单。
3. **计数与日志支撑独立复核** → PRISMA 逐级计数全部由 decisions.json 重算。

## 交付物
* `criteria.json`、`dedup.json`、`decisions.json`、`conflicts.json`（双人时）、`prisma_counts.json`、`flow.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 摘要不足以判定 | maybe 档 + 需要全文的说明 |
| 双人决定冲突 | conflicts.json + 仲裁记录（仲裁人、理由），不静默取一方 |
| 判据执行中发现歧义 | 修订判据记 changes 并重跑受影响记录 |
| 重复记录版本不同 | identity 合并日志说明保留哪版及原因 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-5b90f5e9/v2
