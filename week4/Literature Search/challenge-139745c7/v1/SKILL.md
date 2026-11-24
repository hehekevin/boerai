---
name: file-retrieval-forge
description: 科研文件智能检索。文件名+内容双路检索并排序（filename*3+content），命中定位到行号+章节标题（证据回链可逐字验证），过滤条件作为硬约束执行（无法满足如实报告不放宽），重复文件与版本差异识别（内容哈希+文件名标记）。触发词：文件检索、证据回链、章节定位、版本去重。
---

# file-retrieval-forge — 科研文件智能检索

一句话：**双路检索有排序、命中定位到章节、过滤是硬约束、版本不冒证据。**

## 核心原则（不可违反）

1. **跨文件双路检索**：文件名命中×3 + 内容命中计数排序；同义表述/缩写/上下位词由模型在机器结果之上做概念级复核——避免只命中文件名相同的那一份。
2. **证据回链**：每条结论的定位包含文件路径、行号、章节标题、段落首句与原文片段——可点击、可逐字验证。
3. **过滤是硬约束**：年份/项目编号/文件类型/实验批次/版本/权限等条件严格执行；条件无法满足时如实报告（unsatisfiable_filters），不放宽。
4. **版本不冒证据**：内容哈希相同+文件名版本标记（v2/final/old/copy/旧版）→ 识别为副本/旧版本，不作为独立证据；保留最新版本。
5. **脚本先行**：检索/定位/过滤/版本识别恒为0模型请求；模型只做语义复核与概念级扩展。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：双路检索（0请求）
```bash
python <SKILL_DIR>/scripts/file_search.py --find <目录> "<词1,词2,...>" > /app/work/find.json
```

### 阶段 2：命中定位与证据回链（0请求）
```bash
python <SKILL_DIR>/scripts/file_search.py --locate <文件> "<关键词>" > /app/work/locate.json
```
输出：行号、章节标题、章节行号、原文片段。

### 阶段 3：硬过滤（0请求）
```bash
python <SKILL_DIR>/scripts/file_search.py --filter <目录> <filters.json> > /app/work/filtered.json
```

### 阶段 4：版本识别（0请求）
```bash
python <SKILL_DIR>/scripts/file_search.py --versions <目录> > /app/work/versions.json
```

### 阶段 5：语义复核与成文（约2-4次模型请求）
概念级扩展检索（同义表述/缩写/跨语言）→ 结果综合 → 检索报告。

### 阶段 6：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：find/locate/filter/versions 全量JSON、语义复核结论、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/filesearch-report.md --require "检索|find|搜索,定位|locate|回链|章节,过滤|filter|约束,版本|version|去重" --names "find,locate,filter,versions"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 目录不存在 | gaps 声明，不虚构结果 |
| 二进制文件 | 跳过内容检索并记录（不是文本可读） |
| 过滤条件全部无匹配 | 如实报告0结果+原因，不放宽 |
| 命中过多（>100文件） | 按score截断Top30+报告总数 |

## 资源清单
- `scripts/file_search.py` — find/locate/filter/versions（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/filesearch-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。四子命令恒为0请求。过60%时间冻结。