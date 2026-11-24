---
name: sw-plugin-general-forge
description: 科研软件插件与自动化总课题：按case路由（插件/软件操作/资料库/知识库问答），组合引擎全链路。
---

# sw-plugin-general-forge

## 核心原则（不可违反）
1. **四步保底**：明确任务范围→设计操作流程→每步结果带依据→异常显式说明。
2. **按子场景路由**：插件→content_extract+multidb；软件操作→sw_agent；资料库→classify_engine+clean_engine；知识库问答→file_search+qa_engine。路由理由记录。
3. **每子场景独立可复跑**；不适用进 anomalies。
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
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/sw-plugin-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合任务 | 串联执行分别报告 |
| 引擎不适用 | anomalies 记录 |

## 资源清单
scripts：sw_agent.py, content_extract.py, multidb_engine.py, classify_engine.py, file_search.py, qa_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。