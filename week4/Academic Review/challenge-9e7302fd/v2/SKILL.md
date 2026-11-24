---
name: methods-stats-review
description: "Research-methods and statistics review producing an itemized audit sheet: five facets (design, variables, statistical methods, sample size/power, result reporting), deterministic numeric-claim detectors, severity matched to defect nature, and a validated findings ledger. Use when: a case asks to review a manuscript's study design, variable definitions, statistical methods, sample size and result reporting with per-item location, defect type, severity, basis and fix. NOT for: re-running the analysis, literature search, translation, polishing, or editorial accept/reject decisions."
---

# 研究方法与统计审查：一份能交给作者逐条回复的审查单

面向"研究设计—变量定义—统计方法—样本量—结果报告"五面审查。引擎做确定性簿记：stats 定位全部数值主张并记录 n/CI/p/效应量伴随情况（只产观察）；consistency 核对图表与正文数字；findings 验证器保证每条意见落回具体段落/表/句；严重度与缺陷性质绑定（硬伤≠报告不全）。Agent 做方法学判断——区分"方法本身有缺陷"和"方法可接受但报告不全"。

## 何时使用
* 用例给出稿件全文（或含统计输出的材料），要求输出审查单：问题出在哪一段、属于哪类缺陷、严重到什么程度、依据是什么、应该怎么改。
* 判定标准：每条意见落回原文具体位置；严重度与缺陷性质匹配而非一律"重大"；复核人可按记录独立重跑得到同一份审查单。

**不适用**：原始数据重分析与统计复算、文献检索、全文翻译、语言润色、代写审稿结论或投稿决策。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（稿件、表格、统计输出、补充材料等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <稿件文本>
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 统计报告预扫描。** `python -m arkit.stats <稿件文本> $WORK/stats.json`：定位全部 p 值/CI/n/百分比/mean±SD/效应量，产出三类观察——p 无 CI/效应量伴随、数值无 n、"significant"字样无统计量。观察只是候选，Agent 须回上下文确认（如描述性表格可能本就无需 n）。

**第 2 步 五面逐项审查。** 按 checklist 走五面：研究设计（设计类型vs研究问题、对照/分组/盲法、主要终点是否事先明确）、变量定义（暴露/结局/协变量定义与编码一致性、切点与缺失值处理）、统计方法（检验vs数据结构/分布假设、多重比较、重复测量）、样本量（估算依据、效应量来源、把握度、实际入组与失访处理）、结果报告（效应量+CI、精确 p、统计量与自由度、图表与正文一致性——用 `arkit.consistency` 辅助）。每面结论销 checklist 项。

**第 3 步入册与严重度分级。** 每条确认缺陷写台账：type=method|stats，kind=error|insufficient_evidence|suggestion；severity_basis 必填——critical=动摇主结论/方法硬伤，major=影响可信度或可复现，minor=报告完整性。严禁一律标"重大"。

**第 4 步 验证与报告。** `python -m arkit.findings validate $WORK/ledger.json <稿件文本>`；`python -m arkit.report $WORK/ledger.json $WORK/checklist.json $WORK/report.json $WORK/report.md`。

## 本题判据对齐（题面"三件事"原文）
1. **"每条意见能否落回稿件原文的具体位置"** → 台账强制 quote+locator（§节¶段s句/表号），验证器核对摘录真实存在；定位不到句的发现被驳回。
2. **"严重度是否与缺陷性质匹配，而不是一律写成'重大缺陷'"** → severity_basis 必填且按"是否影响主结论/是否可修正/是否影响可复现"书写；报告按严重度排序，minor 的报告缺口与 critical 的方法硬伤分列。
3. **"复核人能否按记录独立重跑，得到同一份审查单"** → 预扫描、台账、清单、报告全部 JSON 落盘；输入文件 sha256 进 result.json sources。

## 交付物
* `report.md`/`report.json`（审查单：定位/缺陷类型/严重度/依据/修改建议）、`ledger.json`、`stats.json`（数值主张与观察）、`checklist.json`（五面销项）。

## 证据与审计规则
* "作者没有报告"（insufficient_evidence）与"作者做错了"（error）必须分开入册，性质不同严重度不同。
* 统计观察（stats 模块）不是判决；Agent 确认前不得写成缺陷，可接受做法不得判成硬伤。
* 每条意见必须可被第三方按 quote+locator 独立复核；无法判断标 needs_review。
* 材料不足以判断样本量/检验效能时，标 needs_review 而非编造估算。

## 异常处理
| 情况 | 处置 |
|---|---|
| 稿件缺页/章节缺失 | 对应检查面标 needs_review，limits 声明 |
| 扫描件识别失败 | 记录 uncertainty，审可读部分，status=partial |
| 图表/统计输出无法解析 | 结果报告面标 needs_review，注明缺口 |
| 统计方法不熟悉或材料不足 | 标 needs_review + 核对点，不臆断 |
| 语言混杂 | 中英文统计标记均可识别（stats 含中文模式），其余记 uncertainty |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：stats demo 演示 p 无 CI、"significant"无统计量、数值无 n 三类观察；findings demo 演示伪造发现被驳回；端到端合成案例走完整流程。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-9e7302fd/v2
