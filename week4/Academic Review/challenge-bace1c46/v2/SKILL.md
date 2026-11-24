---
name: paper-quality-appraisal
description: "Single-paper research-quality appraisal as a dimension-judgment-evidence-grade table: five dimensions (design/sample/measurement/statistics/reporting), sentence-level evidence anchors, explicit aggregation rule, and honest abstention when evidence is missing. Use when: a case asks to appraise the research quality / risk of bias of a provided paper with per-dimension judgments traceable to located evidence. NOT for: peer-review verdicts, fact-checking external sources, clinical/policy decisions, or appraising papers whose text is not provided."
---

# 文献研究质量评价：维度—判断—证据—等级，可弃权不硬编

面向"给一篇文献做结构化质量评价"的场景。引擎维护量表簿记（quality 模块）：五个维度（研究设计/样本与抽样/测量与结局/统计分析/报告完整性）各自有判断等级、证据锚点与理由；**没有可核验证据时强制判 insufficient_evidence（弃权），拒绝"看起来合理"的补齐判断**；总等级由显式聚合规则推导，附推导行，第二人可按记录复算。Agent 负责阅读判断与偏倚风险语义。

## 何时使用
* 用例给出一篇文献（全文或摘要+材料），要求产出维度—判断—证据—等级的评价表，区分"明确存在/可能存在/未见迹象/证据不足"。
* 判定标准：每条判断对应原文可定位证据片段；维度覆盖与该文献类型应有检查点匹配；第二人按记录可独立复核并给出可比结论。

**不适用**：替代同行评审、对外部来源做事实核验、临床/政策决策、未提供文本的文献臆评。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（文献全文/摘要、量表要求、补充材料等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <文献文本>
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/appraisal.md --artifact ledger=$WORK/scale.json \
    --artifact result=$WORK/appraisal.json
```

**第 1 步 确认文献类型与检查点。** 从 task.md/case.json 确认文献类型（RCT/观察性/综述/摘要-only 等）与题目要求的维度；默认五维量表 `arkit.quality.new_scale(paper_id, paper_type)`，题目另有维度时调整并落盘理由。

**第 2 步 证据定位。** 用预扫描与 locate 为每个维度收集原文片段（句级/表级定位）：`python -m arkit.locate <文献文本>` 浏览定位单元，`arkit.stats`/`arkit.norms` 辅助统计与声明类证据。

**第 3 步 逐维判断。** `arkit.quality.judge(scale, dim, level, evidence=[{quote,locator}], rationale=...)`：level ∈ low_risk/some_concerns/high_risk/insufficient_evidence。**证据为空时引擎强制弃权**（selftest 演示请求 low_risk 但无证据被判 insufficient_evidence）。偏倚风险按该文献类型适用领域说明具体表现，区分明确存在/可能存在/未见迹象/证据不足。

**第 4 步 聚合与报告。** `python -m arkit.quality $WORK/scale.json $WORK/scale.json`：按显式规则出总等级（high if any high_risk；≥半数弃权→undetermined；全 low_risk→low；其余 moderate），附 derivation 推导行。据 scale 写 `appraisal.md`（维度-判断-证据-等级表 + 弃权项 + 推导）。

## 本题判据对齐（题面"三件事"原文）
1. **"每条判断是否对应原文可定位的证据片段"** → judge 强制 evidence 带 quote+locator（locator 必须可解析），无证据即弃权；评价表每条判断可逐条回溯到原文。
2. **"维度覆盖是否与该文献类型应有的检查点匹配"** → 量表按文献类型建立并落盘维度理由；摘要-only 文献自动大量弃权而非硬编。
3. **"评价结果能否被第二个人按记录独立复核并给出可比结论"** → scale.json 含全部证据与理由；聚合规则显式（AGGREGATION_RULE），derivation 行可手算复现。

## 交付物
* `appraisal.md`（评价表）、`scale.json`/`appraisal.json`（量表与聚合结果）、`prescan_full.json`（辅助观察）。

## 证据与审计规则
* 缺证据可弃权是核心能力：insufficient_evidence 是诚实结论，不是缺陷判决。
* 总等级不得孤立给出：必须附 derivation（各维等级→规则→总等级）。
* 证据片段必须真实存在于所标位置（可用 `arkit.locate verify_quote` 抽查）。
* 全文不可得/仅摘要/图表不可解析时，对应维度弃权并在 uncertainty 说明，不补齐判断。

## 异常处理
| 情况 | 处置 |
|---|---|
| 全文不可得/仅摘要 | 多数维度弃权，总等级可能 undetermined，如实报告 |
| 图表不可解析 | 相关维度降级或弃权，注明缺口 |
| 语言或预印本状态特殊 | 记 uncertainty，按可见文本评价 |
| 关键证据缺失 | judge 强制弃权；不硬编"未见迹象" |
| 人工复核分歧 | 在 scale.json 增 note 记录分歧与裁决，沉淀为判据改进 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：quality demo 演示证据锚定判断、无证据强制弃权、high_risk 聚合与 undetermined 结局；另含 10 个审查引擎模块 demo 与端到端合成案例。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-bace1c46/v2
