---
name: logic-review-forge
description: 论文逻辑与论证审查：主张抽取（作者主张/引用观点/假设情形区分+限定条件）、支撑核查（证据存在/来源/强度匹配；结论超出数据/引用不对应）、推理完整性（跳跃/隐含假设/替代解释/相关因果混用）。
---

# logic-review-forge

## 核心原则（不可违反）
1. **张抽取**：摘要/引言/结果/讨论抽取核心主张及限定条件；区分作者主张/引用他人/假设情形——逐条可核查（review_engine --claims）。
2. **撑核查**：每条主张证据是否存在/来自本文实验还是所引文献/是否足以支撑该强度表述；识别"结论超出数据"与"引用不对应"（review_engine --support）。
3. **完整性**：前提到结论推理跳跃/隐含假设未说明/替代解释未排除/相关性与因果性混用（review_engine --methods 逻辑项+模型裁决）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 主张抽取（0请求）：`python scripts/review_engine.py --claims doc.json`
### 阶段2 支撑核查（0请求）：`python scripts/review_engine.py --support doc.json`
### 阶段3 推理完整性（0请求+2-3请求语义裁决）
### 阶段4 审查报告（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/logic-review-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 主张无证据标记 | 结论超出数据判定 |
| 引用不对应 | cite_mismatch_risk 标记 |
| 隐含假设 | 列出待作者确认 |

## 资源清单
scripts：review_engine.py, claim_evidence.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。