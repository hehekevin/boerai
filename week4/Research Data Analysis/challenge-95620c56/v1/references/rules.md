# 规则（rules.md）

## 核心原则（不可违反）
1. **路由**：Agent→multistep；统计→stats-interpret；数据库→db-query；可视化→viz-advisor；代码→codegen；清洗→data-clean。理由记录。
2. **子场景独立复跑**。3. **脚本先行**。

## 异常处置

| 情形 | 处置 |
|-|-|
| 混合 | 串联分别报告 |
| 不适用 | anomalies |

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。