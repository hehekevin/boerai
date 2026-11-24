---
name: stats-methods-review-forge
description: 研究方法与统计审查：设计匹配（设计类型vs研究问题；对照/分组/盲法/偏倚；主要终点事先明确）、变量定义（暴露/结局/协变量编码一致；切点/换算/缺失依据）、统计方法（检验vs数据结构/分布/独立性；多重比较/重复测量/敏感性）。
---

# stats-methods-review-forge

## 核心原则（不可违反）
1. **计审查**：设计类型与研究问题匹配；对照设置/分组/盲法/偏倚控制成立；主要终点与假设事先明确（review_engine --stats）。
2. **义审查**：暴露/结局/协变量/分组变量定义测量编码一致；分类切点/单位换算/缺失处理有依据；变量类型与检验匹配（review_engine --variables）。
3. **法审查**：检验方法与数据结构/分布假设/样本独立性匹配；多重比较/重复测量/交互项/敏感性分析正确处理（review_engine --methods）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1-3 三线审查（0请求）：`--stats` + `--variables` + `--methods`
### 阶段4 审查报告（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/stats-methods-review-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 设计问题不匹配 | mismatch 判定+依据 |
| 切点无依据 | 列为审查发现 |
| 多重比较未校正 | 报告缺陷 |

## 资源清单
scripts：review_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。