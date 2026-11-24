---
name: apparatus-technical-route
description: "Draw a source-bound experimental apparatus, process-train or technical-route figure: components, ports, connections, material flow and ordered steps, each traceable to the supplied protocol or paper, delivered as layered editable SVG, vector PDF, 600 dpi PNG/TIFF and result.json. Use when a case asks for an instrument or rig schematic, a flow diagram of feeds and products, a method workflow or a staged technical route with numbered steps. NOT for data charts, biological pathway mechanism figures, or for inventing connections the protocol does not state."
---

# 实验装置与技术路线图：生成图稿，也保留可编辑来源

装置图的每个部件、每条管路、每个箭头都对应真实实验条件：错一个连接方向、漏一个关键单元，读者对整套方案的理解就会偏。本技能把"装置清单 + 工艺描述"拆成**部件—接口—流向—步骤**的结构化表示，再据此布图，并交付可被别人打开、修改、复跑出同一张图的产物。

## 何时使用
* 用例要求画实验装置、反应器/管路的流程、仪器联用（如 GC–MS 进样回路）、技术路线、方法流程、分阶段实验步骤。
* 材料是实验方案、方法部分、操作规程、设备清单、工艺参数表。
* 关注点：部件名称与数量、接口对应、物料流向、步骤编号与顺序、工况参数与单位。

**不适用**：数据图表（`source-value-chart`）、通路机制（`biological-mechanism-pathway`）、概念框图（`editable-relationship-schematic`）、图形摘要（`graphical-abstract`）。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`。第 1 步读取真实结构。

## 输出（`/app/output`）
`result.json`、`figure.svg`、`figure.pdf`、`figure.png`(600 dpi)、`figure.tif`、`figure_spec.json`、`figure_checks.json`、`figure_provenance.csv`、`figure_report.md`、`run.log`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
grep -n -i -E "reactor|pump|valve|column|detector|trap|flow|temperature|pressure|step|stage|装置|反应器|流量|温度|步骤" "$WORK/material_text"/*.txt | head -40
python "$SKILL/run.py" build   --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure
python "$SKILL/run.py" verify  --spec "$WORK/spec.json" --work "$WORK"
```

**第 1 步 列部件清单。** 从材料抄出每个部件：名称（用原文措辞）、数量、关键工况（温度/压力/流量/转速 + 单位）、接口（进口/出口/取样口）。写 `$WORK/components.json`。材料没写的部件不要补。

**第 2 步 定连接与流向。** 每条连接写 `(from, to, 介质, 原文)`：气路/液路/电路/信号/机械耦合分别用不同线型或标签。流向以材料描述为准（"A 进入 B"→ A→B；"B 由 A 供料"同样 A→B）。取样、回流、旁路要显式画出，不要省略。

**第 3 步 定步骤顺序。** 技术路线按材料的时间顺序编号 1…n；每步写名称 + 时长/条件 + 原文。步骤编号写在节点 `sublabel`（如 `"1 · 30 min"`）或 `order`+`annotations` 中，二者只取一种，避免编号与正文错位。

**第 4 步 写 spec 并出图。**
```json
{"case_id":"<case_id>","figure_id":"figure","figure_kind":"apparatus_route",
 "caption":"(A) 反应装置：气路与液路经混合器进入 350 °C 管式反应器，产物经 −20 °C 冷阱后由六通阀取样进 GC–MS。(B) 单次运行的四阶段及时长（h）。",
 "lanes":[{"id":"gas","label":"Gas feed","order":0,"fill":"#F4F8FB"},
          {"id":"liquid","label":"Liquid feed","order":1,"fill":"#F7FAFC"},
          {"id":"train","label":"Reaction and analysis","order":2,"fill":"#FAFAFA"}],
 "nodes":[{"id":"mfc","label":"Mass-flow controllers","sublabel":"2 × 100 mL min⁻¹","class":"instrument","lane":"gas","source":"E1"},
          {"id":"reactor","label":"Tubular reactor","sublabel":"350 °C","class":"instrument","lane":"train","source":"E3","emphasis":"key"},
          {"id":"gc","label":"GC–MS","class":"instrument","lane":"train","source":"E5"}],
 "edges":[{"id":"a1","from":"mfc","to":"mix","type":"flow","label":"gas","source":"E1"},
          {"id":"a3","from":"mix","to":"reactor","type":"flow","source":"E2"}],
 "legend":{"items":[{"key":"gas","label":"gas line","swatch":"line","color":"#56B4E9"},
                    {"key":"liquid","label":"liquid line","swatch":"line","color":"#0072B2"},
                    {"key":"flow","label":"material flow","swatch":"arrow"}]},
 "evidence":{"E1":{"source":"S1","locator":"p.4","quote":"Gas flow is set by mass-flow controllers."}},
 "sources":[{"id":"S1","path":"/input/protocol.pdf","sha256":"<probe>"}]}
```

**第 5 步 复核三条。** ①部件名称与原文逐字一致（不改写、不合并）；②每条连接在材料中有依据，方向与"进口→出口"一致；③步骤编号与正文顺序一致，时长与单位一致。`GEO-NODE-OVERLAP`、`NUM-TRACEABLE`、`CMP-RELATIONS` 会自动检查，剩下的靠这三条人工判断。

