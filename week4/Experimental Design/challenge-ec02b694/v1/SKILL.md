---
name: param-optimize-forge
description: 实验参数优化建议：域约束（设备手册/材料规格/安全阈值/历史实验→参数上下限/步进/互斥——可判定可行域非笼统经验值）、响应建模（口径/单位/测量/可接受波动；历史拟合/代理模型/经验规则来源声明；不确定性披露）、搜索策略（网格/序贯/贝叶斯/分阶段选择；初始点/每轮补点/利用上轮调整）。
---

# param-optimize-forge

## 核心原则（不可违反）
1. **域约束**：设备手册/材料规格/安全阈值/历史实验抽出参数上下限/步进/互斥关系——可判定可行域，非笼统经验值（stats_viz --paramdomain）。
2. **理建模**：响应指标口径/单位/测量方法/可接受波动；历史拟合/代理模型/经验规则来源声明；预测不确定性披露（stats_viz --searchplan 不确定性字段）。
3. **索策略**：网格/序贯/贝叶斯/分阶段筛选选择；初始点选择/每轮补点/上轮结果调整（stats_viz --searchplan）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 可行域（0请求）：`python scripts/stats_viz_engine.py --paramdomain specs.json`
### 阶段2 搜索策略（0请求）：`--searchplan domain.json`
### 阶段3 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/param-optimize-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 互斥参数 | 排除组合声明 |
| 响应噪声 | 贝叶斯推荐 |
| 不确定性 | 显式披露 |

## 资源清单
scripts：stats_viz_engine.py, plan_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。