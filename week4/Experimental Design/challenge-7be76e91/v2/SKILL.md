---
name: plan-comparison-choice
description: "Side-by-side comparison and defensible choice among candidate experimental plans: unified comparable fields, exact per-plan cost/time arithmetic against case-provided resource/price/booking contracts, feasibility verdict per plan, version diff, and an explicit rejection reason for every non-chosen plan. Use when: a case provides several candidate plan versions plus inventories, price catalogs and booking contracts and asks for a justified choice. NOT for: inventing new plan designs, data analysis, or cost estimates without source numbers."
---

# 实验方案比较与选择：统一口径，给出可辩护的选择

面向"三到五条候选路线选一个并说明舍弃理由"的任务。本技能先把研究目标、硬约束、变量与评价标准固定成可比字段，再逐方案填同一张表：引擎负责结构化抽取（带定位）、逐方案精确成本/时间/资源核对（Fraction/int）、可行性结论计算与版本差异；Agent 负责逐项判定与最终选择论证——结论必须挂来源，舍弃理由必须具体。

## 何时使用
* 用例给出同一目标的多个候选方案（通常 3 个版本化候选）与资源/价格/预约合同，要求横向比较并给出选择与舍弃理由。
* 判定标准：所有候选共用一套可比字段；成本时间可核算；可行性与"本实验室现在可做"分开；每个判断有来源。

**不适用**：方案原始设计创新、单篇文献综述、实验数据统计建模。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（各候选方案、设备清单、价格/采购目录、预约合同、预实验记录等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# 对每个候选方案 i=1..N：
python "$SKILL/run.py" review  --work "$WORK/plan$i" --source <方案i文本>
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/comparison_report.md --artifact data=$WORK/comparison_matrix.json \
    --artifact result=$WORK/choice.json
```

**第 1 步 固定比较口径。** 从 task.md 与 case.json 抽出研究目标、硬约束（预算/截止/安全红线）、评价字段：设备机时、耗材成本、人力工日、时间窗口、参数窗口、风险等级、证据强度——写成 `criteria.json`，逐字段注明来源定位；此后所有方案用同一张表，**禁止各方案各用一套结构**。

**第 2 步 逐方案同构审查。** 每个候选跑 `review` → typed 结构 → 同一张 `checklist.json`（六面 12 项）→ 同一套资源核对命令（`resources materials` / `check_budget` / `check_schedule` / `check_booking` / `resources bounds`）。**成本口径统一**：机时费+耗材费+一次性投入分列，时间口径含样品准备、排期、表征排队与返工余量；所有数为精确 Fraction 并带来源定位。

**第 3 步 可行性分级。** 每方案 `verdict build` 得到 可行/有条件可行/不可行/无法完整判定 及条件清单。"理论上可行"与"本实验室现在可做"分开：有 blocking（不具备资源/超预算/排期违约/参数越界）的方案不得进入"可直接执行"档。

**第 4 步 版本差异（同一方案的 3 个版本）。** `plandiff diff v1.json v2.json`：新增/删除/变更带双版本定位；有内容变更的版本对必须重跑检查表，不得沿用旧结论。

**第 5 步 选择与舍弃理由。** `comparison_matrix.json` 逐行是方案、逐列是统一字段（每格带数值+单位+来源定位）。`choice.json` 记录：入选方案、逐项胜出依据、**每个落选方案的具体舍弃理由**（引用其 blocking/条件/成本差，禁止"综合考虑"式空话）、敏感性说明（哪些条件变化会翻转结论）。

## 本题判据对齐（题面原文）
1. **"把候选方案各自描述一遍却没有可比字段，三个方案用三套结构"** → criteria.json 先冻结字段，逐方案填同一矩阵，缺数据的格子显式写"未提供"并计入 uncertainty。
2. **"不核对本实验室设备是否具备、耗材是否在预算内"** → resources 四态核对（已具备/可外协/需采购/不具备）+ check_budget 精确剩余，双操作数并列。
3. **"时间成本只算实验执行……成本只写耗材单价，漏掉机时费与人力工日"** → check_schedule 逐步求和（含排期/周转），check_booking 机时费精确计入，预算合计含全部行项。
4. **"风险写成'存在一定风险'，没有触发条件、后果量级和缓解措施"** → riskreg 强制具体 failure_mode 与 likelihood/impact 分级，高风险无缓解被驳回。
5. **"参数范围没有来源"** → bounds 的每个可行域必须带 locator；无域参数显式列出。
6. **"给出一个可辩护的选择，以及一个具体的舍弃理由"** → choice.json 的舍弃理由必须引用落选方案的 blocking 事实或条件差异。

## 交付物
* `comparison_report.md`、`comparison_matrix.json`（统一字段矩阵）、`choice.json`（选择+舍弃理由+敏感性）、每方案 `checklist.json`/`verdict.json`/`materials_check.json`、版本间 `plandiff.json`。

## 证据与审计规则
* 矩阵每格带数值+单位+来源定位；无来源的格写"未提供"，不得编造。
* 算术精确（Fraction/int），float 被拒绝；成本/时间比较携带两个操作数。
* 选择结论的强度由证据决定：证据不足时在 uncertainty 声明，status 可降级 partial。
* 组织方合同为前瞻性计划情景，不冒充真实报价；敏感性说明如实给出。

## 异常处理
| 情况 | 处置 |
|---|---|
| 某方案字段缺失 | 矩阵该格"未提供"，对应检查项 needs_review，参与比较但不补造 |
| 候选方案数量与题述不符 | 按实际数量建矩阵并在 limits 说明 |
| 两版方案差异极小 | plandiff 如实报 changed 字段；结论仍需重跑验证 |
| 成本口径无法统一 | 分行列报（一次性/按次），不强行合计不同口径 |
| 全部方案均不可行 | 如实输出 choice=none_viable + 各方案 blocking，不硬选 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo + 一次端到端（合成案例 → probe → extract → review → 资源精确核对 → verdict → emit → result.json），plandiff demo 演示版本变更强制重跑。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-7be76e91/v2
