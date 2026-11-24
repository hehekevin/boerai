---
name: evidence-anchored-paper-qa
description: "Answer per-question literature QA with verbatim, paragraph-anchored evidence and honest abstention: each answer carries claims (reported/inferred) with paragraph_id+quote evidence, conditions, status (answered/partial/insufficient_evidence/input_error) and a coverage report. Use when: a case gives a paper with numbered paragraphs plus a question list and requires answers that can be checked against the text. NOT for: PDF pixel OCR, supplementary-attachment reading, web retrieval, or answers beyond the provided material."
---

# 文献智能问答：逐题回答，也给出依据

面向"读一篇带段落编号的论文 → 逐题回答 → 每条论断挂原文短引文 → 材料未报告就如实说明"的任务。分工：Agent 负责读论文、理解问题、组织答案与翻译；引擎（lrkit）负责可复算的簿记——引文逐字核验、漏题检查、数字防幻觉、阅读覆盖统计——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例提供论文文本（含段落编号）、材料版本、问题清单，要求逐题作答并附依据。
* 判定标准：不漏题、引文可逐字定位、条件/单位保留、未报告处如实拒答。

**不适用**：PDF 图像像素识别、补充附件读取、联网检索、超出给定材料的自由发挥。

## 输入
`/input/case.json`（含 case_id、paper_id、material_version、问题清单）、`/input/task.md`、`/input/**`（论文文本：摘要、正文段落、表格文字、图注、参考文献著录）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ `answers.json`（逐题回答主体，字段契约见下）+ `qa_report.json`（引擎校验记录）+ `coverage.json`（已读/未读段落）。

`answers.json` 字段契约（与题面一致）：每项含 `question_id`、`answer`、`conditions[]`、`status`（answered/partial/insufficient_evidence/input_error）、`claims[]`（claim_id、text、kind=reported|inferred、evidence[] 每项含 paragraph_id/loc 与原文短引文 quote）、`unanswered_parts[]`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"   # 汇总段落为 blocks.json（source+loc+text）
```

**第 1 步 锁定输入标识。** 从 case.json 记录 `case_id`、`paper_id`、`material_version`；从 probe 输出确认问题清单 `questions.json`（一题一个 question_id，含子问拆分备注）。

**第 2 步 建立段落索引。** blocks.json 中每个段落带 `source`（S1..）与 `loc`（段落编号/页码）。若材料自带段落编号，保持原编号作为 loc，不重新编号。

**第 3 步 逐题定位证据。** 对每题先跑定位：
```bash
python -m lrkit.locate search "$WORK/blocks.json" "<关键词 空格分隔>" 
```
候选段落只作线索；答案必须由 Agent 真正读懂段落后写出。

**第 4 步 写 answers.json。** 每题一项：结论写 answer；成立条件（数值、单位、比较对象、实验条件、结论范围）进 `conditions`；区分 `reported`（原文报告）与 `inferred`（自己推断）；材料未报告 → `status=insufficient_evidence` 并在 `unanswered_parts` 写明缺口；只能部分回答 → `partial`。**不得省略任何一题。**

**第 5 步 引擎核验。**
```bash
python -m lrkit.qa "$WORK/questions.json" "$WORK/answers.json" "$WORK/blocks.json" "$WORK/qa_report.json"
python -m lrkit.locate coverage "$WORK/blocks.json" "$WORK/materials_full.json" "$WORK/read_locs.json" "$WORK/coverage.json"
```
qa 校验：引文必须逐字存在于所标段落、数字必须能在材料中找到、漏题与伪证据即失败。有 failed 项必须回第 4 步修正，不得带错交付。

**第 6 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/answers.json" --artifact data="$WORK/qa_report.json"
```

## 本题判据对齐（题面质量条 → 引擎机制）
1. **逐题回答、子问题覆盖完整** → `qa.validate_answers` 的 missing 检查：question 清单中任何一题缺失即 `ok=false`，"不得省略无法回答的问题"由引擎强制。
2. **引文可定位且支持对应结论** → `locate.verify_quote`：quote 折叠空白后必须是所标 loc 段落的逐字子串；编造引文、错挂段落一律 failed。
3. **保留条件、区分实测/解释/推断** → claims 的 `kind`（reported|inferred）由 qa 校验合法性；`conditions` 里的数字必须存在于材料（防张冠李戴）。
4. **"有依据地说明材料未报告也是有效回答"** → `insufficient_evidence` + `unanswered_parts` 是一等公民状态，不是失败；coverage.json 如实列出未读段落及原因。

## 交付物
* `answers.json`（逐题回答+claims+证据）、`qa_report.json`（逐题校验结论）、`coverage.json`（阅读范围）、`questions.json`（问题清单快照）、`report.md`（中文答题报告，逐题列答案与依据）。

## 证据与审计规则
* 每条 `reported` 论断至少一条 evidence；evidence 的 quote 逐字核验，最长 240 字符。
* 推断性表述必须标 `kind=inferred`，不得混进 reported。
* 答案与条件中的每个数字必须能在材料中找到（引擎自动比对）。
* 读取失败的输入文件在 status=input_error 与 uncertainty 中分别说明，不静默跳过。
* 引擎校验 failed 的交付物不得 emit 为 success；降级 partial 并在 limits 写明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料未报告问题答案 | status=insufficient_evidence + unanswered_parts 写明缺口 |
| 只能部分回答（子问缺证据） | status=partial + 逐个子问列 unanswered_parts |
| 原文内部冲突（摘要与正文不一致） | 在 answer 中指出冲突，claims 并列双方出处引文 |
| 段落编号缺失或错乱 | 用 block.N 兜底 loc，并在 coverage.json 记录映射说明 |
| 引文核验失败 | 回原文重取短引文；禁止改写原文凑匹配 |
| 输入文件读取失败 | status=input_error，说明文件与原因，不编造答案 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：14 个引擎模块 demo + 一次端到端（合成段落论文 → probe → extract → blocks → qa 校验 → emit → result.json）。示例论文与数值均为编造占位，仅演示接口。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-15c85674/v2
