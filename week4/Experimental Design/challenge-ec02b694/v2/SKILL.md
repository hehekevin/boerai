---
name: bounded-parameter-optimization
description: "Parameter optimization advice strictly inside validated feasible domains: finite parameter domains extracted from equipment manuals/material specs/safety thresholds with locators, exact out-of-domain detection, exact cost/time accounting for candidate point sets, documented search strategy with convergence criteria, and risk handling for no-feasible-point or conflicting constraints. Use when: a case asks which parameter values to run, with what search strategy, under budget and throughput limits. NOT for: unconstrained single-metric optimization, surrogate-model claims without provided data, or recommendations outside declared domains."
---

# 实验参数优化建议：每条建议都落在可行域内

面向"参数怎么取值、怎么搜、成本多少"的任务。本技能的铁律是**域优先**：先从设备手册、材料规格、安全阈值与历史实验抽出有限可行域（上下限、步进、互斥关系，全部带来源定位），所有建议值经 `bounds` 精确核验——越界即 blocking，无域参数显式列出；搜索策略的每个候选点集用 `resources` 精确算机时/耗材/通量成本；收敛与停止判据落盘可复跑。

## 何时使用
* 用例给出设备量程、材料规格、安全阈值、预算/时间约束与（可能的）历史数据，要求给出关键参数建议值、允许浮动区间、响应指标口径、搜索策略与成本预算。
* 判定标准：建议值在真实可行域内；每条权衡有响应指标与成本口径支撑；整条链路可按记录复跑核对。

**不适用**：无约束单指标"最优"、脱离提供数据的代理模型宣称、越界推荐。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（设备手册/材料规格/安全阈值、价格与预约合同、历史实验记录等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" review  --work "$WORK" --source <手册/规格/历史数据文本>
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/optimization_report.md --artifact data=$WORK/domains.json \
    --artifact result=$WORK/recommendation.json
```

**第 1 步 抽可行域。** 整理 `domains.json`：每参数 `{lo, hi, step, unit, source, locator}`，来源标注设备手册/材料耐温/安全阈值/历史实验；互斥与耦合关系单列（如目标温度 × 材料耐温）。`planparse` 从材料文本抽参数候选，全部带定位。

**第 2 步 建议值核验。** `python "$SKILL/run.py" resources bounds recommendation.json domains.json`：每个建议值精确判断 in/out_of_domain，越界量精确（如 +5 ℃），双侧余量并列；**out_of_domain 的值不得作为建议输出，只能作为"冲突点"写进风险表**；无域参数显式列出并要求补域。

**第 3 步 成本与时间口径。** 候选点集 `check_schedule`（每点机时×点数，含换批/等待）、`check_budget`（耗材×点数+机时费精确合计 vs 预算）、`check_booking`（机时窗）；多目标取舍写明：成本受限时牺牲多少响应指标是可接受的，口径随结论落盘。

**第 4 步 搜索策略。** 在网格/序贯设计/分阶段筛选间选择并写清：初始点怎么选（域内锚点）、每轮补哪些点、利用上轮结果如何调整、什么时候停（收敛判据：如改进量 < 阈值 或预算耗尽）。策略参数（步长、每轮点数）全部落盘，第三人可复跑同一序列。

**第 5 步 风险与结论。** `riskreg` 登记：无可行解、约束冲突（目标温度 vs 材料耐温）、数据缺失、设备报错、指标互相矛盾——每条给降级（放宽哪条约束）、转人工或终止判据。`verdict build` 门控：越界/超预算/无域未处理 → 不可行；需补域/确认 → 有条件可行且条件逐条列出。

## 本题判据对齐（题面原文）
1. **"建议参数是否落在真实可行域内"** → bounds 精确核验，越界量与双余量并列，无域参数显式列出（selftest 演示 +5 ℃ 越界）。
2. **"每一条权衡是否有明确的响应指标与成本口径支撑"** → 响应指标写口径/单位/测量方法/可接受波动；成本用 Fraction 精确算，双操作数并列。
3. **"整条建议链路能否被他人按记录复跑并核对"** → 域、点集、策略参数、停止判据全部 JSON 落盘；算术可手工复算。
4. **"推荐值越界，超出设备量程、材料耐温或安全阈值却不作提示"** → 越界即 blocking 事实（含两侧操作数与来源定位），不是脚注。
5. **"搜索策略没有收敛依据，候选点怎么选、什么时候停、停在哪一步都说不清"** → 策略文档强制初始点/补点规则/停止判据三要素。

## 交付物
* `optimization_report.md`、`domains.json`（可行域+来源）、`recommendation.json`（建议值+bounds 核验结果）、`strategy.json`（搜索策略+收敛判据）、成本包（schedule/budget/booking）、`risk_register.json`、`verdict.json`。

## 证据与审计规则
* 可行域每条边界带来源定位；无来源的域不用于放行建议。
* 算术精确（Fraction/int）；成本/时间比较携带双操作数+单位。
* 预测不确定度如实披露；历史数据拟合只基于案例提供的数据，不编造实验点。
* 材料没有的内容写 uncertainty，status 降级 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 无可行解（约束冲突） | 输出冲突双操作数+降级路径（放宽哪条约束），转人工判据写明 |
| 域缺失/单位不一致 | 参数显式列 no_domain/unit_mismatch，不得默认在域内 |
| 历史数据不足 | 策略降级为分阶段筛选并声明不确定度 |
| 成本超限 | 给出减点方案（牺牲哪些点、损失多少指标），精确算账 |
| 指标互相矛盾 | 并列两指标口径与证据，不强行合成单一分数 |
| 设备报错/中途失败 | 止损点与重跑规则写入 strategy.json |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo（含 +5 ℃ 越界、预约窗 slack=-5 天、float 拒绝）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-ec02b694/v2
