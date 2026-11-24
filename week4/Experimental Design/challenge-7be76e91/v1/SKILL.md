---
name: plan-compare-forge
description: 实验方案比较与选择：口径统一（目标/硬约束/变量/评价标准固定成可比字段再填表）、成本核算（机时/耗材/人力/样品准备/排期返工统一口径；一次性vs按次）、资源约束（设备档期/耗材货期/场地安全审批/人员技能时间窗——理论可行vs现在可做分开）。
---

# plan-compare-forge

## 核心原则（不可违反）
1. **径统一**：先固定研究目标/硬约束/变量/评价标准为可比字段，再逐方案填表——避免各方案各一套描述无法对照（plan_engine --compare）。
2. **间核算**：机时/耗材/人力/样品准备/设备排期/返工统一口径；总量与单位可核算；一次性投入vs按次消耗区分（plan_engine --cost）。
3. **源约束**：设备能力与档期/耗材可得性货期/场地安全审批/人员技能时间窗；"理论上可行"与"本实验室现在可做"分开（plan_engine --resources）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 可比矩阵（0请求）：`python scripts/plan_engine.py --compare plans.json`
### 阶段2 成本（0请求）：`--cost plans.json`
### 阶段3 资源约束（0请求）：`--resources proposal.json inventory.json`
### 阶段4 选择建议成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/plan-compare-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 口径不一 | 统一字段强制 |
| 档期冲突 | 约束清单 |
| 选择权衡 | 多字段显式权重 |

## 资源清单
scripts：plan_engine.py, ranking_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。