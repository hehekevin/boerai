---
name: multistep-analysis-forge
description: 多步骤数据分析Agent：多源对齐（字段名/类型/单位量纲/跨表主键——可核对差异报告）、异常处理规则（缺失/异常/重复——优先级+行数分布影响记录不静默丢）、假设校验（方法选择依据+前提检验）。
---

# multistep-analysis-forge

## 核心原则（不可违反）
1. **段对齐**：多表/多来源/多版本读入；字段名不一致/类型混淆/单位量纲/跨表主键对齐——输出可核对的差异报告（multidb_engine --merge + clean_engine --normalize）。
2. **常处理**：缺失填补/删除、异常判定、重复合并的规则与优先级；每步行数与分布影响记录——不静默丢数据（clean_engine trace）。
3. **设校验**：按数据结构选方法；前提校验（分布/独立性/样本量/多重比较）；选择依据说明（stats_viz --testpick）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 对齐（0请求）：`python scripts/multidb_engine.py --merge`
### 阶段2 清洗留痕（0请求）：`python scripts/clean_engine.py --normalize/--merge/--trace`
### 阶段3 假设校验（0请求）：`python scripts/stats_viz_engine.py --testpick`
### 阶段4 成文（2-3请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/multistep-analysis-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 主键对不齐 | 差异报告+人工核对队列 |
| 静默丢行 | trace审计FAIL |
| 前提不满足 | 非参数替代建议 |

## 资源清单
scripts：multidb_engine.py, clean_engine.py, stats_viz_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。