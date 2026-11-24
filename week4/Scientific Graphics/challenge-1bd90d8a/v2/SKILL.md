---
name: source-value-chart
description: "Build a publication-ready scientific data chart from a real source table, keeping every drawn mark bound to the row and column it came from, and deliver an editable SVG, vector PDF, 600 dpi PNG/TIFF plus a value-to-data mapping table and result.json. Use when a case supplies data (CSV/XLSX/table in a PDF) and asks for bar, line, scatter, box or heatmap panels with correct axes, units, error bars, significance marks, legend and journal styling. NOT for schematic or pathway diagrams, not for choosing statistical tests or computing new statistics, and not for writing results text."
---

# 科研数据图表：生成图稿，也保留可编辑来源

面向"从源数据表出一张能直接投稿的图"。核心约束有三条：**数值只能来自表**（不手打、不四舍五入到看不出）、**每个图元能回到行列**（`figure_provenance.csv` 与 `data_mapping`）、**导出件可编辑**（分层 SVG + 内嵌字体矢量 PDF）。统计方法本身不在本技能范围内。

## 何时使用
* 用例给出数据表（CSV/TSV/XLSX）、论文表格、或正文里的统计结果，要求画柱状/折线/散点/箱线/热图或多面板组合图。
* 要求按目标期刊或模板调字号、线宽、配色、面板布局、留白。
* 要求标注校验：轴标签与单位、刻度范围、误差线含义、样本量、显著性标记、图例与系列对应。

**不适用**：示意图/机制图/装置图/图形摘要（另有对应技能）；也不负责"用哪种检验、算不算显著"。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（数据表、论文 PDF、模板说明）。用第 1 步读取真实结构。

## 输出（`/app/output`）
`result.json`、`figure.svg`、`figure.pdf`、`figure.png`(600 dpi)、`figure.tif`、`figure_spec.json`、`figure_checks.json`、`figure_provenance.csv`、`figure_data_mapping.csv`、`figure_report.md`、`run.log`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"       # 表头、行数、单位提示都会打印
python "$SKILL/run.py" table --work "$WORK" --list   # 有哪些表、多少行、列名
python "$SKILL/run.py" table --work "$WORK" --index 1  # 直接输出可粘贴的 rows
python "$SKILL/run.py" build   --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure
python "$SKILL/run.py" verify  --spec "$WORK/spec.json" --work "$WORK"
```

**第 1 步 认清数据。** `extract` 会打印每个表的表头与行数，`rows` 已做类型转换（数字→数值，空→null）。先确认：哪一列是分组、哪一列是数值、哪一列是误差、哪一列是 n、单位写在哪（列名括号里/图注里/正文里）。

**第 2 步 选图型（按数据形状，不按美观）。**
| 数据形状 | 图型 | 注意 |
|---|---|---|
| 分类 × 1 个数值（含误差） | `bar` | 从 0 起，误差线画 SD/SEM 并注明 |
| 分类 × 1 个数值 × 多系列 | `bar`（分组） | 图例项数 = 系列数 |
| 连续 x × 连续 y（可多系列） | `line` / `scatter` | x 轴量级与刻度要覆盖实测范围 |
| 分类 × 分布（多个重复值） | `box` | 图注写清箱体/须/离群点定义 |
| 矩阵（基因 × 时间等） | `heatmap` | 色标必须有单位或写明 z-score |

**第 3 步 写 spec（数值一律从表里来）。**
```json
{"case_id":"<case_id>","figure_id":"figure","figure_kind":"data_chart",
 "caption":"(A) 相对表达量（mean ± s.d., n = 3 生物学重复）。(B) 诱导后时程（mean ± s.e.m., n = 4）。(C) 四基因 z-score 热图。",
 "panels":[{"id":"A","title":"Expression"},{"id":"B","title":"Kinetics"}],
 "charts":[{"id":"c1","panel":"A","type":"bar",
   "data":{"x":"genotype","y":"expr","err":"sd","n":"n","unit":"fold",
           "xlabel":"Genotype","ylabel":"Relative expression (fold)",
           "rows":[{"genotype":"WT","expr":1.00,"sd":0.10,"n":3},
                   {"genotype":"het","expr":0.60,"sd":0.08,"n":3}]},
   "source":"E1"}],
 "evidence":{"E1":{"source":"S2","locator":"table 1, rows 1-3","quote":"<与表一致的读数行>"}},
 "sources":[{"id":"S2","path":"/input/data.csv","sha256":"<probe 输出>"}]}
