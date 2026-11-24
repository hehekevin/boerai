---
name: review-synthesis-forge
description: 文献综述生成：纳排筛选记录保留、主题归纳（方法/对象/结论分歧提炼主题+边界，防重叠遗漏）、证据表（文献标识/摘录/页码/论断/强度可反查）。
---

# review-synthesis-forge

## 核心原则（不可违反）
1. **献筛选**：研究问题定义纳排标准；重复/低相关/仅摘要文献处理；筛选记录保留（screening_engine --screen）。
2. **题归纳**：从方法/对象/结论分歧提炼主题与子主题；每主题给文献支撑与边界——主题间不重叠不遗漏。
3. **与回链**：证据表（文献标识/原文摘录/页码或段落/支撑论断/证据强度）——草稿可反向查到证据行（verify_engine + claim_evidence）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 筛选（0请求）：`python scripts/screening_engine.py --screen records.json criteria.json`
### 阶段2 证据表（0请求）：`python scripts/claim_evidence.py --claims draft.md`
### 阶段3 主题归纳（0请求+2-3请求归纳）：主题矩阵（主题×文献）
### 阶段4 成文（2-3请求）：综述草稿+证据表

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/review-synthesis-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 仅摘要无全文 | 标记 evidence_level=abstract-only |
| 主题重叠 | 归并+边界声明 |
| 分歧证据 | conflict 标记+双方出处 |

## 资源清单
scripts：screening_engine.py, claim_evidence.py, verify_engine.py, search_audit.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。