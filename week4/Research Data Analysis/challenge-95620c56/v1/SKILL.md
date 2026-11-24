---
name: analysis-general-forge
description: 科研数据分析总课题：按case路由（多步骤Agent/统计解读/数据库查询/可视化/代码/清洗），组合引擎。
---

# analysis-general-forge

## 核心原则（不可违反）
1. **路由**：Agent→multistep；统计→stats-interpret；数据库→db-query；可视化→viz-advisor；代码→codegen；清洗→data-clean。理由记录。
2. **子场景独立复跑**。3. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 路由（1请求）
### 阶段1-N 执行
### 阶段末 成文

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/analysis-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合 | 串联分别报告 |
| 不适用 | anomalies |

## 资源清单
scripts：multidb_engine.py, clean_engine.py, stats_viz_engine.py, sw_agent.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。