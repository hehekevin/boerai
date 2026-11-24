---
name: data-cleaning-forge
description: 文献数据清洗与标准化。编号规则库（R1-R4含优先级/适用条件/失效情形），字段映射（同义列名+未映射清单），单位换算保留原值+公式+精度（未收录单位不改值入人工表），可解释合并键（同物质+同实验才合并），每个改动沿规则编号→输入行→原始文献追溯。触发词：数据清洗、规则库、单位换算、字段映射、追溯。
---

# data-cleaning-forge — 文献数据清洗与标准化

一句话：**规则有编号、换算留公式、合并防错并、改动可回溯。**

## 核心原则（不可违反）

1. **规得齐**：同一指标统一字段名/数据类型/允许值集合——靠编号规则库（R1字段改名/R2类型转换/R3枚举归一/R4缺失与未知区分）而非人记；未映射字段进 unmapped 清单。
2. **换得准**：单位换算保留原值+写出公式+精度；复合单位/数量级前缀/区间值按表逐段处理；**未收录单位不改值**，列入 needs_manual。
3. **合得对**：合并按可解释判定键（同物质+同实验标识）；字段冲突保留记录——**不同实验/不同物质绝不合并**。
4. **追得回**：每个改动值沿 规则编号→输入行→原始文献 回溯；缺规则编号或缺行定位=审计FAIL。
5. **脚本先行**：normalize/units/merge/trace 恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：字段规范化（0请求）
```bash
python <SKILL_DIR>/scripts/clean_engine.py --normalize <记录.json> > /app/work/normalized.json
```

### 阶段 2：单位换算（0请求）
```bash
python <SKILL_DIR>/scripts/clean_engine.py --units <数值清单.json> > /app/work/units.json
```

### 阶段 3：可解释合并（0请求）
```bash
python <SKILL_DIR>/scripts/clean_engine.py --merge /app/work/normalized.json > /app/work/merged.json
```

### 阶段 4：追溯审计（0请求）
```bash
python <SKILL_DIR>/scripts/clean_engine.py --trace /app/work/normalized.json
```

### 阶段 5：成文与交付（约1-2次模型请求）
模型复核 needs_manual 单位与合并边界；组装 result.json（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/cleaning-report.md --require "规则|rule|编号|R\d,换算|unit|单位|公式,合并|merge|键|key,追溯|trace|回溯" --names "rules,units,merge,trace"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 未映射字段 | unmapped 清单显式列出，不猜 |
| 未收录单位 | needs_manual 表，保留原值 |
| 类型转换失败 | 保留原值+cast_failed 标记 |
| 合并键字段缺失 | 该记录保持独立（不并入） |
| 预算不足 | normalized.json 先落盘 status=partial |

## 资源清单
- `scripts/clean_engine.py` — normalize/units/merge/trace（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/cleaning-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。四子命令恒为0请求。过60%时间冻结。