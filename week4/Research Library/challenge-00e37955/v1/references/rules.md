# 规则（rules.md）

## 核心原则（不可违反）
1. **四步保底**：明确任务范围→设计管理流程→每条结果带出处→异常显式说明。
2. **按子场景路由**：入库→classify_engine+clean_engine；问答→file_search+qa_engine；软件→sw_agent；插件→content_extract+multidb；迁移→increment_tracker+multidb。路由理由记录。
3. **每子场景独立可复跑**。
4. **脚本先行**。

## 异常处置

| 情形 | 处置 |
|-|-|
| 混合任务 | 串联分别报告 |
| 不适用 | anomalies 记录 |

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。