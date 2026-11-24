---
name: quality-bias-forge
description: 文献研究质量评价：量维度条目化（设计/样本/测量/统计/报告完整性；判定所需证据明确）、据定位（句子/表格级+页码章节图表）、偏倚风险（按文献类型选领域；明确存在/可能存在/未见迹象/证据不足四档）。
---

# quality-bias-forge

## 核心原则（不可违反）
1. **量维度**：设计/样本与抽样/测量与结局/统计分析/报告完整性拆成可判断条目；每条明确所需证据与判定情形（review_engine --stats+--variables）。
2. **据定位**：章节级→句子/表格级；保留原文表述+页码/章节/图表编号——判断可逐条回溯（claim_evidence 锚点）。
3. **倚风险**：按文献类型选偏倚领域；四档判定（明确存在/可能存在/未见迹象/证据不足）——不判"不存在"（review_engine --bias）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 条目审查（0请求）：`python scripts/review_engine.py --stats/--variables`
### 阶段2 偏倚（0请求+1-2请求领域表现描述）：`python scripts/review_engine.py --bias doc.json rct`
### 阶段3 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/quality-bias-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 文献类型不明 | 默认cohort+声明 |
| 领域无描述 | 证据不足档——不判不存在 |
| 锚点缺失 | 补定位 |

## 资源清单
scripts：review_engine.py, claim_evidence.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。