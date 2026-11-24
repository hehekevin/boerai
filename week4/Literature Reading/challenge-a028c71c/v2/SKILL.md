---
name: general-evidence-reading
description: "General-purpose evidence-anchored literature reading: identify the reading task type from the case (QA / extraction / verification / translation), route to the matching sub-workflow, and guarantee the common contract for every task - key results carry verbatim locators (page/paragraph/table/figure), unreported and undecidable items are stated explicitly, material conflicts are surfaced. Use when: a case asks for any reading task over provided scientific material (parse, translate, answer, extract, verify, structure knowledge). NOT for: tasks requiring materials beyond those provided, web retrieval, or claims without source anchoring."
---

# 文献阅读通用技能：任何阅读任务，关键结论都回到原文证据

面向整个文献阅读领域的通用入口：先识别任务类型与材料边界，再路由到对应子流程（问答/提取/核验/翻译），所有子流程共享同一条证据契约——**关键结果带定位、未报告如实说明、冲突显式登记**。Agent 负责语义工作，引擎（lrkit）负责统一的证据核验与运行簿记。

## 何时使用
* 用例给出科研材料与阅读类任务（解析、翻译、问答、提取、核验、知识结构化中任意一种或组合）。
* 判定标准：任务类型识别正确、结果覆盖任务要求、关键结论可复核、无法判断不被写成事实。

**不适用**：需要材料之外信息的任务、联网检索、无来源锚定的结论。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（论文/表格/图注/网页快照等材料）。

## 输出（写入 /app/output）
`result.json`（含 case_id 与全部 output_contract 字段、status、sources、uncertainty）+ 按任务类型的主交付物（见"交付物"）+ 各子流程的引擎校验报告。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"   # 统一证据底座：source+loc+text
```

**第 1 步 识别任务类型。** 读 task.md 与 case.json 的工作指令，把任务映射到一个或多个子流程，写入 `route.json`（任务类型 + 理由 + 涉及材料）：

| 任务信号 | 子流程 | 引擎模块 | 校验命令 |
|---|---|---|---|
| 逐题回答、问题清单 | 问答 | lrkit.qa + lrkit.locate | `python -m lrkit.qa questions answers blocks report` |
| 字段表、结构化抽取 | 提取 | lrkit.fields | `python -m lrkit.fields validate dict ext blocks report` |
| 论断核验、引用核查 | 核验 | lrkit.claims | `python -m lrkit.claims validate claims blocks report` |
| 翻译、术语一致 | 翻译 | lrkit.terms | `python -m lrkit.terms align/terms glossary alignment ...` |
| 公式解析、代入 | 公式 | lrkit.formula | `python -m lrkit.formula vtable/numeric ...` |
| 多篇对比 | 比较 | lrkit.matrix | `python -m lrkit.matrix validate ...` |

**第 2 步 材料边界登记。** blocks.json 是唯一定位底座；读不出/未提供的材料写入 uncertainty，不越界作答。

**第 3 步 执行子流程。** 按上表对应命令完成定位→语义工作→落盘→引擎校验；组合任务（如"翻译+问答"）按序执行，各自校验。

**第 4 步 统一交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/report.md" --artifact data="$WORK/<主交付物>.json"
```

## 本题判据对齐（题面通用质量条 → 引擎机制）
1. **"关键结果回到原文证据"** → 所有子流程共用 `locate.verify_quote`：引文逐字核验，伪引文/错挂位置一律 failed。
2. **"对未报告、无法判断和材料冲突明确说明"** → 各子流程的状态枚举（insufficient_evidence / not_reported / not_found / unresolved）都是一等公民；uncertainty 强制落盘。
3. **"完成标准：覆盖任务要求且能回到材料定位"** → 各校验器含覆盖检查（漏题/缺字段/子判断缺失即 ok=false）。
4. **结果正确性与可核验性** → 数字防幻觉检查（qa/terms）、数值字面一致（fields）、四级判定（claims）——自动校验报告随交付物提交。

## 交付物
* `route.json`（任务识别记录）、按子流程的主交付物（answers.json / fields.json / claims.json / alignment.json / variable_table.json / matrix.json）、对应校验报告、`report.md`（中文综合报告：任务、方法、结果、证据定位、不确定性）。

## 证据与审计规则
* 任何关键结论必须有 loc+逐字 quote；引擎核验不通过不得 emit success。
* 材料没有的内容写入 uncertainty，status 降 partial 并在 limits 说明。
* 推断与原文报告分开标注（inferred vs reported 等机制）。
* 冲突（原文自相矛盾、多材料不一致）并列双方出处，不取其一掩盖。
* route.json 记录任务类型判断理由，类型误判可在审计中发现。

## 异常处理
| 情况 | 处置 |
|---|---|
| 任务类型不明/混合 | route.json 标混合并列出全部子流程，逐一执行 |
| 材料缺失/读取失败 | uncertainty 记录 + status 降 partial，不编造 |
| 材料未报告所需信息 | 子流程的拒答状态（insufficient_evidence/not_reported）|
| 材料内部冲突 | 冲突登记（双方出处），report 说明 |
| 输入格式异常（损坏/乱码） | probe 报告，能救的部分先救，其余如实说明 |
| 引擎校验失败 | 回到对应子流程修正；禁止带 failed 交付 success |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：14 个引擎模块 demo 覆盖全部子流程 + 一次端到端合成问答案例。示例材料与数值均为编造占位，非正式案例结果。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-a028c71c/v2
