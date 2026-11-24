---
name: manuscript-quality-audit
description: "Full-manuscript quality audit with a typed, locator-bound findings ledger: six facets (fact/citation/method/stats/logic/norm), severity-graded findings, anti-fabrication validation, and checklist coverage. Use when: a case asks to review a paper's overall quality, structural completeness and factual consistency and deliver an itemized issue list with locations, severity and fixes. NOT for: language polishing, plagiarism checking, typesetting, or submission decisions."
---

# 论文质量审查：发现问题，也给出证据

面向"把一篇稿件审成一份可交办问题清单"的任务。本技能把审查拆成确定性簿记（引擎）与语义判断（Agent）：引擎负责定位、数字/声明/结构预扫描、台账验证（无原文摘录+定位+依据的发现一律驳回）、清单覆盖率与报告组装；Agent 负责阅读、判断与修改建议——每一步落盘 JSON，第三方可按记录逐条复核。

## 何时使用
* 用例给出一篇论文全文（或长文材料），要求输出带位置、类型、严重度和修改建议的问题清单，并覆盖事实核验、引用支持、方法设计、统计报告、论证链、学术规范六类检查项。
* 判定标准：每条问题真实存在于原文、定位到句、严重度有据、零问题也是合法结论。

**不适用**：论文润色、语言翻译、查重比对、投稿排版等事务性工作。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（稿件 PDF/文本/表格、参考文献、补充材料等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 确定审查对象。** 从 extract 产物中选定主稿件文本（$WORK/texts/ 下），多文件时记录选用依据；扫描版无文本、缺章节等先记入 uncertainty。

**第 2 步 确定性预扫描。** `python "$SKILL/run.py" audit --work "$WORK" --source <稿件文本>`：产出 `prescan_full.json`（stats 数字主张观察、consistency 跨节数字冲突/摘要-正文缺口/章节结构、norms 声明缺失观察）、空台账 `ledger.json`、12 项六面清单 `checklist.json`。预扫描只产观察，不是结论。

**第 3 步 逐面审查并入册。** Agent 按 checklist 六项 facet 逐面阅读；每条拟报问题写入台账：`python -m arkit.findings`（或脚本调用 `arkit.findings.add`），必填 type/kind/severity/quote/locator/justification/suggestion/severity_basis。区分四类性质：error（事实错误）、insufficient_evidence（证据不足）、norm_issue（规范问题）、suggestion（建议）。

**第 4 步 验证台账。** `python -m arkit.findings validate $WORK/ledger.json <稿件文本>`：引擎逐条核对 quote 是否在原文真实出现（exact/fuzzy≥0.92）、locator 是否可解析、依据是否非空；不通过的发现保留在台账中并标 `rejected`+原因——误报控制留痕，不是删除。

**第 5 步 清单销项与报告。** 逐项 `arkit.checklist.set_status`（pass/issue/needs_review/not_applicable，issue 必须挂 finding_ids 或 evidence）；`python -m arkit.report $WORK/ledger.json $WORK/checklist.json $WORK/report.json $WORK/report.md` 生成计数、覆盖率与 Markdown 报告。有未检查项 → status 必须 partial。

## 本题判据对齐（题面评分点原文）
1. **"交付结构固定、可交办的问题清单，而不是整篇评语"** → 台账固定字段（id/类型/性质/严重度/摘录/定位/依据/建议），报告按严重度排序成表。
2. **"误报是否可控"** → findings.validate 强制 quote+locator+justification，伪造摘录被驳回并留痕（selftest 含伪造发现被驳回的演示）。
3. **"六类检查项……是否都查过"** → checklist 12 项覆盖六面，coverage 逐面计数，unchecked 显式列出绝不隐藏。
4. **"足以让他人回到原文逐条核对"** → 每条发现带 §/¶/页/表 定位串 + 原文摘录 + severity_basis；全部中间产物落盘可复跑。

## 交付物
* `report.md`（问题清单+驳回记录+待复核）、`report.json`（计数/覆盖率/状态建议）、`ledger.json`（验证后台账）、`checklist.json`（逐项状态）、`prescan_full.json`（引擎观察）。

## 证据与审计规则
* 无 quote+locator+justification 的发现一律不得入册；验证器驳回的发现保留并注明原因。
* 零发现是合法结论：台账为空时报告 outcome=no_findings，但 checklist 未查项必须列出。
* 引擎观察（stats/consistency/norms）只是线索，Agent 确认前不得写成缺陷（"作者没报告"≠"作者做错了"）。
* 材料没有的内容不补：无法判断写 uncertainty，status 降级 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 稿件解析失败/扫描版无文本 | 记录 uncertainty，只审可读部分，status=partial |
| 图表无法读取 | 对应检查项标 needs_review，注明缺口 |
| 参考文献缺失/引文无法获取 | citation 面标 needs_review，不臆断"引用不支持" |
| 长文截断 | 在 limits 声明实际覆盖范围，禁止宣称完成全文审查 |
| 数据与结论冲突 | 入册为 fact/logic 发现并附两处摘录定位 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo + 一次端到端（合成稿件 → probe → extract → audit → 台账验证 → 报告 → result.json），含零问题稿件与伪造发现被驳回两条诚实路径。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-0999879e/v2
