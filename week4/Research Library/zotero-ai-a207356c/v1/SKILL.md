---
name: zotero-plugin-forge
description: Zotero AI 插件：多来源导入（PDF/网页快照/题录文件；附件与条目绑定/重复条目/集合归属）、字段补全（首页/DOI解析/已有题录；优先级+覆盖规则+来源标注）。
---

# zotero-plugin-forge

## 核心原则（不可违反）
1. **献导入**：PDF/网页快照/题录文件多来源入库；附件与条目脱节修复；重复条目去重（classify --versions 键策略）；集合归属校验。
2. **据补全**：原文首页/DOI解析/已有题录补齐字段；字段优先级显式（DOI解析>首页>已有）、覆盖规则（不覆盖人工已确认值）、来源标注（multidb_engine 字段映射+provenance）。
3. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 导入去重（0请求）：`python scripts/classify_engine.py --versions records.json`
### 阶段2 字段补全（0请求）：`python scripts/multidb_engine.py --merge normalized.json`
### 阶段3 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/zotero-plugin-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 附件脱节 | 附件-条目绑定清单 |
| 字段冲突 | 优先级+来源标注 |
| 重复条目 | 合并保留依据 |

## 资源清单
scripts：classify_engine.py, multidb_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。