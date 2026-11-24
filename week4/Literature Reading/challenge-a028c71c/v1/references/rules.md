# 规则（rules.md）— 文献阅读领域总课题

## 核心原则（不可违反）

1. **四步保底**：明确任务与范围→设计或改进阅读流程→每条结果保留来源与依据→无结果/冲突/缺失/权限显式说明。
2. **按子场景路由**：公式→math_audit；问答→qa_engine；结论数据→extraction_engine；溯源→verify_engine；比较→compare_matrix；清洗→clean_engine；分类→classify_engine；批注→annotation_engine；评测→bench_engine；网页→content_extract。路由理由记录。
3. **每子场景独立可复跑**；路由错误进 anomalies 不硬跑。
4. **脚本先行**；模型仅路由判断+成文。

## 异常处置

| 情形 | 处置 |
|-|-|
| 子场景无法判断 | 多引擎串联全跑，各环节分别报告 |
| 引擎不适用 | anomalies 记录不硬跑 |
| 材料为空 | gaps 声明部分交付 |

## 维护

版本 1.0.0（2026-11），作者 dafeiyu。引擎改动同步 examples 与本文件。