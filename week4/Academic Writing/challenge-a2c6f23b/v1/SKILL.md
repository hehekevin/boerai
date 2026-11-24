---
name: writing-general-forge
description: 写作领域总课题：按case路由（结构优化/修订客户端/格式适配/汇报组织/长文档），组合第3周验证资产。
---

# writing-general-forge

## 核心原则（不可违反）
1. **四步保底**：明确任务与范围→设计或改进写作流程→每条改动/结论带依据→异常显式说明。
2. **按子场景路由**：结构→structure_audit；修订→revision_tracker；格式→format_spec；汇报→presentation_planner；长文档→thesis流程。路由理由记录。
3. **可追溯**：改动可接受/拒绝；论断指回原文。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点与路由（1请求）
### 阶段1-N 按路由执行（0请求/子命令）
### 阶段末 成文+契约核验

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/writing-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合任务 | 串联执行分别报告 |
| 引擎不适用 | anomalies 记录 |

## 资源清单
scripts：format_spec.py, presentation_planner.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。