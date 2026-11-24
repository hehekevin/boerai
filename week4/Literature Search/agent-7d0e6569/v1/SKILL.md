---
name: iterative-search-agent-forge
description: 文献检索 Agent 与自动迭代。规划-执行-评估-迭代闭环，每轮工具调用留痕（参数/返回规模/失败原因），台账强制；四类停止判据（覆盖度/边际收益/预算/人工介入）脚本评估；回退点标记并保留已获证据；人工介入点可追溯可统计。触发词：检索Agent、自动迭代、停止条件、边际收益、回退。
---

# iterative-search-agent-forge — 文献检索 Agent 与自动迭代

一句话：**每轮留台账、停止有判据、回退保证据、介入可追溯。**

## 核心原则（不可违反）

1. **闭环五步**：规划→执行→评估→迭代→（停止或转人工）；每步有明确产出与完成判据，无判据不进入下一步。
2. **工具调用留痕**：每次调用的参数、目标库、返回规模、失败原因全部入台账；工具返回的原始结果不直接当结论，必须经覆盖率/去重审计。
3. **停止判据脚本化**：四类停止条件（覆盖度达标/边际收益趋零/预算耗尽/人工介入点）由 --stop 脚本评估，不凭感觉停止；避免过早收敛与无意义重复。
4. **回退保证据**：连续两轮边际收益为0 → 标记回退点，回到上一个可用状态或换备用路径；已获得证据全部保留。
5. **人工介入可追溯**：何时必须转人工、转交什么材料、人工判断如何回写轨迹——台账中 HUMAN: 前缀行标记，介入点可统计。
6. **脚本先行**：台账构建/停止评估/回退标记恒为0模型请求；模型只做策略调整与结论成文。

## 运行环境约定
- 输入：`/input/case.json` 与 `/input/task.md`；查询执行日志（TSV: round/query/db/hits/cost）以实际路径为准。
- 工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：构建迭代台账（0请求）
```bash
python <SKILL_DIR>/scripts/iter_loop.py --ledger <查询日志.tsv> > /app/work/ledger.json
```
台账字段：round/query/db/hits_raw/cost_min/cum_unique_est/marginal_gain。

### 阶段 2：停止条件评估（0请求）
```bash
python <SKILL_DIR>/scripts/iter_loop.py --stop /app/work/ledger.json > /app/work/stop.json
```
四类判据逐项评估，输出 stop_reasons 与 human_intervention_points。

### 阶段 3：回退点标记（0请求）
```bash
python <SKILL_DIR>/scripts/iter_loop.py --rollback /app/work/ledger.json > /app/work/rollback.json
```

### 阶段 4：语义评估与结论（约2-4次模型请求）
- 复核停止理由的语义合理性（如边际收益计算是否因去重口径失真）；
- 对未覆盖区间设计补充查询（若未停止）；
- 撰写检索结论：已获证据汇总+未覆盖缺口+建议。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：ledger、stop 评估、rollback 点、conclusions、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/iter-report.md --require "台账|ledger|轮次,停止|stop|判据,证据|evidence|回退|rollback" --names "ledger,stop,evidence"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 查询日志缺失/损坏 | gaps 声明；从 case.json 描述重建部分台账并标注"重建" |
| hits 字段缺失 | 该轮 marginal_gain 置 null，不参与停止判据 |
| 全程无人工介入点 | 报告"未触发介入条件"，不虚构 |
| 预算不足 | ledger/stop JSON 先落盘 status=partial |

## 资源清单
- `scripts/iter_loop.py` — 台账/停止评估/回退（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/agent-loop-rules.md` — 判据定义与介入协议
- `templates/result.schema.json`、`templates/ledger.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒/单响应16384 token。台账/停止/回退恒为0请求。过60%时间冻结：ledger+stop 先落盘 status=partial。