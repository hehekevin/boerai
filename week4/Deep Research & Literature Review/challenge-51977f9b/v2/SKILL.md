---
name: systematic-review-trail
description: "Systematic literature review with an auditable trail: executable search strings with per-clause intent, versioned inclusion/exclusion criteria applied consistently, two-round screening records with per-record reason codes and evidence snippets, explainable quality appraisal, and synthesis where every statement links back to included evidence. Use when: a case asks for a systematic-review-style pipeline with search protocol, screening records, quality appraisal and reproducible included set. NOT for: single-paper close reading/translation, writing polish, or methodology fact-checking of source papers."
---

# 系统性文献综述：一条别人可以沿着走一遍的流程

面向"检索式 → 纳排标准 → 两轮筛选记录 → 质量评价 → 可复核综述"全链路任务。本技能把系统综述流程变成可复跑的确定性簿记：纳排判定与质量等级由 Agent 依事先写定的条款作出，引擎强制每条记录有决定+理由码+证据片段、计数可重算、双人分歧不静默覆盖、综述论断必须回链纳入证据。

## 何时使用
* 用例给出研究问题与题录/全文材料，要求按系统综述规范交付检索方案、筛选记录、质量评价与带回链结论。
* 判定标准：纳入与排除的每一篇都有可查理由；综述每条论断能回链具体证据；换人拿同样输入与记录能复跑出基本一致的纳入集与结论。

**不适用**：单篇文献精读与翻译、论文写作润色、对源文献做事实与方法核验的学术审查。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：题录表、检索结果、全文快照等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 以下各步的中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/review.md --artifact evidence_matrix=$WORK/matrix.json \
    --artifact data=$WORK/screen_check.json
```

**第 1 步 问题结构化与检索式。** 用 qplan 把研究问题拆成检索要素（对象/干预/结局/研究类型）：`plan.json` → `qplan validate`。检索式写入 `queries.json`：`[{id, subq_id, string, source, fields, time_range, language, intent, returned, kept}]`——**每段检索式写 intent**（同义词/受控词/字段/时间语言限制的理由）。检索日期与数据库范围在 review.md 中注明。

**第 2 步 纳排标准（先于筛选写定）。** `criteria.json`：`{version, inclusion:[{code, rule}], exclusion:[{code, rule}], priority, conflict_policy}`。条款必须可判定（研究类型、人群/对象、时间范围、语言、全文可得性），条款冲突时的优先级写清。筛选途中修改标准 → 版本号+1 并在 changes.json 记修改原因——**不允许悄悄放宽**。

**第 3 步 两轮筛选留痕。** 题录级与全文级分别产出 `decisions_t1.json`/`decisions_t2.json`：`[{record_id, decision: include|exclude|maybe, reasons:[criteria 码], evidence:"原文片段", screener, round}]`。校验：
```bash
python "$SKILL/run.py" screen validate $WORK/records.json $WORK/decisions_t1.json $WORK/screen_t1.json
python "$SKILL/run.py" screen validate $WORK/records.json $WORK/decisions_t2.json $WORK/screen_t2.json
```
每条记录恰一条决定；exclude/maybe 必须带证据片段；计数（identified→deduped→screened→included）可重算。双人/双轮分歧：`screen conflicts d1.json d2.json` 列出待裁决清单，裁决结果落盘——不静默覆盖。多库去重先跑 `identity`。

**第 4 步 质量评价。** 选定量表维度写入 `appraisal.json`：`[{record_id, dimensions:{维度: 0|1|2}, evidence_loc, overall: high|medium|low, impact_note}]`——逐维度给依据位置，说明该等级如何影响后续结论（如低质量研究只作敏感性叙述）。`screen rank` 可复算排序。

**第 5 步 证据综合与论断回链。** 纳入研究进 `matrix.json`（claim→quote+locator）→ `evidence validate`；冲突结论进 `conflicts` 并 adjudication（拒绝"尚存争议"搪塞）→ `evidence conflicts`。综述论断进 `synthesis.json` → `synthesis audit`（fact/inference/undetermined 三分类；每个子问题被覆盖或显式标缺口）。研究空白 → `gaps map/validate`（必须回指真实检索记录）。

## 本题判据对齐（题面原文的"三件事"）
1. **纳入与排除的每一篇是否都有可查的理由** → screen validate：无理由码/无证据片段的决定被拒；PRISMA 计数可重算。
2. **综述中的每条论断是否能回链到具体证据** → matrix quote+locator 强制 + synthesis audit 拒绝悬空引用。
3. **换人拿同样输入和记录能否复跑** → criteria.json 版本化、decisions 逐条落盘、inputs.json 含 sha256、全部 *_check.json 可复算。

## 交付物
* `review.md`（综述正文）、`criteria.json`（纳排标准，版本化）、`queries.json`（检索式+intent）、`decisions_t1/t2.json`+`screen_t1/t2.json`（两轮筛选记录与计数）、`appraisal.json`（质量评价）、`matrix.json`（证据表）、`synthesis_audit.json`、`gaps.json`/`coverage.json`。

## 证据与审计规则
* 纳排标准先于筛选写定并版本化；中途修改必须留痕（changes.json）。
* 排除理由引用 criteria 条款码，不写自由文本套话；题录级与全文级记录分开保存。
* 质量评价逐维度给依据位置；"质量较高"式一句话评价不合规。
* 综述论断不越过纳入证据：材料没有的内容写 undetermined+basis，status 降 partial。

## 异常处理
| 情况 | 处置 |
|---|---|
| 检索为空 | 如实记 returned:0；在 review.md 说明检索范围，空白走 searched_no_evidence |
| 数据库/接口超时、全文不可得 | 记录该来源状态，受影响记录标 maybe+理由，进 uncertainty.json |
| 术语歧义（同一概念多种表述） | 同义词表落盘并在检索式 intent 中说明 |
| 纳排条款冲突 | 按 criteria.priority 判定；判不了进 pending，记录核对点 |
| 纳入证据互相矛盾 | matrix conflicts + adjudication；genuinely_unresolved 须写依据 |
| 文献量巨大 | 分层抽样口径写明，计数仍按实际处理量报 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：8 个引擎模块 demo（screen 含无理由拒绝、双人分歧负例）+ 一次端到端（合成 case → probe → extract → 模块校验 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Deep%20Research%20%26%20Literature%20Review/challenge-51977f9b/v2
