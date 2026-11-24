---
name: deep-research-general-forge
description: 深度研究与文献综述总课题：按case路由（综述生成/深度Agent/系统综述/趋势分析），组合引擎。
---

# deep-research-general-forge

## 核心原则（不可违反）
1. **四步保底**：明确任务→设计流程→结果带依据→异常显式。
2. **路由**：综述→review-synthesis；Agent→deep-research-agent；系统综述→systematic-review；趋势→trend-analysis。理由记录。
3. **子场景独立复跑**；不适用进 anomalies。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 路由（1请求）
### 阶段1-N 执行（0请求/子命令）
### 阶段末 成文

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/deep-research-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合 | 串联分别报告 |
| 不适用 | anomalies |

## 资源清单
scripts：screening_engine.py, question_decompose.py, iter_loop.py, stats_viz_engine.py, ranking_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。