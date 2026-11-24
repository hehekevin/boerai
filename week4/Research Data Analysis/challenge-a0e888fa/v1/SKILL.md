---
name: data-clean-forge
description: 科研数据清洗与处理：缺失处置（未检测/低于检出限/录入缺失/真值0区分；按分布量纲选策略）、重复识别（真实主键+大小写空格单位近似重复；保留依据）、单位转换（编码/分隔符/时区/混排/科学计数法/有效位；可逆或映射表——不静默丢精度）。
---

# data-clean-forge

## 核心原则（不可违反）
1. **值处置**：区分"未检测"/"低于检出限"/"录入缺失"/真值0——按字段分布与量纲选填补或标记；异常结合物理上下限与分布诊断（clean_engine --normalize）。
2. **录识别**：样品编号/时间戳/受试者标识等真实主键；大小写/空格/单位写法近似重复；明确保留哪条及依据（clean_engine --merge 显式键）。
3. **位转换**：编码/分隔符/日期时区/混排/科学计数法/单位换算/有效位——可逆或映射表留痕；不静默丢精度（clean_engine --units 公式+原值）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 规范化（0请求）：`python scripts/clean_engine.py --normalize`
### 阶段2 单位（0请求）：`python scripts/clean_engine.py --units`
### 阶段3 合并（0请求）：`--merge` + 追溯 `--trace`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/data-clean-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 未检测vs0 | 分级编码 |
| 转换不可逆 | 映射表保留 |
| 近似重复 | 键策略+依据 |

## 资源清单
scripts：clean_engine.py, stats_viz_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。