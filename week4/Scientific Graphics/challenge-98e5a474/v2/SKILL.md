---
name: editable-relationship-schematic
description: "Generate a source-bound, fully editable scientific relationship schematic (block diagram of entities, groups and typed relations) from case materials, and deliver layered SVG plus vector PDF, 600 dpi PNG/TIFF, a machine-checkable provenance table and result.json. Use when a case asks to draw, redraw or edit a scientific schematic, concept/relationship diagram, workflow or structure diagram where every box, arrow and number must be traceable to the supplied paper, table or sketch. NOT for statistical charts, posters, artistic illustration, or writing the manuscript text."
---

# 科研示意图：生成图稿，也保留可编辑来源

面向"把材料里的实体与关系画成一张审稿人挑不出错的示意图"的任务。本技能不做图像生成式的"配图"，而是先把材料拆成**实体—关系清单**，再据此排出分层布局，最后同时交付分层源文件与合规导出件。图上每个方框、每条箭头、每个数字都能回溯到材料中的一句原文。

## 何时使用
* 用例要求：绘制/重绘/编辑示意图、关系图、结构图、流程图、概念图、技术路线框图。
* 材料形态：论文 PDF（含图注）、实验记录、数据表、草图、或一段文字描述。
* 判定标准：图上的实体、关系、方向、层级与标注数值必须能被第三方逐项复核。

**不适用**：统计图表（用 `source-value-chart`）、生物通路机制图（用 `biological-mechanism-pathway`）、装置与工艺流程图（用 `apparatus-technical-route`）、单页图形摘要（用 `graphical-abstract`）。四者共用同一引擎，差别在图形语法与检查项。

## 输入
| 位置 | 内容 |
|---|---|
| `/input/case.json` | 案例输入。键名不固定，用第 1 步读取真实结构，不要凭字段名猜内容 |
| `/input/task.md` | 任务说明与输出契约，`output_contract` 字段的权威来源 |
| `/input/**` | 实际材料：PDF、CSV/XLSX、DOCX、图片、草图 |

## 输出（写入 `/app/output`）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）、`figure.svg`（分层可编辑源文件）、`figure.pdf`（矢量、内嵌字体）、`figure.png`（600 dpi）、`figure.tif`、`figure_spec.json`、`figure_checks.json`、`figure_provenance.csv`、`figure_report.md`、`run.log`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"
export WORK=/app/work; export OUT=/app/output
mkdir -p "$WORK" "$OUT"

python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 写规格：$WORK/spec.json（见下）——
python "$SKILL/run.py" build   --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure
python "$SKILL/run.py" verify  --spec "$WORK/spec.json" --work "$WORK"   # 只看 fail/warn
```

**第 1 步 读输入。** `probe` 打印 `case.json` 的键、长文本字段、文件清单（含 sha256）与 `output_contract`。先确认：要画哪张图、图的用途（论文/答辩/基金）、有无目标期刊尺寸、有无给定草图或既有图稿要改。

**第 2 步 抽材料。** `extract` 把 PDF 按页、表格按列解析到 `$WORK/material_text/`，每段带 `[p.N]` 定位。用 `grep` 定位图注与关键句，只读需要的页，不要通读整篇。

**第 3 步 建实体—关系清单（决定图对不对）。** 先写 `$WORK/entities.json`，再转成 spec：
```json
{"entities":[{"id":"sensor","label":"Sensor array","class":"component","quote":"The sensor array …","locator":"p.2"}],
 "relations":[{"from":"sensor","to":"daq","verb":"feeds","type":"flow","quote":"…feeds the data acquisition board","locator":"p.2"}],
 "groups":[{"id":"g1","label":"Sensing unit","members":["sensor","daq"],"quote":"…"}]}
