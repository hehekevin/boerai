---
name: plan-generate-validate
description: "Generate and iteratively revise an experimental plan as a typed, locator-bound structure that must pass validation before it can be called executable: operational variables, controls, steps bound to exact equipment/consumables, exact time and budget arithmetic, parameter domains with sources, risk register with concrete failure modes, and a computed readiness verdict. Use when: a case asks to turn a research goal into an executable, schedulable plan under given resource/price/booking contracts. NOT for: literature review, data analysis, or replacing safety/ethics review by lab staff."
---

# 实验方案生成与优化：写出来，也经得起核对

面向"把研究目标变成能排期、能执行、能被评审的方案"的任务。本技能的硬约束是：**生成的方案必须先通过引擎验证才能宣称可执行**——每条参数/步骤/资源带依据定位（无定位被驳回），设备耗材落到型号规格并对库存/价格/预约合同做精确核对，参数区间带来源，风险台账的异常处置映射具体失败模式，最终 readiness 结论由 verdict 计算而非文字宣称。

## 何时使用
* 用例给出研究目标、约束（预算/时间/设备/材料合同），要求生成或迭代优化一份实验方案，明确假设、变量、对照、步骤、参数、资源、判读标准与异常处置。
* 判定标准：方案六要素齐备（假设与变量/对照组/设备材料/时间成本/参数范围/风险和异常）；每条参数有依据；能排期能报价。

**不适用**：文献综述、数据分析建模、论文写作；替代安全与伦理审批责任。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（目标与约束、设备清单、价格/预约合同、预实验记录等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" review  --work "$WORK" --source <约束与材料文本>   # 提取可用资源候选
# —— Agent 生成方案 → 引擎验证 → 迭代，全程落盘 ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/plan.md --artifact data=$WORK/plan_struct.json \
    --artifact result=$WORK/verdict.json
```

**第 1 步 目标→假设→变量。** 从 task.md 抽取研究目标，落成可检验假设；每个变量给操作定义、测量方式、单位、取值范围，标明自变量/因变量/混杂因素。全部条目带依据定位（case 材料或标注为假设）。

**第 2 步 方案生成（typed 结构）。** 方案以 planparse schema 输出 `plan_struct.json`：steps 绑定设备型号/量程/耗材规格；parameters 含单位与允许区间及依据来源；controls 说明每个对照排除哪类混杂（避免只有空白组）；判读标准可执行。同步写人类可读 `plan.md`。**每一步资源引用须与案例提供的清单/合同一致。**

**第 3 步 引擎验证门。** 
- `python "$SKILL/run.py" planparse validate plan_struct.json <依据文本>`：无定位条目被驳回；
- `resources materials / check_budget / check_schedule / check_booking`：数量、总价、总时长、预约窗精确核对，四态标明已具备/可外协/需采购/不具备；
- `resources bounds params.json domains.json`：每个参数落在声明的有限可行域内，域带来源（设备手册/预实验/文献），越界即 blocking；
- `riskreg validate`：每个预设失败模式（污染/无信号/重复性差/样本不足等）有判据、止损点与替代路径；高风险必须有具体缓解。

**第 4 步 迭代留痕。** 每次修订产新版本结构，`plandiff diff v_old.json v_new.json`：改动逐条带双版本定位；有内容变更必须重跑验证门，不得沿用旧结论。

**第 5 步 readiness 结论。** `checklist`（六面 12 项）逐项判定后 `verdict build`：方案只有拿到 可行/有条件可行（条件逐条列出）才能交付为"可执行"；未查项存在 → 无法完整判定，方案按"草稿+缺口清单"交付。

## 本题判据对齐（题面原文）
1. **"方案读起来像教科书目录，实验人员却无法据此排期"** → 方案以 typed 结构生成，步骤绑定型号/规格/时长，check_schedule 精确求和使方案可排期。
2. **"变量只有名字没有操作定义……参数不写量程与单位"** → 变量/参数条目强制单位+取值范围+依据定位；validate 驳回无定位条目。
3. **"对照只有空白组没有阳性对照"** → controls 逐条注明排除的混杂类型，单一对照在检查表中标 issue。
4. **"设备与耗材不落到型号和规格……时间与预算估算缺失"** → resources 四态核对+budget 精确合计，双操作数+单位+定位。
5. **"风险与异常处置只写一句'注意安全'"** → riskreg 的 GENERIC 词表驳回空泛 mitigation；异常处置必须映射具体失败模式。
6. **"涉及主观判断时，须写明参考答案、来源定位、可接受范围和不确定性"** → 每条判断带 evidence+locator，不确定性写 uncertainty。

## 交付物
* `plan.md`+`plan_struct.json`（typed 方案）、`validation.json`（planparse 验证）、`materials_check.json`+`budget/schedule/booking/bounds`、`risk_register.json`+`risk_validation.json`、`checklist.json`、`verdict.json`、迭代间 `plandiff.json`。

## 证据与审计规则
* 生成内容的每条参数/资源引用必须能定位到案例材料；定位缺失即驳回，不允许"看似合理"。
* 算术精确（Fraction/int）：预算、时长、机时费可手工复算。
* 无法从材料确认的内容标为假设或写入 uncertainty，不得写成已确认事实。
* 组织方合同为前瞻性计划情景，不冒充真实报价/审批。

## 异常处理
| 情况 | 处置 |
|---|---|
| 约束缺失（无预算/无截止） | 相应检查项 needs_review，方案标注假设值与依据 |
| 设备/材料不可得 | 给可外协/替代项并标四态；无替代则如实报不具备 |
| 参数依据不足 | 标假设+建议预实验确认，不得伪引来源 |
| 生成与合同冲突（超预算/排期违约） | 降级设计或如实报 blocking，不隐瞒 |
| 迭代后旧结论失效 | plandiff 强制重跑验证门并在报告说明 |
| 验证门不通过 | 按草稿+缺口清单交付，status=partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo + 一次端到端（合成约束 → probe → extract → review → 精确核对 → verdict → emit → result.json；含无定位条目被驳回演示）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-cf1995b5/v2
