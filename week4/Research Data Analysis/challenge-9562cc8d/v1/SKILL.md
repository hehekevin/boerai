---
name: viz-advisor-forge
description: 科研数据可视化：图表选择（数据类型×分析目的→图型+推荐理由）、编码方式（位置/长度/角度/面积/颜色/形状/分面映射；类别过多/量纲差异/双轴/对数变换；避免面积误编码）、轴标目与图注（单位/图例/误差线定义/显著性/样本量/方法——图注独立可读）。
---

# viz-advisor-forge

## 核心原则（不可违反）
1. **表选择**：数据类型（连续/分类/时序/多变量/分组）×目的（分布/比较/相关/趋势/构成）→可选图型+推荐理由（stats_viz --chartpick）。
2. **码方式**：位置/长度/角度/面积/颜色/形状/分面映射；类别过多/量纲差异大/双轴/对数变换处理；**避免面积编码比较**（chartpick 警告）。
3. **与图注**：轴标目/单位/图例/误差线定义/显著性标记/样本量/方法说明——图注独立于正文被读懂（stats_viz --caption）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 选图（0请求）：`python scripts/stats_viz_engine.py --chartpick data.json`
### 阶段2 图注校验（0请求）：`python scripts/stats_viz_engine.py --caption meta.json`
### 阶段3 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/viz-advisor-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 类别过多 | 横置/分面/聚合警告 |
| 误差线未定义 | missing 标记 |
| 双轴组合 | 对齐警告 |

## 资源清单
scripts：stats_viz_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。