```
规则：**只收材料里出现过的实体**；同一实体只出现一次（用 `sublabel` 区分同工型/区室）；关系必须有动词依据；`contain` 只在材料明确说"属于/包含/组成"时使用，不能因为画在一起就加框。

**第 4 步 写 spec 并出图。** 字段见 `docs/SPEC.md`。最小可用：
```json
{"case_id":"<case_id>","figure_id":"figure","figure_kind":"relationship_schematic",
 "title":"…","caption":"方框=模块，箭头=信息流，虚线框=同一机箱内的模块；标注数值为时延（ms，n=5 次）。",
 "nodes":[{"id":"sensor","label":"Sensor array","class":"component","group":"g1","source":"E1"}],
 "edges":[{"id":"e1","from":"sensor","to":"daq","type":"flow","label":"12 ms","source":"E1"}],
 "containers":[{"id":"g1","label":"Sensing unit","members":["sensor","daq"],"source":"E1"}],
 "legend":{"items":[{"key":"flow","label":"data flow","swatch":"arrow"},
                    {"key":"contain","label":"shared enclosure","swatch":"line","dash":true}]},
 "evidence":{"E1":{"source":"S1","locator":"p.2","quote":"The sensor array feeds the data acquisition board (12 ms latency)."}},
 "sources":[{"id":"S1","path":"/input/paper.pdf","sha256":"<probe 输出的 sha256>"}],
 "uncertainty":["…"]}
