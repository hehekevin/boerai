---
name: experiment-design-review-core
description: "Core engine for the experimental-design umbrella challenge: locator-bound plan structuring, six-facet constraint checklist with explicit unchecked items, exact-arithmetic resource/budget/schedule/booking/parameter-domain validation, risk register, version diff, and a computed feasibility verdict. Use when: a case in the experimental-design domain asks to generate, compare, review or explain plans and the concrete subtask is not known in advance. NOT for: executing experiments, literature review as the main deliverable, or any conclusion without source locators."
---

# 实验方案设计领域总课题：一套可复跑的审查底座

面向实验方案设计领域的开放性案例：生成、比较、审查、解释四类任务共用同一底座。本技能把共性簿记固化在引擎里：结构化抽取（带定位）、六面检查表（未查项显式列出）、资源/预算/时长/预约/参数域的精确算术核对、风险台账、版本差异与结论计算；Agent 按案例的具体问题裁剪检查表并逐项判定——**方案没写的内容绝不默认满足，结论永远可复跑**。

## 何时使用
* 用例属于实验方案设计领域但子题型开放：可能要求生成/优化方案、比较多版本候选、评估可行性或解释结果。
* 判定标准：输入输出明确、完成标准可核、适用边界写清、每条判断可独立复核。

**不适用**：以文献综述/数据分析/论文写作为主要交付物的任务；替代实验人员承担安全与伦理审批。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（方案、资源/价格/预约合同、数据材料等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 按子题型交付（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" review  --work "$WORK" --source <方案/结果文本>
# —— 按子题型选择下列路径，中间产物全部落盘 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact data=$WORK/checklist.json \
    --artifact result=$WORK/verdict.json
```

**第 0 步 识别子题型。** 从 task.md 判定本案例属于：A 生成/优化、B 比较选择、C 可行性审查、D 结果解释；在 summary.json 记录判定依据（引用 task.md 原句）。各路径共用底座，差异如下：

- **A 生成/优化**：产出方案必须是 typed 结构（planparse schema，每条带依据定位），`planparse validate` 通过后才允许进入检查表；迭代版本间跑 `plandiff diff` 留痕改动。
- **B 比较选择**：先冻结统一比较字段（criteria.json），逐方案同构审查填矩阵，choice.json 给入选依据与具体舍弃理由。
- **C 可行性审查**：六面 checklist + resources 四态核对 + verdict 计算（见第 1–4 步）。
- **D 结果解释**：解释台账（结论+阈值+数据行定位），异常映射具体失败模式（riskreg），复核步骤可执行。

**第 1 步 结构化与定位验证。** `review` 产候选；Agent 确认成 typed 结构并 `planparse validate`：无定位条目被驳回留痕。

**第 2 步 检查表。** 默认六面 12 项（设备/材料/时间/样本/伦理/安全）；子题型可裁剪（同 schema 改条目并记录裁剪理由）。逐项判定带 evidence（quote+locator）；conditional 必须写可执行条件；未查项显式列出。

**第 3 步 精确核对。** `resources materials`（四态+短缺量+采购价）、`check_budget`（求和 vs 预算）、`check_schedule`（逐步时长）、`check_booking`（预约窗）、`resources bounds`（有限参数域）——全部 Fraction/int 精确算术，比较携带双操作数+单位+定位。

**第 4 步 风险与结论。** `riskreg validate`（高风险无缓解被驳回；异常步骤必须映射具体失败模式）；`verdict build` 计算 可行/有条件可行/不可行/无法完整判定：有条件可行逐条列条件，未查项存在时不下可行性结论。

## 本题判据对齐（题面原文）
1. **"常见问题包括方案不可执行、参数依据不足、不同方案难以比较，以及异常结果缺乏解释路径"** → 四子题型共用底座：参数依据强制 locator（bounds 带域定位）、比较先冻结口径、异常必须映射具体失败模式。
2. **"实验人员可据此执行或明确知道缺什么"** → 四态资源核对（已具备/可外协/需采购/不具备）+ 未查项/缺失信息显式列出。
3. **"假设和边界可复核"** → 每条判定带 quote+locator；算术精确可手工复算。
4. **"不把未经确认的建议写成可执行事实"** → 确认项（安全/伦理/设备可用性/专家确认）一律走 checklist conditional/needs_review，条件逐条列出。

## 交付物
* 公共：`report.md`、`checklist.json`、`verdict.json`、`plan_candidates.json`。
* 按子题型：A `plan_struct.json`+`plandiff.json`；B `comparison_matrix.json`+`choice.json`；C `materials_check.json`+evidence_pack；D `ledger.json`+`risk_validation.json`。

## 证据与审计规则
* 无 quote+locator 不入册；验证器驳回的条目保留并注明原因。
* 精确算术：Fraction/int，float 拒绝；比较携带双操作数+单位+定位。
* 材料没有的内容不补：写 uncertainty，status 降级 partial 并在 limits 说明。
* 组织方合同为前瞻性计划情景，不冒充真实报价/审批/测量结果。

## 异常处理
| 情况 | 处置 |
|---|---|
| 子题型判定模糊 | 在 summary 写明判定依据与备选解释，按最保守路径（全检查表）执行 |
| 方案/数据缺页或无法解析 | 记 uncertainty，只处理可读部分，status=partial |
| 参数/资源信息缺失 | 对应检查项 needs_review 或 fail，绝不默认满足 |
| 方案自相矛盾 | 双摘录并列，相关检查项 fail |
| 检查表被裁剪 | 记录裁剪理由与未覆盖项，结论相应降级 |
| 超长文档 | 分段处理并在 limits 声明覆盖范围 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo + 一次端到端（合成案例 → probe → extract → review → 资源核对 → verdict → emit → result.json；含未检查项守卫路径）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-a57a8549/v2
