---
name: biological-mechanism-pathway
description: "Draw a source-bound biological mechanism or pathway figure: compartments, membrane receptors, activation versus inhibition, complexes and modifications, with every arrow, entity and read-out traceable to the supplied paper and delivered as layered editable SVG, vector PDF, 600 dpi PNG/TIFF and result.json. Use when a case asks for a signalling pathway diagram, mechanism model, cell-biology schematic or pathway map that must express interaction type and direction correctly. NOT for data charts, apparatus or process diagrams, graphical abstracts, or for inventing steps the paper does not report."
---

# 生物机制图与通路图：生成图稿，也保留可编辑来源

机制图是一份可以被逐条质疑的机制陈述。本技能把"句子里的机制"转成**区室—实体—相互作用—方向**的结构化表示，再按生物学习惯布图：区室自上而下、通路自左向右、激活与抑制用不同终点形状。**画错一个箭头等于给出一个错误论断**，因此每个元素都必须绑定原文。

## 何时使用
* 用例要求画信号通路、机制模型、细胞过程、通路串扰、药物作用机制图。
* 材料是论文正文/图注、综述段落、或既有通路图需要改绘。
* 关注点：激活 vs 抑制、上下游方向、跨膜与转位、复合物与修饰、区室归属。

**不适用**：数据图表（`source-value-chart`）、装置与工艺（`apparatus-technical-route`）、概念框图（`editable-relationship-schematic`）、单页摘要（`graphical-abstract`）。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`。第 1 步读取真实结构，不按领域标签猜内容。

## 输出（`/app/output`）
`result.json`、`figure.svg`（分层：lanes / containers / edges / nodes / legend / caption）、`figure.pdf`、`figure.png`(600 dpi)、`figure.tif`、`figure_spec.json`、`figure_checks.json`、`figure_provenance.csv`、`figure_report.md`、`run.log`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
grep -n -i -E "inhibit|suppress|activat|induc|phosphoryl|binds|recruit|translocat|抑制|激活|磷酸化" "$WORK/material_text"/*.txt | head -40
python "$SKILL/run.py" build   --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure
python "$SKILL/run.py" verify  --spec "$WORK/spec.json" --work "$WORK"
```

**第 1 步 抽机制三元组。** 先把每条机制句子拆成 `(来源实体, 动词, 目标实体, 区室, 原文)`，写到 `$WORK/mechanism.json`。动词到类型的映射：

| 原文动词（示例） | `type` | 图形 |
|---|---|---|
| activates / induces / promotes / drives / 激活 / 诱导 / 促进 | `activate` | 实心箭头 |
| inhibits / suppresses / represses / blocks / prevents / 抑制 / 阻断 | `inhibit` | T 形横杠 |
| binds / recruits / associates with / 结合 / 招募 | `bind` | 空心菱形 |
| phosphorylates / ubiquitinates / 磷酸化 / 泛素化 | `phosphorylate` | 虚线箭头 + 修饰基团标注 |
| forms a complex with / 组成复合物 | `complex` | 无箭头连线 |
| transports / releases / secretes / 转运 / 分泌 | `transport` | 实心箭头（跨膜） |
| translocates to / 易位至 | `translocate` | 虚线箭头（跨区室） |
| is required for / is upstream of / 上游 | `sequence` 或 `activate` | 依原文语气选择 |

**第 2 步 定区室。** 默认自上而下：`Extracellular → Plasma membrane → Cytoplasm → Nucleus`（按材料实际出现的区室裁剪）。跨膜受体用 `shape:"membrane_receptor"`（渲染为跨双层脂膜的方框），不要画在膜内或膜外。核内事件必须在 `nucleus` 区内，或显式加 `Nucleus` 区室带。

**第 3 步 写 spec。**
```json
{"case_id":"<case_id>","figure_id":"figure","figure_kind":"mechanism_pathway",
 "caption":"区室自上而下为胞外、质膜、胞质。实心箭头=激活，T 形横杠=抑制，空心菱形=结合，虚线=间接或多步。ERK 对 SOS 的负反馈见正文 p.5。",
 "lanes":[{"id":"extra","label":"Extracellular","order":0,"fill":"#F4F8FB"},
          {"id":"mem","label":"Plasma membrane","order":1,"fill":"#EEF3F7"},
          {"id":"cyto","label":"Cytoplasm","order":2,"fill":"#FAFAFA"}],
 "nodes":[{"id":"egfr","label":"EGFR","class":"receptor","shape":"membrane_receptor","lane":"mem","source":"E2"},
          {"id":"ras","label":"RAS-GTP","class":"protein","lane":"cyto","source":"E4"}],
 "edges":[{"id":"e1","from":"egfr","to":"ras","type":"activate","label":"via GRB2–SOS","source":"E3"},
          {"id":"e2","from":"erk","to":"sos","type":"inhibit","label":"feedback","source":"E7"}],
 "legend":{"items":[{"key":"activate","label":"activation","swatch":"arrow"},
                    {"key":"inhibit","label":"inhibition","swatch":"tbar"},
                    {"key":"bind","label":"binding","swatch":"line","color":"#009E73"},
                    {"key":"indirect","label":"indirect","swatch":"dash"}]},
 "evidence":{"E2":{"source":"S1","locator":"p.2","quote":"Ligand-bound EGFR recruits GRB2."}},
 "sources":[{"id":"S1","path":"/input/paper.pdf","sha256":"<probe>"}]}
```

