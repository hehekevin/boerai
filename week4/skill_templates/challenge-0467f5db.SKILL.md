---
name: search-coverage-audit
description: "Audit literature-search coverage against a frozen reference set: per-item hit status, miss classification with query-level attribution, and supplement-delta proof. Use when: a case asks to audit search coverage against a reference set, classify missed papers, and plan supplementary searches. NOT for: database access, full-text reading, or formal systematic-review inclusion processes."
---

# 检索覆盖率与遗漏分析：找到文献，也保留筛选依据

面向"以参考集为分母算覆盖、给漏检归因、做定向补检"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出已知相关文献清单（参考集）与检索结果/查询日志，要求回答覆盖率、漏检清单与补检效果。
* 判定标准：覆盖率分子分母可核对、漏检归因到具体查询/字段/来源、补检后遗漏真实下降。

**不适用**：替代数据库接入、全文阅读、系统综述正式纳排。

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

**第 1 步 冻结参考集。** 从材料整理 `refs.json`：`[{id, doi, title, authors, year, include_reason, usable, exclude_reason}]`；撤稿/无法获取全文的标 `usable:false` 并写排除理由。

**第 2 步 整理命中日志。** 每次查询的结果整理成 `hits.json`：`[{query_id, source, query_string, record:{...}}]`——漏检归因依赖 query_id 与 source 的完整保留。

**第 3 步 算覆盖。** `python -m lskit.coverage refs.json hits.json $WORK/coverage.json [year_min]`：逐条参考给命中状态（哪次查询、哪个来源、哪条规则），分母=冻结可用参考数。

**第 4 步 漏检归因。** 引擎给候选类别（query_vocab/field_restriction/time_window/source_not_indexed/record_anomaly），Agent 逐条回到查询日志确认并写证据，落盘 `misses_confirmed.json`。

**第 5 步 定向补检与增量。** 按归因类别设计新查询（换同义词、放开字段、延长时间窗、加来源库），补检快照同样走第 3 步；增量报告按 ref_id 逐条列出 resolved/remaining；残余遗漏写明原因。

## 本题判据对齐（题面原文的"三件事"）
1. **分子分母可核对** → coverage 的 `denominator_note` + 冻结 refs.json（含撤稿排除理由）。
2. **每条漏检归因到具体查询/字段/来源** → misses_confirmed.json 逐条引用 query_id 与原始查询式。
3. **补检后遗漏真的下降** → 增量报告按 ref_id 列出 resolved/remaining，不接受只报总数。

## 交付物
* `coverage.json`、`misses_confirmed.json`（归因+证据）、`supplement_delta.json`、`refs.json`/`hits.json`（冻结数据）、`report.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 参考集含撤稿/缺字段记录 | `usable:false` + 排除理由，不进分母也不静默删除 |
| 同一文献多版本 | identity 合并并在 merge 日志记录规则；必要时按版本分别计 |
| 补检无新增 | 如实报告 zero-gain，不得宣称遗漏下降 |
| 命中判定模糊 | 进 pending_review 队列并写明核对点 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-0467f5db/v2
