---
name: iterative-search-agent
description: "Run an iterative search loop with a replayable ledger, signal-backed decisions, rollback and explicit stop/handoff criteria. Use when: a case asks to run an iterative search loop with a replayable ledger, signal-backed decisions, rollback and explicit stop criteria. NOT for: single-paper reading, writing, or black-box automation without logs."
---

# 文献检索 Agent 与自动迭代：找到文献，也保留筛选依据

面向"规划-执行-评估-迭代闭环，每轮决策有信号"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例要求以 Agent 闭环方式完成检索：规划、工具调用、评价、迭代、失败停止。
* 判定标准：闭环真跑起来并留可复跑轨迹；每轮继续/换策略/停止有评估信号；失败时回退或明确请求人工。

**不适用**：单篇阅读、写作、无日志的黑盒自动化。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、参考集、查询日志、引文图、PDF/表格等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/<主交付物> --artifact data=$WORK/<数据文件>
```

**第 1 步 规划。** qplan 拆子问题并定义每步完成判据；初始计划落盘。

**第 2 步 执行+账本。** 每轮写入 `ledger.json`：`{n, action, params, returned, new_items, kept, signal, decision}`——signal 与 decision 为空即协议违规。

**第 3 步 评估信号。** 每轮结束跑 `iterloop signals`：边际收益序列、覆盖率、预算消耗；决策必须与信号对应。

**第 4 步 停止与回退。** `iterloop stop` 给出触发理由；策略失败用 `iterloop rollback <round>` 回到上一可用状态，重跑必须引用回滚记录。

**第 5 步 人工介入。** 触发条件（目标模糊、证据冲突不可判、预算将尽且无进展）写成 handoff packet：当前状态、已得证据、待判问题。

## 本题判据对齐（题面原文的"三件事"）
1. **闭环真跑起来且留轨迹** → ledger.json 全字段非空，可复跑。
2. **每轮决策有信号支撑** → signals 输出与 decision 的对应逐轮可核对。
3. **失败回退或明确请求人工** → rollback/handoff 记录，而非硬凑完整结果。

## 交付物
* `plan.json`、`ledger.json`、`signals.json`、`stop.json`（或 rollback/handoff 记录）、`summary.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 工具/快照报错 | 账本记录失败轮与错误，decision=switch 或 handoff，不静默重试 |
| 连续零新增 | 触发 stop 判据；报告残余覆盖缺口 |
| 预算将尽 | 提前写 handoff packet |
| 回滚后重跑 | 新轮次引用 rollback 记录编号 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/agent-7d0e6569/v2
