# 规则（rules.md）

## 核心原则（不可违反）
1. **四步保底**：明确任务范围→设计操作流程→每步结果带依据→异常显式说明。
2. **按子场景路由**：插件→content_extract+multidb；软件操作→sw_agent；资料库→classify_engine+clean_engine；知识库问答→file_search+qa_engine。路由理由记录。
3. **每子场景独立可复跑**；不适用进 anomalies。
4. **脚本先行**。

## 异常处置

| 情形 | 处置 |
|-|-|
| 混合任务 | 串联执行分别报告 |
| 引擎不适用 | anomalies 记录 |

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。