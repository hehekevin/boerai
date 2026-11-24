# 图稿规格（spec）参考 · Figure specification reference

一份图只有一个事实来源：`spec.json`。渲染器不生成任何 spec 之外的文字、数值或关系；每个元素都可以绑定一条逐字来源引文（evidence），校验器据此判断"图上的每一句话是否来自材料"。

## 1. 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` | 是 | 与 `/input/case.json` 的 `case_id` 一致，写入 `result.json` |
| `figure_id` | 是 | 输出文件名主干，例如 `figure03` |
| `figure_kind` | 是 | `relationship_schematic` / `data_chart` / `mechanism_pathway` / `apparatus_route` / `graphical_abstract` |
| `title` | 否 | 单行标题；缺省则不留标题区 |
| `caption` | 是 | 图注。必须定义缩写、样本量 n、误差线含义、显著性标记与颜色编码 |
| `canvas` | 否 | `{preset, width_mm, height_mm, dpi, font_pt, line_pt, font_stack, fit_content}`；缺省按 figure_kind 取预设 |
| `sources` | 是 | 输入文件清单：`[{id, path, sha256, version, kind, note}]` |
| `evidence` | 是 | 引文表：`{E1: {source, locator, quote}}` |
| `uncertainty` | 否 | 明确写出的不确定项（材料缺失、描述矛盾、数值取舍） |
| `changes` | 否 | 修改记录 |

画布预设：`nature_single` 89×70、`nature_1_5` 120×90、`nature_double` 183×120、`science_double` 175×110、`elsevier_double` 190×130、`thesis_a4` 160×110、`grant_slide` 230×130、`ga_landscape` 160×80（单位 mm）。`canvas.width_mm`/`height_mm` 显式给出时以显式值为准；只给宽度时高度按内容自动收缩（`fit_content: false` 可关闭）。

## 2. 元素

### 2.1 `nodes`（实体）
```json
{"id":"egfr","label":"EGFR","sublabel":"Y1068","class":"receptor","shape":"membrane_receptor",
 "lane":"membrane","group":"g1","order":1,"panel":"A","emphasis":"key",
 "fill":"#E8F1F8","stroke":"#0072B2","source":"E2"}
```
* `class` 决定默认配色与图元：`gene protein receptor kinase complex ligand metabolite ion cell organelle nucleus tissue process step stage phenotype condition instrument component material sample data concept`。
* `shape` 可选：`roundrect rect ellipse diamond hexagon cylinder membrane_receptor cell organelle nucleus vesicle channel instrument document`；缺省由 `class` 推导。
* `lane` 指定区室带；`group` 指向 `containers` 的包含框；`order` 决定同列内的上下顺序。
* `x_mm`/`y_mm` 可显式定位；一般留空由布局计算。
* `source` 指向 `evidence` 的键。**没有来源的实体不应上图。**

### 2.2 `edges`（关系）
```json
{"id":"e5","from":"ras","to":"erk","type":"activate","label":"via RAF–MEK","source":"E4","route":"straight"}
```
关系类型与图形语法（箭头终点形状是语义，不是装饰）：

| `type` | 中文 | 终点 | 线型 |
|---|---|---|---|
| `activate` / `promote` / `upregulate` | 激活/促进/上调 | 实心箭头 | 实线 |
| `inhibit` / `repress` | 抑制/阻遏 | T 形横杠 | 实线 |
| `bind` | 结合 | 空心菱形 | 实线 |
| `complex` | 组成复合物 | 无箭头 | 实线 |
| `modify` / `phosphorylate` | 修饰/磷酸化 | 实心箭头 | 虚线 |
| `transport` / `secrete` / `flow` | 转运/分泌/流向 | 实心箭头 | 实线 |
| `translocate` / `signal` | 易位/信号 | 实心箭头 | 虚线 |
| `sequence` | 时序下一步 | 实心箭头 | 实线 |
| `contain` / `part_of` / `associate` / `connect` | 包含/属于/关联/连接 | 无箭头 | 实线（`part_of` 虚线） |
| `catalyze` / `convert` | 催化/转化 | 实心箭头 | 实线 |

