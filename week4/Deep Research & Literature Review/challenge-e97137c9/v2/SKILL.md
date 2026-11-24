---
name: review-draft-evidence-link
description: "Literature-review generation over a given corpus where every sentence is traceable: criteria-first screening records, data-driven theme induction with per-theme support and boundaries, an evidence table with verbatim quotes and locators, and a draft whose statements carry citation strength (proven/suggestive/contested) with conflict pairs shown side by side. Use when: a case provides a literature set and asks for screening, theme induction, evidence organization and a review draft. NOT for: close reading of single papers, full-text translation, language polish, journal selection, or fact-level academic review."
---

# 文献综述生成：每一句都能指回具体文献的草稿

面向"在一批真实文献上完成筛选 → 主题归纳 → 证据组织 → 综述草稿"的任务。本技能把四步串成可复核的链：筛选标准先于写作写定并被引擎一致执行；主题从文献分布里长出来（每个主题给出支撑文献与边界）；证据表每行是 文献标识+原文摘录+定位+支撑论断+证据强度；草稿逐句经审计——引的那篇不支持这句话、反面证据被抹平、空白套话收尾，都会被引擎拒绝。

## 何时使用
* 用例给出一批文献（题录/PDF/全文快照），要求交付筛选记录、主题结构、证据表与带引用的综述草稿。
* 判定标准：筛选标准先于写作写明并一致执行；每条实质论断指回具体文献的具体位置；主题划分与研究空白从这批文献里长出来而不是套上去的。

**不适用**：单篇精读、全文翻译、语言润色、投稿选刊、事实层面学术审查。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献集、题录、PDF/文本快照）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 以下各步的中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/draft.md --artifact evidence_matrix=$WORK/matrix.json \
    --artifact data=$WORK/synthesis_audit.json
```

**第 1 步 筛选（先于写作）。** 依研究问题写 `criteria.json`（纳入/排除条款码）；重复文献先 `python "$SKILL/run.py" identity $WORK/records.json $WORK/deduped.json` 合并（多版本、低相关、仅摘要无全文分别标记）。筛选决定 `decisions.json` → `python "$SKILL/run.py" screen validate $WORK/records.json $WORK/decisions.json $WORK/screen_check.json`——每条记录一条决定+理由码+证据片段，筛选记录可重算。

**第 2 步 主题归纳。** 从纳入文献的方法、对象、结论分歧提炼主题：`themes.json`：`[{id, name, basis:"从哪些文献的什么特征归纳", support_record_ids, boundary:"不覆盖什么"}]`。禁止套通用框架（背景/方法/挑战/展望）；每个主题必须有 support_record_ids，主题间重叠在 boundary 里说清。需要量化支撑时可跑 `trendstat topics` 看主题-年份分布。

**第 3 步 证据表。** `matrix.json`：`sources` 登记全部纳入文献；每个 claim = 一条可定位证据行：`{id, text, subq_id(主题id), supports:[{source_id, quote, locator}], strength: strong|suggestive|contested}`。校验 `python "$SKILL/run.py" evidence validate $WORK/matrix.json $WORK/matrix_check.json`：无原文摘录+定位的行被拒绝。草稿写作从证据表反查，不允许先写句子后补引用。

**第 4 步 冲突并列呈现。** `evidence suggest` 找同主题异极性候选对，Agent 确认后进 `conflicts`：`evidence conflicts` 强制逐对比较双方证据（样本/方法/条件），结论相反或方法互斥的文献在草稿中并列呈现，不抹平成一条叙事线。

**第 5 步 草稿生成与逐句审计。** 草稿 `draft.md` 每个实质论断句同时登记 `synthesis.json`：`{sentence, class: fact|inference|undetermined, claim_ids, basis}`——表述强度对应 claim 的 strength（strong→"已被证明"，suggestive→"有提示性证据"，contested→"仍有争议"并列双方）。审计：
```bash
python "$SKILL/run.py" synthesis audit $WORK/synthesis.json $WORK/matrix.json $WORK/synthesis_audit.json $WORK/plan.json
```
悬空引用（引的文献不在证据表/不支持该句）、无依据推断、静默遗漏主题，全部拒绝。研究空白：`gaps map`/`gaps validate`——空白落到具体证据缺口（哪个主题、哪次检索、缺什么），拒绝"有待进一步研究"套话。

## 本题判据对齐（题面原文的"三件事"）
1. **筛选标准是否先于写作写明并被一致执行** → criteria.json + screen validate（理由码+证据片段强制，计数可重算）。
2. **每条实质论断能否指回具体文献的具体位置** → matrix quote+locator 强制 + synthesis audit 拒绝悬空引用与伪造 claim_id。
3. **主题划分与研究空白是不是从这批文献里长出来的** → themes.json 的 basis+support_record_ids 强制；gaps validate 要求空白回指检索记录或标 speculation。

## 交付物
* `draft.md`（综述草稿，带引用强度标注）、`matrix.json`（证据表）、`themes.json`（主题结构）、`criteria.json`+`decisions.json`+`screen_check.json`（筛选记录）、`synthesis.json`+`synthesis_audit.json`、`conflict_check.json`、`gaps.json`/`coverage.json`、`deduped.json`。

## 证据与审计规则
* 文献必须真实存在：只用 extract 落盘的材料；quote 与原文一致性由 Agent 对照核对并记录定位。
* 引述强度与原文一致：strength 标在 claim 上，草稿措辞不得强于证据强度。
* 反面证据并列呈现；"尚存争议"只有 genuinely_unresolved+依据时才允许。
* 材料没有的内容不补：undetermined+basis，status 降 partial 并写 uncertainty.json。

## 异常处理
| 情况 | 处置 |
|---|---|
| 缺全文/只有摘要 | 标 record usable 限制，证据强度上限 suggestive，进 uncertainty |
| 元数据不全 | 缺字段如实标注，不臆补 |
| 文献重复/多版本 | identity 合并并留合并日志；按版本分别计时说明口径 |
| 结论冲突 | conflicts 并列+adjudication，不抹平 |
| 超出上下文（文献太多） | 按主题分层处理，筛选计数按实际处理量报 |
| 检索/材料为空 | 如实报告，status=partial，不编文献不编主题 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：8 个引擎模块 demo（含无定位证据行、搪塞裁决、伪造引用负例）+ 一次端到端（合成 case → probe → extract → 模块校验 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Deep%20Research%20%26%20Literature%20Review/challenge-e97137c9/v2