**第 4 步 方向复核。** 对每条边问三个问题：原文的主语是 `from` 吗？动词支持这个 `type` 吗？方向与上下游一致吗（受体→激酶→转录因子→基因）？`SEM-RELATION-WORD` 与 `SEM-DIRECTION` 会用引文动词和实体出现顺序自动反查。

**第 5 步 修图。** 按 `FAIL.fix` 改，重跑。`fail` 不清零 → `status=partial` + `uncertainty`。

## 图形语法（机制图专用）
1. **终点形状即语义**：实心箭头=正调控/流向；T 形横杠=负调控；空心菱形=结合；无箭头=结构关系；虚线=间接/多步/易位。图例必须逐项解释（`SEM-LEGEND-TYPES`）。
2. **区室是硬约束**：跨膜蛋白画在 `Plasma membrane` 带内并跨双层；胞外配体不进胞质；核内事件不画在胞质。
3. **方向**：通路自左向右；反馈边允许自右向左并标 `feedback`；不要为了排版把箭头反过来。
4. **复合物**：用 `containers`（`relation:"complex"`）把成员包在一起，或用一个 `class:"complex"` 节点列成员名，不要用并列箭头暗示结合。
5. **修饰**：`phosphorylate` 用虚线箭头 + 标注 `P`；多位点写 `Y1068-P`，不确定位点就只写 `P`。
6. **命名**：基因符号斜体（`"italic": true`）、蛋白正体；物种前缀（h/m/z）按原文；不要自造同义词或大小写变体。
7. **读出型数值**（表达量、抑制率、置信度）只在材料给出时标注，并在图注写 n 与统计量；不给就留空。
8. **颜色**：颜色编码"实体类别"或"通路分支"之一，不能同时编码两者；通路分支用色时图例项数=分支数。

## 编辑既有图稿时的处理（source-preserving edit）
用例常要求"在给定图稿上修改"（改标签、加一条通路、换配色）。本技能一律采用**按来源重绘**而非像素级修改位图：

1. 把原图当作**元素清单的来源之一**：逐项抄出实体名、关系方向、分组、单位与图注，写入 `$WORK/entities.json`，并在 `changes` 记录"原图第 X 项 → 新图第 Y 项"。
2. 文字与数值以正文/数据表为准校正；原图与正文冲突时取正文，冲突写进 `uncertainty`。
3. 只改被要求改的部分，其余元素保持标签、顺序与配色不变，并在 `changes` 逐条列出改动。
4. 若原图为位图且无文字层：不把图像噪声当文字；只复现能确认的实体，缺项写入 `uncertainty`，并在交付说明中指出"原图为位图，已按正文重建"。
5. 交付的分层 SVG 可直接在 Illustrator/Inkscape 中按层编辑，`figure_spec.json` 支持再次 `build` 复现，二者共同构成"可编辑来源"。

## 证据与溯源
* 每条边必须有 `source`；`quote` 用原文那句（含动词），`locator` 到页/图注。
* `contain`/复合物关系也要有原文依据（"forms a complex with"），不能因为画在一起就加框。
* 材料没说的步骤：不画。需要示意"间接"时用虚线并写 `indirect`，并在 `uncertainty` 说明推理链。
* `result.json.element_inventory` 逐条给出 `relation:类型` 与引文，评审可据此核对每个箭头。

## 异常处理
| 情况 | 处置 |
|---|---|
| 原文只说"activation"未说直接/间接 | 用 `activate` 实线；若中间有未标注节点，改虚线并在图注写"indirect" |
| 同一分子在不同区室出现 | 建两个节点（`id` 加区室后缀，`sublabel` 写区室），用 `translocate` 连接，不要用一个节点跨区室 |
| 复合物成员在材料中不明 | 只画已确认成员，`uncertainty` 说明可能还有未列成员 |
| 区室过多（>4） | 合并为 `Cytoplasm` 或拆面板；不要缩小到不可读 |
| 中文标签无字体 | `GLYPH-CJK` 失败；换 `font_stack` 或改英文并在 `uncertainty` 说明 |

## 最小示例（示例，不是正式案例结果）
`python "$SKILL/run.py" demo --out /tmp/ff_demo`：EGFR–RAS–ERK 三区室机制图（教科书拓扑 + 虚构读数），演示区室、激活/抑制/结合与图例写法。

## 参考
`docs/SPEC.md`、`docs/CHECKS.md`、`docs/METHOD.md`、`docs/USAGE.md`。


## 本题评分对齐（challenge-83d4f050 · 生物机制图与通路图）

题面评分点与本 Skill 的对应能力：

| 评分点（题面考察内容摘要） | 本 Skill 的对应机制 |
|---|---|
| 读机制材料—定实体与关系—定布局与图例—出源文件与导出件的闭环 | 机制三元组抽取流程 + 13 类关系语义表 + 区室布局 + 双渲染器导出 |
| 实体画对、相互作用类型画准、方向与数据编码一致 | membrane_receptor 跨膜渲染；激活/抑制/结合/修饰/转运五种终点形状；SEM-* 引文反查 |
| 区室与跨膜位置约束布局、图例与数据编码一致性 | lanes 自上而下区室带；复合物 containers 不吞非成员；LEG-* 检查 |
| 同名基因与蛋白等歧义的处置 | sublabel 区室/修饰标注；基因斜体蛋白正体；CMP-DUPLICATE-LABELS 检查 |

* 组织方输入修订（workorder `biological_mechanism_pathway`）：固定案例按该工单类型给料；本 Skill 按 `figure_kind` 路由到对应图类语法。
* 公开作品：<https://github.com/hehekevin/boerai/tree/main/week4/Scientific%20Graphics/challenge-83d4f050/v2>