`bidirectional: true` 时两端都画终点形状；`waypoints` 给出折点坐标可强制走线。

### 2.3 `containers`（包含/分组）
`{id, label, members:[node ids], relation: contains|part_of|associate, source}`。包含框只包住成员；非成员与框相交时布局会把非成员挪开，仍相交则由 `GEO-CONTAINER` 报出。

### 2.4 `lanes`（区室带）
`{id, label, order, fill, panel}`。机制图按 `extracellular → membrane → cytoplasm → nucleus` 自上而下排序；`fill:"none"` 可只留分隔线。

### 2.5 `charts`（数据图）
```json
{"id":"c1","panel":"B","type":"bar",
 "data":{"x":"condition","y":"pERK","err":"sd","n":"n","unit":"fold vs vehicle",
         "xlabel":"Condition","ylabel":"pERK/ERK (fold vs vehicle)",
         "rows":[{"condition":"Vehicle","pERK":1.00,"sd":0.08,"n":3}]},
 "source":"E8"}
```
* `type`：`bar` `line` `scatter` `box` `heatmap`。
* 三种数据形态任选其一：`rows`（每行一个观测或一个汇总值，`x`/`y`/`err`/`n` 为列名）、`series`+`categories`（每系列一组数值）、`matrix`+`row_labels`+`col_labels`（热图）。
* 同一 `(x, 分组)` 出现多行时按均值聚合，`err` 取各行误差的均值，`n` 取行数或 `n` 列。
* `unit` 必须与 `ylabel` 括号内单位一致；`significance: [{from,to,label}]` 画显著性括号；`ymin/ymax/log/value_labels/colorbar/cmap` 控制坐标与标注。
* 数值只能来自 `rows`/`matrix`，不得手写进标签；`value_labels: true` 时打印的数值由数据计算。

### 2.6 `legend`
`{title, position: bottom|right, items:[{key,label,swatch,color,dash,source}]}`；`swatch`：`color bar box line arrow tbar dash gradient shape`。图例项数必须与数据分类数一致（`LEG-MATCHES-DATA`）。

### 2.7 `annotations`
`{id, kind: note|callout|scalebar, text, target, x_mm, y_mm, size_pt, source}`。`callout` 会从文字引一条虚线到 `target`。

### 2.8 `panels`
`{id:"A", title:"…", x_mm, y_mm, w_mm, h_mm, layout:"row|column"}`。全部省略时按图型自动分栏（1–4 栏网格）；只给 `id/title` 时自动排布并加面板字母。

## 3. `evidence` 与溯源
```json
"evidence":{"E2":{"source":"S1","locator":"p.4, col.2, para 1","quote":"Ligand-bound EGFR recruits GRB2."}}
```
* `quote` 必须是来源材料中的**逐字**片段（可截断到一句），`locator` 给页码/图表号/表行号。
* 校验器会把 `quote` 与抽取到的材料文本比对（容忍空白与连字符断行），比对失败报 `EVID-QUOTE-PRESENT`。
* `result.json` 输出 `element_inventory`（每个元素→引文）与 `figure_provenance.csv`（可表格复核）。

## 4. 最小可用 spec
```json
{"case_id":"c1","figure_id":"figure03","figure_kind":"relationship_schematic",
 "caption":"…","nodes":[{"id":"a","label":"A","source":"E1"},{"id":"b","label":"B","source":"E2"}],
 "edges":[{"id":"e1","from":"a","to":"b","type":"activate","source":"E3"}],
 "evidence":{"E1":{"source":"S1","locator":"p.1","quote":"…"},"E2":{…},"E3":{…}},
 "sources":[{"id":"S1","path":"/input/paper.pdf","sha256":"…"}]}
```
其余字段全部有默认值，`build` 会补全并给出提示。
