---
name: academic-review-general-forge
description: 学术审查总课题：按case路由（逻辑/质量/方法统计/回复修改/质量评价/引用核验/规范合规），组合引擎。
---

# academic-review-general-forge

## 核心原则（不可违反）
1. **路由**：逻辑→logic-review；质量→quality-review；方法统计→stats-methods-review；回复修改→review-reply（复用2815a418资产）；质量评价→bias；引用核验→verify_engine；合规→compliance。理由记录。
2. **子场景独立复跑**。3. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 路由（1请求）
### 阶段1-N 执行（0请求/子命令）
### 阶段末 成文

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/academic-review-general-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 混合审查 | 多引擎串联分别报告 |
| 不适用 | anomalies |

## 资源清单
scripts：review_engine.py, verify_engine.py, claim_evidence.py, review_ledger.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。