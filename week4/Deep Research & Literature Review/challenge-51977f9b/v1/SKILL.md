---
name: systematic-review-forge
description: 系统性文献综述：检索式（数据库/字段/布尔/受控词/时限意图说明）、条款化纳排标准（优先级）、两轮筛选逐条记录（题录级+全文级，判定人记录，可追溯重算）。
---

# systematic-review-forge

## 核心原则（不可违反）
1. **检索式**：研究问题→可执行检索式；数据库/字段/布尔逻辑/同义词与受控词/时间语言限制；每段检索式意图说明（search_audit --plan）。
2. **排标准**：条款化可判定纳排标准；研究类型/人群/时间/语言/全文可得；条款优先级与冲突处理（screening_engine --protocol）。
3. **选记录**：题录级+全文级两轮逐条结论/排除理由/判定人；纳入集可追溯可重算（screening_engine --screen --audit 计数闭合）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 检索式（0请求）：`python scripts/search_audit.py --plan`
### 阶段2 协议与标准（0请求）：`python scripts/screening_engine.py --protocol`
### 阶段3 两轮筛选+审计（0请求）：`--screen` + `--audit`
### 阶段4 成文（2-3请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/systematic-review-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 条款冲突 | 优先级声明+仲裁 |
| 计数不闭合 | 修复再交付 |
| 仅题录 | 全文级标 pending |

## 资源清单
scripts：search_audit.py, screening_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。