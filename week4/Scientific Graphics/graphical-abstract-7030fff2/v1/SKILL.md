---
name: ga-forge
description: Graphical Abstract（图形摘要）。单页视觉摘要生成：研究问题→方法→结果→结论四区确定性版式，实体-来源映射（每个上图元素带 file:line），视觉通道与数据一一对应（颜色/长度/面积+图例+色觉冗余），SVG 可编辑源文件（text 不轮廓化、g 分层命名）+ PNG/PDF 导出合规清单，同输入同版式可复现。触发词：图形摘要、Graphical Abstract、单页摘要、visual abstract。
---

# ga-forge — Graphical Abstract 图形摘要

**要素上图必有出处、四区版式可复现、SVG 分层可编辑、导出有清单——图能进投稿流程而不只是好看。**

## 核心原则（不可违反）

1. **实体可追溯**：图中每个实体、关系箭头、数值标签都能指到来源材料的具体位置（file:line）并标注版本（v1/v2…与导出检查结果）；来源里没有的实体/数值不得上图。
2. **可编辑源文件**：交付分层命名（每面板一个 `<g data-role>`）、文字用 `<text>` 不轮廓化、数据与样式分离的 SVG 源文件——不是一张改不动的位图。
3. **同输入同版式**：确定性布局规则（分区坐标、面板顺序），两次运行结构一致。
4. **导出合规**：源文件 + 导出件（PNG/PDF）同时交付，导出参数（尺寸/字号/白底）写进检查清单；脚本审计源文件与导出清单。

## 运行环境约定

- 输入：`/input/case.json` 与 `/input/task.md`；材料以实际路径为准。
- 工作目录 `/app/work`，输出 `/app/output`。资源以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段 0：盘点（约 1 次模型请求）

```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

读 task.md：单页摘要的主题范围（研究问题/方法/结果/结论哪些必须上图）、目标尺寸与格式。

### 阶段 1：要素抽取——面板-要点映射（约 2–3 次模型请求）

从材料抽取：研究对象（实体）、方法路线（步骤链）、核心结果（数值/趋势）、结论（一句话）。产 `/app/work/element-source-map.md`：
`{面板, 要素, 类型(实体/关系/数值/标签), 来源(file:line), 图面表达(形状/颜色/箭头)}`。
- 来源里没有的实体/数值**不上图**；
- 只进图注不进图面的信息明确列出（detail-to-caption 清单）。

### 阶段 2：版式与绘制（约 3–5 次模型请求）

确定性版式（同一输入同一布局）：单页 A 区（问题）/ B 区（方法链）/ C 区（结果）/ D 区（结论），通栏标题。产 `/app/output/graphical-abstract.svg`：
- 每面板一个 `<g data-role="panel-A">`；
- 文字全部 `<text>` 元素（不轮廓化）；
- 数据编码：颜色/长度与结果数值一一对应（结果 → 视觉通道映射写进 element-source-map）；
- 图例必备（≥4 色时），字号 ≥9px，白底。

### 阶段 3：审计与导出（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/svg_audit.py --check /app/output/graphical-abstract.svg
python <SKILL_DIR>/scripts/svg_audit.py --pair /app/output/graphical-abstract.svg /app/output/graphical-abstract.png /app/output/graphical-abstract.pdf
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/work/element-source-map.md --require "实体|element|面板|panel,来源|source|file:line,编码|颜色|legend|图例" --names "elements,sources,encoding"
```

audit 检查：XML 合法、text 可编辑、分层命名、viewBox、色板、图例、字号、**画布溢出**（元素越界=导出裁切风险）、**字体族声明**（未声明=字体替换风险）。渲染 PNG/PDF（环境有渲染器则用，如 rsvg/inkscape/cairosvg；无则交付 SVG 源 + 导出清单并在 anomalies 声明）。

### 阶段 4：交付

`/app/output/result.json`（合并 output_contract + case_id）：element-source-map（要素级溯源）、导出检查结果、gaps/anomalies、status。

## 异常处置速查（详见 references/edge-cases.md）

| 情形 | 处置 |
|-|-|
| 材料缺结论/结果段 | 对应面板留占位 + gaps（"材料未提供 X"），不编内容 |
| 实体关系与文字描述冲突 | 以文字描述为准；conflicts 记录 |
| 渲染器不可用 | 交付 SVG 源文件 + 导出清单；anomalies 声明未渲染 |
| 色觉可及性 | 主色对加形状区分（形状编码冗余），灰度打印检查 |
| 预算不足 | element-source-map + SVG 草稿先落盘，status=partial |

## 资源清单

- `scripts/svg_audit.py` — SVG 源审计（XML/可编辑性/分层/画布/色板/图例/字号）与导出清单校验
- `scripts/inspect_case.py`、`scripts/validate_result.py` — 盘点与交付契约校验
- `references/diagram-rules.md` — 实体关系抽取与版式规则
- `references/edge-cases.md` — 异常与降级处置
- `templates/element-source-map.md`、`templates/result.schema.json`
- `examples/minimal-example.md`（示例数据，非正式案例结果）
- `README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。SVG 审计与导出检查 0 模型请求；模型只做实体抽取与版式生成。过 60% 时间立即冻结：element-source-map + SVG 草稿先落盘，status=partial。
