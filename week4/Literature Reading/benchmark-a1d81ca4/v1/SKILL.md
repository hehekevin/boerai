---
name: bench-toolkit-forge
description: 文献阅读 Benchmark 与评测工具。题卡字段校验（判得动）、统一运行器与复跑稳定性（得一致）、分数可追溯（查得回）、失败归因到题型（改得动）。触发词见核心原则。
---

# bench-toolkit-forge — 文献阅读 Benchmark 与评测工具

## 核心原则（不可违反）

1. **判得动**：题卡六字段（任务/输入材料/参考答案/评分规则/难度/数据授权）齐备；评分规则可机械判定或明确人工流程——不同人看同一输出给出同一结论。
2. **得一致**：固定工具权限与资源预算；复跑分数波动单独记录并解释。
3. **查得回**：每个分数顺题目ID可追到原始输出、运行配置、评分记录。
4. **改得动**：失败归到具体题型，转化为下一版专项题；只重算受影响分数。
5. **0/1/2 记分**：逐题得分+判分依据+争议标记（1分建议人工复核）。
6. **脚本先行**：validate-card/score/panel 恒为0模型请求。

## 运行环境约定

- 输入 `/input/case.json` 与 `/input/task.md`；材料以实际路径为准。工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段0 盘点（1请求）：`python scripts/inspect_case.py /input/case.json`
### 阶段1 题卡校验（0请求）：`python scripts/bench_engine.py --validate-card card.json`
### 阶段2 规则评分（0请求）：`python scripts/bench_engine.py --score rubric.json outputs.json`
### 阶段3 结果面板（0请求）：`python scripts/bench_engine.py --panel results.json`
### 阶段4 人工复核交接（1请求）：1分争议清单

### 交付阶段（0请求）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/bench-toolkit-forge.md --require "原则关键词,流程关键词,异常关键词" --names "p1,p2,p3"
```

主产物 `/app/output/bench-toolkit-forge.md`：每条结论带锚点。

## 异常处置速查（详见 references/rules.md）

| 情形 | 处置 |
|-|-|
| 题卡缺字段 | invalid+缺失清单，不评分 |
| 评分规则不可机械判定 | 转人工流程声明 |
| 复跑波动 | 波动记录+解释 |

## 资源清单

- `scripts/`：bench_engine.py；inspect_case.py、validate_result.py
- `references/rules.md`、`templates/result.schema.json`、`examples/minimal-example.md`、`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。确定性子命令恒为 0 请求；模型仅语义裁决与成文。过 60% 时间冻结：JSON 先落盘，status=partial。