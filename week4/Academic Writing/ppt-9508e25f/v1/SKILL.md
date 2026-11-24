---
name: ppt-general-forge
description: PPT领域总课题：按case路由（生成/模板/论文转PPT三子场景），全链路可追溯。
---

# ppt-general-forge

## 核心原则（不可违反）
1. **按子场景路由**：生成与编辑→ppt_engine --outline/--edit；模板适配→--fit-template；论文转PPT→--outline/--density/--figures/--notes。路由理由记录。
2. **每子场景独立可复跑**；路由错误进 anomalies。
3. **脚本先行**；模型仅路由+成文。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点与路由（1请求）
### 阶段1-N 按路由执行（0请求/子命令）
### 阶段末 成文+契约核验

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/ppt-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 子场景混合 | 多引擎串联分别报告 |
| 不适用 | anomalies 不硬跑 |

## 资源清单
scripts：ppt_engine.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。