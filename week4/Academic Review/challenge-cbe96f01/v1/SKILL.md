---
name: cite-fact-check-forge
description: 引用与事实核验：支持判定（完整/部分/不支持/无法判定四档+结论超出引文范围识别）、来源可靠性（来源等级/出版状态/版本差异/更正撤稿）、一致性（正文/表格/图注/摘要数字样本量显著性自洽）。
---

# cite-fact-check-forge

## 核心原则（不可违反）
1. **持判定**：四档支持判定；"结论超出引文范围"的过度推断识别——主题相关≠支持（verify_engine --support）。
2. **可靠性**：来源等级/出版状态/版本差异/更正与撤稿信息；预印本vs正式版不一致处理（increment_tracker 版本识别逻辑+claim_evidence --checkref）。
3. **一致性**：正文/表格/图注/摘要间数字/样本量/显著性自洽（review_engine --structure 摘要正文数值核对+--stats）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 支持判定（0请求）：`python scripts/verify_engine.py --decompose/--support`
### 阶段2 引用对账（0请求）：`python scripts/claim_evidence.py --checkref`
### 阶段3 一致性（0请求）：`python scripts/review_engine.py --structure`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/cite-fact-check-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 过度推断 | 超出范围判定 |
| 撤稿来源 | 不可作为支撑 |
| 预印本不一致 | 版本差异标注 |

## 资源清单
scripts：verify_engine.py, claim_evidence.py, review_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。