## 图形语法（装置/路线图专用）
1. **流向唯一**：单一主流程按左→右（宽画布）或上→下（窄高画布）排列；支路（气/液/取样）用 `lanes` 或不同线色区分，不要交叉成一团。
2. **部件形状**：仪器/单元用 `instrument`（带内框的圆角矩形），容器/物料用 `cylinder`，步骤用 `roundrect`，判断/分支用 `diamond`。
3. **接口与管路**：`flow` 实心箭头表示物料流向；`connect` 无箭头表示机械/电气连接；信号线用 `signal`（虚线）。线型必须与图例一致。
4. **工况写在部件上**：`sublabel` 放温度/压力/流量与单位，格式统一（`350 °C`、`10 bar`、`1.0 mL min⁻¹`）。
5. **步骤编号**：`1 · Flush (0.5 h)` 这种形式，编号、名称、时长三段齐全；只画编号不画名称、或只画名称不编号都不合格。
6. **分组**：同一单元（进样段/反应段/分析段）用 `containers` 包起来，标签置于框内左上。
7. **比例不撒谎**：不要用方框大小暗示体积/流量差异，除非材料给出数值并写明编码（此时必须有图例）。

## 编辑既有图稿时的处理（source-preserving edit）
用例常要求"在给定图稿上修改"（改标签、加一条通路、换配色）。本技能一律采用**按来源重绘**而非像素级修改位图：

1. 把原图当作**元素清单的来源之一**：逐项抄出实体名、关系方向、分组、单位与图注，写入 `$WORK/entities.json`，并在 `changes` 记录"原图第 X 项 → 新图第 Y 项"。
2. 文字与数值以正文/数据表为准校正；原图与正文冲突时取正文，冲突写进 `uncertainty`。
3. 只改被要求改的部分，其余元素保持标签、顺序与配色不变，并在 `changes` 逐条列出改动。
4. 若原图为位图且无文字层：不把图像噪声当文字；只复现能确认的实体，缺项写入 `uncertainty`，并在交付说明中指出"原图为位图，已按正文重建"。
5. 交付的分层 SVG 可直接在 Illustrator/Inkscape 中按层编辑，`figure_spec.json` 支持再次 `build` 复现，二者共同构成"可编辑来源"。

## 证据与溯源
* 每个部件、每条连接、每个工况数值都要 `source`；工况数值写成 `sublabel` 时，`NUM-TRACEABLE` 会核对材料中是否存在该数字。
* 材料缺参数（如未给流量）：留空或写 `n.r.`，不要填"典型值"。
* 取样/回流等次要管路同样要引文；若材料只暗示，用 `uncertainty` 写明"按方法部分描述补画取样回路"。

## 异常处理
| 情况 | 处置 |
|---|---|
| 部件参数缺失 | 只画部件名，`sublabel` 留空；`uncertainty` 记录缺失项 |
| 工艺描述有歧义（"经 A 后进入 B"未说是否经 C） | 采用最小解释（A→B），把歧义写入 `uncertainty` |
| 接口信息冲突（两处流量不一致） | 取方法部分的数值，另一处写进 `uncertainty`；不要取平均 |
| 画布溢出/部件过多 | 拆面板（进样/反应/分析）或改 `science_double`；不要压到 5 pt 以下 |
| 步骤与图注编号错位 | 用 `order` 重排并在图注写明"编号同正文步骤" |

## 最小示例（示例，不是正式案例结果）
`python "$SKILL/run.py" demo --out /tmp/ff_demo` 演示同类引擎产物；本赛道的装置图示例见 `examples/`（示例数据，非正式结果）。

## 参考
`docs/SPEC.md`、`docs/CHECKS.md`、`docs/METHOD.md`、`docs/USAGE.md`。


## 本题评分对齐（challenge-9034312d · 实验装置与技术路线图）

题面评分点与本 Skill 的对应能力：

| 评分点（题面考察内容摘要） | 本 Skill 的对应机制 |
|---|---|
| 把输入材料变成可直接使用的装置图/流程图/技术路线图 | instrument/cylinder/document 图元 + flow/connect/signal 线型语义 + lanes 分路 |
| 部件名称与数量、接口对应、上下游顺序、箭头方向、标注数值与来源一致 | 部件逐字抄录规则；工况写 sublabel 并过 NUM-TRACEABLE；SEM-DIRECTION 方向复核 |
| 覆盖六类要素：实体、空间布局、连接、流向、步骤编号、参数 | sublabel 编号·时长格式；containers 单元分组；图例解释线型 |
| 参数缺失、描述歧义、接口冲突的识别与处置 | 缺参留空+uncertainty；最小解释原则；冲突取方法部分并记录 |

* 组织方输入修订（workorder `apparatus_and_technical_route`）：固定案例按该工单类型给料；本 Skill 按 `figure_kind` 路由到对应图类语法。
* 公开作品：<https://github.com/hehekevin/boerai/tree/main/week4/Scientific%20Graphics/challenge-9034312d/v2>