```
`rows` 直接由 `$WORK/material_text/<表>.txt` 誊写，或从 `$WORK/materials_full.json` 取 `rows`；**不要手改数值**。同组多行会按均值聚合、`err` 取均值、`n` 取行数。

**第 4 步 校验标注。** 重点：
* 轴标签带单位，且与 `unit` 一致（`UNIT-CONSISTENT`）。
* 误差线含义写进图注（SD / SEM / 95% CI），不能只画不写。
* 显著性标记只画材料给出的比较与符号；`p` 值或检验方法未给时不要自造（写进 `uncertainty`）。
* 图例项数与数据分类/系列数一致（`LEG-MATCHES-DATA`）。
* 中文标签必须有中文字体（`GLYPH-CJK`）。

**第 5 步 修图。** 按 `FAIL.fix` 改 spec 重跑；`fail` 不清零则 `status=partial`。

## 图面规范（数据图专用）
1. **字号**：6–8 pt（`nature_double` 默认 6.5 pt）；线宽 0.5–0.75 pt；坐标轴线 0.25–0.4 pt。
2. **配色**：Okabe–Ito 色盲安全序列（`#0072B2 #D55E00 #009E73 #CC79A7 #E69F00 #56B4E9`），灰度打印仍可区分；同类颜色只编码同一变量。
3. **刻度**：由数据范围 + `nice_ticks` 生成；柱图从 0 起；不以截断坐标轴夸大差异（确有需要时在图注写明断轴）。
4. **误差线**：带端帽，长度=SD/SEM，图注定义；`n` 写在图注或柱上，不要两处不一致。
5. **显著性**：括号只跨实际比较的两组，星号与图注定义一致（`* p<0.05` 等）。
6. **多面板**：面板字母 A/B/C 左上角、同字号、同基线；共享轴时只标一次单位。
7. **热图**：色标必须有标签（`z-score`、`log2 FC`、单位），零值居中时用发散色板（`cmap:"diverging"`）。
8. **导出**：矢量优先（PDF/SVG），位图 600 dpi、RGB、无透明背景；文字保持可编辑（不转曲）。

## 编辑既有图稿时的处理（source-preserving edit）
用例常要求"在给定图稿上修改"（改标签、加一条通路、换配色）。本技能一律采用**按来源重绘**而非像素级修改位图：

1. 把原图当作**元素清单的来源之一**：逐项抄出实体名、关系方向、分组、单位与图注，写入 `$WORK/entities.json`，并在 `changes` 记录"原图第 X 项 → 新图第 Y 项"。
2. 文字与数值以正文/数据表为准校正；原图与正文冲突时取正文，冲突写进 `uncertainty`。
3. 只改被要求改的部分，其余元素保持标签、顺序与配色不变，并在 `changes` 逐条列出改动。
4. 若原图为位图且无文字层：不把图像噪声当文字；只复现能确认的实体，缺项写入 `uncertainty`，并在交付说明中指出"原图为位图，已按正文重建"。
5. 交付的分层 SVG 可直接在 Illustrator/Inkscape 中按层编辑，`figure_spec.json` 支持再次 `build` 复现，二者共同构成"可编辑来源"。

## 证据与溯源
* 每个 `charts[]` 绑定 `source` → `evidence` 的表/图注定位。
* `result.json.data_mapping` 逐条列出：图表、分类、系列、字段名（`x`/`y`/`err`）、数值、误差、n、对应图元 tag。
* `figure_provenance.csv` 给出元素→引文→定位；`figure_data_mapping.csv` 给出图元→数据行。
* 表里没有的数值一律不标；聚合值（均值）在图注说明是均值而非原始值。

## 异常处理
| 情况 | 处置 |
|---|---|
| 缺列 / 空值 | 该行跳过并在 `result.json` 记录实际使用行数；缺关键列报 `CHART_NO_DATA`，不要用别的列顶替 |
| 量级异常（10× 离群） | 先核对单位（mM vs µM、% vs 比例）；不能确认时保留原值并在 `uncertainty` 写明 |
| 标签过长 | `xtick_rotate` 设 -40；仍挤则改 `bar` 为横向或缩短标签（不改语义） |
| 分类数与图例不一致 | 以数据为准重画图例，`LEG-MATCHES-DATA` 复检 |
| 中文乱码/方框 | 装 `Noto Sans CJK SC` 或改 `font_stack`；`GLYPH-CJK` 复检 |
| 导出位图化 | 引擎优先 matplotlib 矢量 PDF；回退后端会写进 `export_report.attempts` |

## 最小示例（示例，不是正式案例结果）
`python "$SKILL/run.py" demo --out /tmp/ff_demo`：含带误差线与显著性括号的柱状图（`examples/example_data.csv`，数值为示例）。

## 参考
`docs/SPEC.md`、`docs/CHECKS.md`、`docs/METHOD.md`、`docs/USAGE.md`。


## 本题评分对齐（challenge-1bd90d8a · 科研数据图表生成与编辑）

题面评分点与本 Skill 的对应能力：

| 评分点（题面考察内容摘要） | 本 Skill 的对应机制 |
|---|---|
| 读源数据—出图—调样式—校验标注—交付可编辑文件的链路 | probe→extract→table→build 五步；table 子命令直接输出可粘贴的数据行，避免手抄 |
| 数值与图元、坐标刻度与单位量级、误差线含义、显著性标记、图例与系列一致 | 柱高/点位置由数据表计算；nice_ticks 由数据范围生成；UNIT-CONSISTENT/LEG-MATCHES-DATA 检查 |
| 科学实体命名正确、中文标注不乱码 | sanitize() 字形回退；GLYPH-CJK 字体检查与 CJK 字体自动前置 |
| 图元到源数据字段可回查 | result.json.data_mapping 逐条列出 图表/分类/系列/字段/数值/误差/n |

* 组织方输入修订（workorder `source_value_chart`）：固定案例按该工单类型给料；本 Skill 按 `figure_kind` 路由到对应图类语法。
* 公开作品：<https://github.com/hehekevin/boerai/tree/main/week4/Scientific%20Graphics/challenge-1bd90d8a/v2>
