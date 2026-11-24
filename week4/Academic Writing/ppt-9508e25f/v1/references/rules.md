# 规则（rules.md）

## 核心原则（不可违反）
1. **按子场景路由**：生成与编辑→ppt_engine --outline/--edit；模板适配→--fit-template；论文转PPT→--outline/--density/--figures/--notes。路由理由记录。
2. **每子场景独立可复跑**；路由错误进 anomalies。
3. **脚本先行**；模型仅路由+成文。

## 异常处置

| 情形 | 处置 |
|-|-|
| 子场景混合 | 多引擎串联分别报告 |
| 不适用 | anomalies 不硬跑 |

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。