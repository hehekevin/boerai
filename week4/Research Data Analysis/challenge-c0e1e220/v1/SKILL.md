---
name: stats-interpret-forge
description: 统计分析与结果解读：描述统计（样本量/中心/离散/分位数/分布形态；缺失异常重复口径与单位）、推断统计（方法选择前提检验；多重比较/配对结构；避免误用）、效应量（匹配设计；口径方向置信区间）。
---

# stats-interpret-forge

## 核心原则（不可违反）
1. **述统计**：样本量/中心/离散/分位数/形态正确；缺失/异常/重复处理；每个统计量口径与单位说明（stats_viz --descriptive）。
2. **断统计**：按分布/样本量/设计选检验；先正态性/方差齐性；多重比较与配对处理；避免误用（stats_viz --testpick）。
3. **效应量**：与设计匹配的效应量（标准化均值差/解释比例/关联强度）；口径/方向/置信区间（stats_viz --effectsize）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 描述（0请求）：`python scripts/stats_viz_engine.py --descriptive data.json`
### 阶段2 选检验（0请求）：`--testpick`
### 阶段3 效应量（0请求）：`--effectsize`
### 阶段4 解读成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/stats-interpret-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 数据类型混列 | 类型过滤+标记 |
| 前提不满足 | 非参数替代 |
| 效应量缺CI | 标注缺失 |

## 资源清单
scripts：stats_viz_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。