---
name: quality-review-forge
description: 论文质量审查：结构完整性（章节/层级/摘要正文对应/结论回应引言——关键缺位识别）、引用支持（论断-文献对应/数据三处一致/术语统一）、统计报告（对照/样本量/随机化/显著/误差/重复；方法缺陷vs报告缺陷区分）。
---

# quality-review-forge

## 核心原则（不可违反）
1. **完整性**：章节齐备/层级合理/摘要与正文对应/结论回应引言问题——识别"结构看着完整但关键部分缺位"（review_engine --structure）。
2. **用支持**：论断与所引文献主张对应；数据在摘要/正文/图表一致；术语定义前后统一；错配具体位置指出（claim_evidence --checkref + --claims）。
3. **计报告**：对照/样本量与抽样/指标/显著性/误差与置信区间/重复与随机化——区分"方法本身缺陷"与"报告缺陷"（review_engine --stats）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 结构审计（0请求）：`python scripts/review_engine.py --structure`
### 阶段2 引用支持（0请求）：`python scripts/claim_evidence.py --claims` + `--checkref`
### 阶段3 统计报告（0请求）：`python scripts/review_engine.py --stats`
### 阶段4 审查报告（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/quality-review-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 章节缺位 | missing_sections 清单 |
| 数据不一致 | 三处对照定位 |
| 缺陷分类 | 方法vs报告分开 |

## 资源清单
scripts：review_engine.py, claim_evidence.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。