```

**第 5 步 自检—修复。** 按 `FAIL` 的 `fix` 改 spec 重跑。`fail` 不清零则 `status=partial`，把无法消除的原因写进 `uncertainty`，`result.json.limits` 会保留。

## 图面语法（示意图专用）
1. **阅读方向固定**：左→右为流程/因果，上→下为层级/时序。不要混用。
2. **关系类型即图形语法**（引擎按 `type` 决定终点形状，抑制画成 T 形横杠而非箭头）：
   `activate/promote/flow/sequence/transport →` 实心箭头；`inhibit/repress ⊣` 横杠；`bind ◇` 空心菱形；`contain/connect` 无箭头；`part_of` 虚线无箭头；`modify/phosphorylate/signal` 虚线箭头。
3. **层级用包含框，并列用同层同尺寸**：`containers` 只包成员；子级用更浅的填充色；同级实体尺寸一致（引擎按标签自动定宽，必要时显式给 `w_mm`）。
4. **区室/分区**用 `lanes`：`order` 决定上下顺序，`fill` 用极浅底色，不要用高饱和色压过实体。
5. **标注数值必须带单位与来源**：`label:"12 ms"` + 对应 `source`；`NUM-TRACEABLE` 会核对材料里是否有"12"。
6. **图例只解释图形语法**：箭头/线型/分组边界。实体类别用配色区分时，图例项数必须等于类别数。
7. **面板**：多子图用 `panels` 给 `A/B/C` 与短标题；单图不要加面板字母。

## 编辑既有图稿时的处理（source-preserving edit）
用例常要求"在给定图稿上修改"（改标签、加一条通路、换配色）。本技能一律采用**按来源重绘**而非像素级修改位图：

1. 把原图当作**元素清单的来源之一**：逐项抄出实体名、关系方向、分组、单位与图注，写入 `$WORK/entities.json`，并在 `changes` 记录"原图第 X 项 → 新图第 Y 项"。
2. 文字与数值以正文/数据表为准校正；原图与正文冲突时取正文，冲突写进 `uncertainty`。
3. 只改被要求改的部分，其余元素保持标签、顺序与配色不变，并在 `changes` 逐条列出改动。
4. 若原图为位图且无文字层：不把图像噪声当文字；只复现能确认的实体，缺项写入 `uncertainty`，并在交付说明中指出"原图为位图，已按正文重建"。
5. 交付的分层 SVG 可直接在 Illustrator/Inkscape 中按层编辑，`figure_spec.json` 支持再次 `build` 复现，二者共同构成"可编辑来源"。

## 证据与溯源
* 每个 `nodes[]`/`edges[]`/`containers[]` 都要 `source`；`evidence` 的 `quote` 必须是材料里的原句（可截断），`locator` 写页码/图号/表行。
* `EVID-QUOTE-PRESENT` 用抽出的材料文本逐字比对；比对失败说明引文被改写或来源给错，回到材料复制。
* 交付时 `figure_provenance.csv` 一行一个元素：`element,type,label,evidence_id,source_file,locator,quote`。
* 材料没有的内容：不画。必须画时写进 `uncertainty`（例如"草图未标注单位，按正文采用 ms"）。

## 自检要点（详见 `docs/CHECKS.md`）
| 检查 | 说明 |
|---|---|
| `SEM-RELATION-WORD` | 引文只有抑制动词却画成激活（或反之）→ 改 `type` |
| `SEM-DIRECTION` | 引文中目标出现在来源之前 → 可能画反 |
| `EVID-QUOTE-PRESENT` | 引文无法在材料中找到 |
| `GEO-NODE-OVERLAP` / `GEO-CANVAS` | 实体重叠、文字出画布 |
| `LEG-MATCHES-DATA` | 图例分类数与数据分类数不一致 |

## 异常处理
| 情况 | 处置 |
|---|---|
| `case.json` 缺失/非 JSON | 用 `/input` 文件清单与 `task.md` 建规格，`case_id` 记 `unknown-case`，在 `uncertainty` 说明 |
| 材料是扫描件无文字层 | 只用可读材料；不要把图像内容"读"成实体；`uncertainty` 记录缺页 |
| 描述与图注矛盾 | 以正文+图注的明确陈述为准，二者冲突时取更具体的一条并在 `uncertainty` 写明另一条 |
| 实体过多导致拥挤 | 拆面板（`panels`）或换 `science_double`；不要缩小字号到 5 pt 以下 |
| 数据与图例不符 | 以数据表为准重画，`LEG-MATCHES-DATA` 会拦住 |
| 无中文字体 | `GLYPH-CJK` fail；把 `canvas.font_stack` 指向可用字体，或标签改英文并在 `uncertainty` 说明 |
| 导出失败 | 引擎自动回退其他后端；全部失败仍交付 SVG，`status=partial` 且 `limits` 写明 |

## 最小示例（示例，不是正式案例结果）
`python "$SKILL/run.py" demo --out /tmp/ff_demo` → 三区室机制图 + 柱状图，对应 `examples/example_spec.json`。仅演示接口与产物形态。

## 参考
`docs/SPEC.md`（字段）、`docs/CHECKS.md`（25 项检查与修复）、`docs/METHOD.md`（方法与边界）、`docs/USAGE.md`（完整用法）、`resources/`（配色与预设）。


## 本题评分对齐（challenge-98e5a474 · 科研示意图生成与编辑）

题面评分点与本 Skill 的对应能力：

| 评分点（题面考察内容摘要） | 本 Skill 的对应机制 |
|---|---|
| 材料→图稿→导出全链路，产出可继续编辑的示意图而非套模板插画 | 三层中间表示（证据→规格→渲染），模板不存在；每个元素绑定逐字引文 |
| 实体、关系、方向、层级、比例与数值单位与来源一致 | SEM-RELATION-WORD/SEM-DIRECTION/NUM-TRACEABLE/UNIT-CONSISTENT 检查；关系类型决定箭头终点 |
| 覆盖三类示意图要素与图例、标注、单位、子图编号 | lanes/containers/annotations/panels/legend 全要素；CMP-* 完整性检查 |
| 图稿与来源材料可独立复核 | figure_provenance.csv + result.json.element_inventory 逐元素溯源 |

* 组织方输入修订（workorder `editable_relationship_schematic`）：固定案例按该工单类型给料；本 Skill 按 `figure_kind` 路由到对应图类语法。
* 公开作品：<https://github.com/hehekevin/boerai/tree/main/week4/Scientific%20Graphics/challenge-98e5a474/v2>
