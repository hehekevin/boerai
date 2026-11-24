---
name: plan-feasibility-review
description: "Feasibility review of an experimental plan under equipment/material/time/sample/ethics/safety constraints: locator-bound plan structure, exact-arithmetic resource cross-check (quantities, prices, durations, booking windows), risk register, and a computed feasible/conditional/infeasible verdict with every condition enumerated. Use when: a case asks to audit a concrete experimental plan's feasibility against provided inventories, price catalogs and booking contracts, and deliver an executable conclusion. NOT for: executing experiments, data analysis, literature review, or writing papers."
---

# 实验方案可行性评估：落到清单行，也给出可执行结论

面向"审一份具体方案能不能开工"的任务。本技能把审查拆成确定性簿记（引擎）与语义判断（Agent）：引擎负责结构抽取（每条带原文定位）、六面 12 项检查表（未查项显式列出，绝不默认满足）、资源/价格/时长/预约窗的精确算术核对（Fraction/int，拒绝 float）、风险台账验证与结论计算；Agent 负责阅读方案与案例材料、逐项判定并带证据落盘——全程 JSON，第三人可按记录复算。

## 何时使用
* 用例给出一份实验方案（含 3 个版本候选）与组织方提供的资源/价格/预约合同、设备清单、SOP、审批材料，要求逐项审查设备、材料、时间、样本、伦理、安全约束并给出可行/有条件可行/不可行结论。
* 判定标准：每条判断落到方案章节、参数和清单行；"有条件可行"逐条写清条件；未检查项显式列出。

**不适用**：实验执行、数据分析、文献综述、论文写作。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（方案文档、设备清单、价格/采购目录、预约合同、SOP、审批表单等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" review  --work "$WORK" --source <方案文本>   # 每个方案版本各跑一次
# —— Agent 逐项判定并落盘（见下），引擎命令全部可复跑 ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/review_report.md --artifact data=$WORK/checklist.json \
    --artifact result=$WORK/verdict.json
```

**第 1 步 方案结构化。** `review` 产出 `plan_candidates.json`（章节/参数/步骤/资源候选，全部带行定位）。Agent 确认后整理成 typed 结构 `plan_struct.json`（sections/parameters/steps/resources/controls/variables），并跑 `python "$SKILL/run.py" planparse validate plan_struct.json <方案文本>`：**无定位或定位不可解析的条目被驳回留痕**。

**第 2 步 六面检查表。** `checklist.json` 12 项（设备 2/材料 2/时间 2/样本 2/伦理 2/安全 2）初始全部 unchecked。Agent 逐项 `checklist set`：pass/fail/conditional/needs_review/not_applicable，fail/conditional 必须带 evidence（quote+locator），conditional 必须写可执行条件。**没写进方案的内容标 fail 或 needs_review，绝不留 unchecked 进结论**；确因材料缺失查不了的，留 unchecked 并在结论中显式列出。

**第 3 步 资源精确核对。** Agent 从方案与案例合同整理 `requirements.json`（qty/unit/locator），然后：
- `python "$SKILL/run.py" resources materials requirements.json <库存.json> <价格目录.json|-> materials_check.json`：四态（已具备/可外协/需采购/不具备），短缺量与采购价为精确 Fraction，单位不匹配显式报错；
- 预算：`resources.check_budget`（逐项 total_price 求和 vs 预算，双操作数并列）；
- 时长：`resources.check_schedule`（逐步时长求和 vs 窗口；无时长步骤显式列出）；
- 预约：`resources.check_booking`（earliest_slot vs needed_by，slack 天数带正负号）；
- 参数域：`resources bounds params.json domains.json`（有限可行域 [lo,hi]，越界量精确，无域参数显式列出）。

**第 4 步 风险台账。** 按方案异常步骤登记 `risk_register.json`（failure_mode/likelihood/impact/mitigation/contingency/locator/addresses_step），`riskreg validate`：**高风险无具体缓解/降级路径被驳回；异常处置步骤未映射具体失败模式被列出**。

**第 5 步 版本比较（3 个候选版本）。** `python "$SKILL/run.py" plandiff diff v1.json v2.json [out.json]`：新增/删除/变更带双版本定位；任何内容变更 → 检查表必须重跑，不得沿用旧结论。

**第 6 步 结论计算。** 汇总 evidence_pack.json（materials/budget/schedule/bookings/bounds/risk_validation），`python "$SKILL/run.py" verdict build checklist.json evidence_pack.json verdict.json`：有未查项 → 无法完整判定；有 fail/不具备/超预算/排期违约/越界/高风险无缓解 → 不可行（blocking 逐条带操作数）；否则有条件 → **有条件可行且条件逐条列出**；全通过 → 可行。结论写入 review_report.md。

## 本题判据对齐（题面原文）
1. **"审查是否真正落到方案的具体章节、参数和清单行"** → 每条 evidence 强制 quote+locator；planparse.validate 驳回无定位条目；资源核对每行带双侧定位。
2. **"结论是否可执行，即'有条件可行'能不能写清是有哪些条件"** → verdict 从 conditional 检查项与需采购/外协资源逐项生成条件串（含数量、价格、货期算式），不接受"建议进一步确认"式空话。
3. **"同一份方案换一个人按记录复跑，能否得到可比较的结论"** → 全部中间产物 JSON 落盘；算术精确（Fraction/int）；plandiff 区分"方案改了"与"审查判错"。
4. **"是否把'方案没写'误当成'方案满足'"** → checklist 初始全 unchecked；verdict 对未查项只给"无法完整判定"并逐条列出（selftest 含此守卫路径）。

## 交付物
* `review_report.md`（结论+条件+驳回/未查项）、`verdict.json`、`checklist.json`、`materials_check.json`（含 budget/schedule/booking/bounds 证据包）、`risk_register.json`+`risk_validation.json`、`plan_struct.json`（各版本）+`plandiff.json`。

## 证据与审计规则
* 无 quote+locator 的判定不得入表；验证器驳回的条目保留并注明原因。
* 数字一律精确：数量/价格/时长/日期用 Fraction/int 或 ISO 日期；引擎拒绝 float。
* 每次比较携带两个操作数+单位+来源定位；单位不匹配显式报错，不做隐式换算。
* 方案/材料没写的内容不补：写 uncertainty，status 降级 partial 并在 limits 说明。
* 组织方合同是前瞻性计划情景，不冒充真实报价/审批结果；不确定处如实标注。

## 异常处理
| 情况 | 处置 |
|---|---|
| 方案缺页/扫描件无文本 | 记 uncertainty，只审可读部分，对应检查项 needs_review，status=partial |
| 参数缺失/无依据 | 对应检查项 fail 或 needs_review，不得默认在可行域内 |
| 设备信息不明（无型号/量程） | eq-presence 标 needs_review 并写明缺哪一项 |
| 伦理状态未定 | ethics-approval 标 needs_review，结论最多"有条件可行"且条件含审批落实 |
| 方案自相矛盾 | 两处摘录并列入 evidence，相关检查项 fail |
| 库存/价格/合同缺行 | resources 显式报 unavailable/no entry，短缺量照算，不补造来源 |
| 超长文档 | 分段 review 并在 limits 声明实际覆盖范围 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo（含"未检查项→无法完整判定"守卫、精确算术断言）+ 一次端到端（合成方案/库存/价格目录 → probe → extract → review → 逐项填表 → 资源核对 → verdict=有条件可行且条件逐条列出 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-2e2c5820/v2
