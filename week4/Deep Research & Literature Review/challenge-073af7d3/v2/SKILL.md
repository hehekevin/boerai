---
name: research-trend-audit
description: "Auditable research-frontier and trend analysis: yearly output distributions with declared counting conventions, per-topic per-year evolution tables, change-point signals, stage-representative works with stated selection criteria, and research gaps grounded in actual search records. Use when: a case asks to analyze time trends, topic evolution, representative works or research gaps over a literature set. NOT for: database access beyond provided materials, citation-index truth claims, or whole-field completeness guarantees."
---

# 研究前沿与趋势分析：文献综述——综合证据，也说明边界

面向"判断一个方向现在做到哪、往哪走、哪里还空着"的趋势分析任务。本技能把趋势判断变成可复算的确定性簿记：年度分布、主题-年度计数、拐点信号由引擎从冻结记录集算出；阶段划分、代表作选取、术语归并、空白论证由 Agent 完成并落盘——每条趋势断言必须回指真实统计行，幻影年份与"没检索到=空白"都会被拒绝。

## 何时使用
* 用例给出一批跨年份文献记录（含年份、主题/关键词、被引等字段），要求交付时间趋势、主题演化、代表性工作、研究空白四类产物。
* 判定标准：趋势由可核对的年度分布支撑；演化说清什么时候、因为什么变化；代表作覆盖各阶段且口径可说明；空白有排除证据而非检索遗漏。

**不适用**：超出所给材料的数据库接入、全领域完整性担保、把关键词热度直接当趋势结论。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、检索结果、题录表等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 以下各步的中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact data=$WORK/yearly.json \
    --artifact evidence_matrix=$WORK/matrix.json
```

**第 1 步 冻结记录集。** 从材料整理 `records.json`：`[{id, year, topics:[...], title, authors, citations, source_db}]`。多年份口径（在线发表/见刊/预印本）在报告中显式注明取哪个；多版本记录用 `python "$SKILL/run.py" identity records.json deduped.json` 合并（合并日志留痕）。**缺年份的记录不进分布但必须列名**——引擎的 `missing_year_ids` 强制列出。

**第 2 步 问题拆解（可选但推荐）。** 若案例含显式研究问题，走 `qplan validate`（见第 5 步引用）；纯趋势任务可直接定义主题口径。

**第 3 步 算分布与主题演化。**
```bash
python "$SKILL/run.py" trendstat yearly $WORK/records.json $WORK/yearly.json
python "$SKILL/run.py" trendstat topics $WORK/records.json $WORK/topics.json
python "$SKILL/run.py" trendstat signals $WORK/yearly.json $WORK/signals.json
```
yearly 给出逐年计数、时间跨度、缺失年份清单与 denominator_note；topics 给出每个主题的总量、首现年、末现年、逐年序列（主题的出现/扩张/衰退从数字读）；signals 给出拐点**信号**（窗前均值 × 倍数），信号≠拐点，是否真实拐点须 Agent 结合文献内容论证。术语漂移/同名异义：Agent 提供 synonyms 归并表后重跑 topics，引擎不做语义归并，归并表落盘可复算。

**第 4 步 代表作选取。** 为各阶段选代表作，入选口径写明（如：阶段内被引前列 ∪ 方法首创长尾），落盘 `representatives.json`：`[{record_id, stage, selection_basis}]`。禁止只用总被引排序一口径。

**第 5 步 趋势断言审计。** 每条趋势/演化结论写入 `trend_claims.json`：`[{id, text, kind: trend|evolution|representative|gap, stat_refs:{years:[...], topics:[...]}}]`。审计：`python "$SKILL/run.py" trendstat audit $WORK/trend_claims.json $WORK/yearly.json $WORK/topics.json $WORK/trend_check.json`——无 stat_refs 的趋势断言、引用零记录年份、引用不存在的主题，全部被拒绝。

**第 6 步 研究空白。** 空白主张必须建立在检索记录上：`gaps map`（plan+queries+evidence → coverage.json）后 `gaps validate`；searched_* 类空白引用真实 query_id，未覆盖方向标 `speculation:true`。"没检索到"不等于"研究空白"，须附检索范围与排除条件。

**第 7 步 证据回链与报告。** 关键趋势判断同时进 `matrix.json`（claim→quote+locator），走 `evidence validate`；结论分级（fact/inference/undetermined）走 `synthesis audit`。报告写清数据口径、阶段划分依据、代表作口径、空白依据与不确定性。

## 本题判据对齐（题面原文的"四件事"）
1. **趋势是否由可核对的年度分布支撑** → yearly.json 逐行可手算 + trendstat audit 强制 stat_refs + 幻影年份拒绝。
2. **演化是否说清"什么时候、因为什么变化"** → topics.json 的首现年/逐年序列定"什么时候"，"因为什么"由 Agent 引用具体文献段落（matrix.json）论证。
3. **代表作是否覆盖各阶段且口径可说明** → representatives.json 每条的 stage+selection_basis；多口径并集，避免纯被引排序。
4. **空白是否有排除证据而不是检索遗漏** → gaps validate：空白必须引用真实检索记录或显式标记为推测。

## 交付物
* `report.md`（趋势分析报告）、`yearly.json`/`topics.json`/`signals.json`（可复算统计）、`trend_claims.json`+`trend_check.json`、`representatives.json`、`coverage.json`/`gaps.json`/`gaps_check.json`、`matrix.json`（关键判断回链）、`records.json`（冻结数据）。

## 证据与审计规则
* 分母只用冻结记录集，绝不用结果集反推；缺年份记录列名不静默删除。
* 引擎给的拐点是信号不是结论；Agent 的拐点论证必须引用文献内容并落盘。
* 趋势/演化断言无统计回链即拒绝；"前沿"不得定义为检索结果前若干条。
* 材料没有的内容不补：无法判断写 undetermined + basis，status 降级 partial 并在 uncertainty.json 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 检索为空/记录过少 | 如实报告，拒绝输出趋势结论；gaps 走 searched_no_evidence |
| 年份缺失 | missing_year_ids 列名，分布分母说明 |
| 主题严重歧义（术语漂移） | Agent 提供 synonyms 归并表并重跑；未归并的歧义主题写入 uncertainty |
| 文献量爆炸 | 先按年份/来源分层抽样并在报告注明口径，再算分布 |
| 证据互相冲突 | 进 matrix conflicts 并 adjudication，不取一方了事 |
| 各阶段代表作缺候选 | 该阶段如实标注"无满足口径的代表作"，不凑数 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：8 个引擎模块 demo（trendstat 含幻影年份拒绝负例）+ 一次端到端（合成 case → probe → extract → 模块校验 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Deep%20Research%20%26%20Literature%20Review/challenge-073af7d3/v2
