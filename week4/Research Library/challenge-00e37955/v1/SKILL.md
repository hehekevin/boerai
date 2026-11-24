---
name: library-general-forge
description: 资料管理领域总课题：按case路由（入库管理/知识库问答/软件操作/插件/迁移五子场景），组合引擎全链路。
---

# library-general-forge

## 核心原则（不可违反）
1. **四步保底**：明确任务范围→设计管理流程→每条结果带出处→异常显式说明。
2. **按子场景路由**：入库→classify_engine+clean_engine；问答→file_search+qa_engine；软件→sw_agent；插件→content_extract+multidb；迁移→increment_tracker+multidb。路由理由记录。
3. **每子场景独立可复跑**。
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
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/library-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合任务 | 串联分别报告 |
| 不适用 | anomalies 记录 |

## 资源清单
scripts：classify_engine.py, clean_engine.py, file_search.py, qa_engine.py, sw_agent.py, multidb_engine.py, increment_tracker.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。