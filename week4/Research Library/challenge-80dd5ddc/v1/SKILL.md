---
name: kb-qa-forge
description: 科研知识库问答：跨目录跨格式检索（重复副本/历史版本处理+召回策略）、论断与原文片段一一对应（引用粒度与置信可检查）、据回链坐标（文件/版本/页码/段落）、分级提示（证据不足/冲突/不可读/权限受限说明缺什么）。
---

# kb-qa-forge

## 核心原则（不可违反）
1. **件检索**：跨目录/跨格式/含重复副本与历史版本——明确检索范围与召回策略；重复副本与旧版本不作为独立证据（file_search --versions）。
2. **的问答**：关键论断与原文片段一一对应；引用格式/粒度/置信说明可检查（qa_engine --retrieve + scaffold）。
3. **据回链**：可定位坐标（文件/版本/页码/段落）——他人能按记录回到原文核对（file_search --locate）。
4. **性提示**：证据不足/证据冲突/文件不可读/权限受限分级提示，说明缺什么——不静默。
5. **脚本先行**：检索/定位/版本识别恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 检索（0请求）：`python scripts/file_search.py --find <目录> "<词>"` + `--versions <目录>`
### 阶段2 定位与回链（0请求）：`python scripts/file_search.py --locate <文件> "<词>"`
### 阶段3 问答脚手架（0请求+2-4请求成文）：复用 qa_engine --retrieve/--scaffold
### 阶段4 分级提示（0请求）：证据不足/冲突/不可读/权限四类分级
### 阶段5 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/kb-qa-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 文件不可读 | 分级提示+说明缺什么 |
| 权限受限 | 提示而非报错 |
| 检索零命中 | 召回策略说明+建议 |
| 重复副本 | 版本识别不冒证据 |

## 资源清单
scripts：file_search.py, qa_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。