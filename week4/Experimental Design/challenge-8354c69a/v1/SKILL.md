---
name: anomaly-triage-forge
description: 实验结果解释与异常分析：结果趋势（走势/拐点/平台期/偏离幅度；依据区间对照拟合方式）、异常点定位（样本/批次/通道/孔位/时间维度；程度/阈值/与对照重复偏离关系）、原因候选（按证据强度排序；支持证据/排除证据；相关误当因果风险）。
---

# anomaly-triage-forge

## 核心原则（不可违反）
1. **果趋势**：单/多指标走势/拐点/平台期/偏离幅度判断；说明依据的区间/对照/拟合方式（stats_viz --descriptive + plan_engine --anomaly）。
2. **异常点**：样本/批次/通道/孔位/时间点维度定位；异常程度/判定阈值/与对照或重复的偏离关系（stats_viz --anomaly）。
3. **能原因**：按证据强度排序的原因候选清单；每条标支持证据/排除证据；把相关误当因果的风险标注（stats_viz --causes）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 趋势（0请求）：`python scripts/stats_viz_engine.py --descriptive data.json`
### 阶段2 异常定位（0请求）：`--anomaly data.json`
### 阶段3 原因候选（0请求+1-2请求补充证据）：`--causes data.json`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/anomaly-triage-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 阈值缺失 | 判定依据声明 |
| 原因无证据 | 弱证据排序降级 |
| 相关因果 | 风险显式 |

## 资源清单
scripts：stats_viz_engine.py, plan_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。