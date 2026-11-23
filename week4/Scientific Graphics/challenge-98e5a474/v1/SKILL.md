---
name: diagram-forge
description: 科研示意图生成与编辑。机制图/流程图/结构关系图：实体-关系清单先行（激活/抑制/上下游/包含/时序的图形语法，方向必有原文依据），来源没有的实体严禁上图，图例-数据映射逐项一致，SVG 分层可编辑源文件（text 可编辑、g 命名）+ PNG/PDF 导出清单，修改任务按图层编辑不动其他面板。触发词：科研示意图、机制图、流程图、通路图、entity-relation、diagram。
---

# diagram-forge — 科研示意图生成与编辑

**关系方向必有依据、实体不造新名、图例与数据逐项一致、SVG 分层可编辑——审稿人挑不出结构错误。**

## 核心原则（不可违反）

1. **实体可追溯**：图中每个实体、关系箭头、数值标签都能指到来源材料的具体位置（file:line）；来源里没有的实体/数值不得上图。
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

读 task.md：图类型（机制图/流程图/结构关系图）、目标版式、编辑任务（新建 or 修改已有图）。

### 阶段 1：实体-关系抽取（约 2–3 次模型请求）

从材料抽取实体清单与关系清单，产 `/app/work/element-source-map.md`：
- 实体：`{name, 类型(分子/细胞/器件/样本), 属性, 来源(file:line)}`；
- 关系：`{from, to, type(激活/抑制/上下游/包含/时序), 方向依据(原文引用), 来源}`——**抑制不得画成激活，上下游不得颠倒，包含不得画成并列**；
- 数据：图例/颜色映射所依据的数据表（若有）逐行登记。

### 阶段 2：SVG 绘制/编辑（约 3–5 次模型请求）

按关系类型用图形语法绘制 `/app/output/diagram.svg`：
- 每面板/分区一个 `<g data-role>`，文字 `<text>` 可编辑；
- 箭头语义：实线箭头=促进，平端=抑制，虚线=推测通路（材料依据标注在 map）；
- 图例与数据映射逐项一致（颜色数=分类数）；
- 修改任务：先 --diff 旧版（结构审计），按编辑指令改对应图层，不动其他面板。

### 阶段 3：审计与导出（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/svg_audit.py --check /app/output/diagram.svg
python <SKILL_DIR>/scripts/svg_audit.py --pair /app/output/diagram.svg /app/output/diagram.png /app/output/diagram.pdf
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/work/element-source-map.md --require "实体|element|关系|relation,来源|source,图例|legend|映射" --names "entities,sources,legend"
```

### 阶段 4：交付

`/app/output/result.json`（合并 output_contract + case_id）：element-source-map（实体/关系/数据三层溯源）、图例-数据映射表、导出清单、gaps/anomalies、status。

## 异常处置速查（详见 references/edge-cases.md）

| 情形 | 处置 |
|-|-|
| 来源未指明关系方向 | 不画箭头；gaps + 追问（画对方向比画好看重要） |
| 图例色数与数据分类数不一致 | 以数据分类数为准修正配色 |
| 编辑指令指向不存在图层 | 不虚构；uncertainties 记录 |
| 渲染器不可用 | SVG 源 + 导出清单，anomalies 声明 |
| 预算不足 | element-source-map + SVG 先落盘，status=partial |

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
