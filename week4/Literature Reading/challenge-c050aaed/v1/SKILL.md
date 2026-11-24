---
name: annot-forge
description: 阅读批注与知识沉淀。批注提取（载体/页码/坐标/颜色/标签/类型区分）、笔记结构化（五类+锚点一一对应）、知识关联（带依据控过度连接）、可检索入口。触发词见核心原则。
---

# annot-forge — 阅读批注与知识沉淀

## 核心原则（不可违反）

1. **批注提取**：PDF/扫描件/网页/Word 等载体的高亮/划线/页边批注/手写标记——保留页码、坐标、颜色、标签、所属文件；**批注类型区分不混为一类**。
2. **笔记结构化**：原文片段→问题/方法/结论/可复用要点/待验证疑点五类结构化笔记；批注到笔记条目一一对应（note_id=annotation_id）。
3. **知识关联**：批注-笔记-文献-作者-方法-项目间关联带依据；**控制过度连接**——无锚点依据不入图；同一文献重复下载/版本差异合并锚点防分裂。
4. **可检索入口**：按主题/标签/实体/来源/时间五维索引；召回不足与误召回的处理方式显式说明。
5. **脚本先行**：extract/notes/link/retrieval 恒为0模型请求。

## 运行环境约定

- 输入 `/input/case.json` 与 `/input/task.md`；材料以实际路径为准。工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段0 盘点（1请求）：`python scripts/inspect_case.py /input/case.json`
### 阶段1 批注提取（0请求）：`python scripts/annotation_engine.py --extract ann.json`
### 阶段2 笔记结构化（0请求+1-2请求归类复核）：`python scripts/annotation_engine.py --notes ann.json`
### 阶段3 知识关联（0请求）：`python scripts/annotation_engine.py --link notes.json`
### 阶段4 检索入口（0请求）：`python scripts/annotation_engine.py --retrieval notes.json`
### 阶段5 成文（1请求）

### 交付阶段（0请求）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/annot-forge.md --require "原则关键词,流程关键词,异常关键词" --names "p1,p2,p3"
```

主产物 `/app/output/annot-forge.md`：每条结论带锚点。

## 异常处置速查（详见 references/rules.md）

| 情形 | 处置 |
|-|-|
| 批注载体混杂 | carrier字段+类型判定；扫描件手写标注OCR限制 |
| 无页码/坐标 | 保留可获取字段，缺失显式标记 |
| 过度关联 | 无依据不入图 |
| 预印本vs正式版 | 合并锚点防知识分裂 |

## 资源清单

- `scripts/`：annotation_engine.py；inspect_case.py、validate_result.py
- `references/rules.md`、`templates/result.schema.json`、`examples/minimal-example.md`、`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。确定性子命令恒为 0 请求；模型仅语义裁决与成文。过 60% 时间冻结：JSON 先落盘，status=partial。