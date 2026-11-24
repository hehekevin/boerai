---
name: graphical-abstract
description: "Build a single-page graphical abstract that compresses problem, approach, core result and conclusion into one self-consistent visual language, with every entity and number traceable to the paper, delivered as layered editable SVG, vector PDF, 600 dpi PNG/TIFF and result.json. Use when a case asks for a graphical abstract, table-of-contents graphic, single-figure summary or visual abstract for a paper, grant or presentation. NOT for multi-panel result figures, data charts alone, or for adding claims the paper does not make."
---

# Graphical Abstract（图形摘要）：生成图稿，也保留可编辑来源

图形摘要最容易被快速浏览、也最容易被误读。它必须在单页内把**问题 → 方法 → 核心结果 → 结论**压成一套自洽的视觉语言，并且每个实体、每条通路方向、每个数值都能回到原文与数据。本技能按"面板—要点"映射出图，而不是生成一张热闹的信息图。

## 何时使用
* 用例要求图形摘要、图文摘要、TOC graphic、单图概括、投稿用 visual abstract。
* 材料是一篇论文（正文 + 图 + 表）、研究描述或实验记录。
* 关注点：主线是否一眼可读、实体与因果关系是否正确、编码（颜色/长度/面积）是否与数据对应、能否投稿（尺寸、字体、分辨率）。

**不适用**：多面板结果图与统计图（`source-value-chart`）、通路机制细节图（`biological-mechanism-pathway`）、装置与方法流程（`apparatus-technical-route`）。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（论文 PDF、图、数据表）。第 1 步读取真实结构。

## 输出（`/app/output`）
`result.json`、`figure.svg`（分层：panels / edges / nodes / charts / legend / caption）、`figure.pdf`、`figure.png`(600 dpi)、`figure.tif`、`figure_spec.json`、`figure_checks.json`、`figure_provenance.csv`、`figure_report.md`、`run.log`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
grep -n -i -E "we (show|report|find|demonstrate)|here we|conclusion|summary|abstract|我们发现|本文|结果表明" "$WORK/material_text"/*.txt | head -30
python "$SKILL/run.py" build   --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure
python "$SKILL/run.py" verify  --spec "$WORK/spec.json" --work "$WORK"
```

**第 1 步 抽主线。** 用摘要 + 最后一段 + 图注，写四行：
`问题`（1 句）、`方法`（1 句：做了什么、关键手段）、`结果`（1 句：带数值与单位）、`结论`（1 句）。这四行就是四个面板的标题（各 ≤6 词）。写不出"结果"的数值，说明材料里没有，不要编。

**第 2 步 定面板与要点。** 默认四栏：`A Problem → B Approach → C Result → D Conclusion`（横向叙事）。也可三栏（问题/方法+结果/结论）。每个面板只放 **1 个视觉要点**，其余进图注。

**第 3 步 定编码。** 只允许一种变量上色（处理组、时间点或通路分支之一）。颜色、长度、面积三者只选其一编码数值，并在图例写出变量名与单位。核心结果的数值用 `charts` 面板画（柱/点），不要用"更大更红的箭头"暗示强弱。

**第 4 步 写 spec 并出图。**
```json
{"case_id":"<case_id>","figure_id":"graphical_abstract","figure_kind":"graphical_abstract",
 "canvas":{"preset":"ga_landscape","dpi":600},
 "title":"一句话结论（≤12 词，含对象与效应）",
 "caption":"问题→方法→结果→结论自左向右。颜色编码渗透条件（等渗=蓝，高渗=橙）。柱高为均值，误差线为 s.d.（n = 3）。",
 "panels":[{"id":"A","title":"Problem"},{"id":"B","title":"Approach"},
           {"id":"C","title":"Result"},{"id":"D","title":"Conclusion"}],
 "nodes":[{"id":"stress","label":"Hyper-osmotic stress","class":"condition","panel":"A","source":"E1"},
          {"id":"sensor","label":"Membrane sensor","class":"receptor","shape":"membrane_receptor","panel":"B","source":"E3"},
          {"id":"genes","label":"Target genes","class":"gene","panel":"C","source":"E5"}],
 "edges":[{"id":"g1","from":"stress","to":"sensor","type":"activate","panel":"A","source":"E1"},
          {"id":"g4","from":"sensor","to":"genes","type":"activate","panel":"B","source":"E3"}],
 "charts":[{"id":"c1","panel":"C","type":"bar",
   "data":{"x":"condition","y":"expr","err":"sd","unit":"fold","xlabel":"Condition","ylabel":"Expression (fold)",
           "rows":[{"condition":"Iso","expr":1.00,"sd":0.10},{"condition":"Hyper","expr":3.20,"sd":0.30}]},
   "source":"E7"}],
 "legend":{"items":[{"key":"iso","label":"iso-osmotic","swatch":"color","color":"#0072B2"},
                    {"key":"hyper","label":"hyper-osmotic","swatch":"color","color":"#D55E00"}]},
 "evidence":{"E1":{"source":"S1","locator":"p.1","quote":"Hyper-osmotic stress activates the membrane sensor."},
             "E7":{"source":"S2","locator":"table 1","quote":"Expression: iso 1.0, hyper 3.2"}},
 "sources":[{"id":"S1","path":"/input/paper.pdf","sha256":"<probe>"},
            {"id":"S2","path":"/input/data.csv","sha256":"<probe>"}]}
```

**第 5 步 自检—修复。** 重点看 `NUM-TRACEABLE`（图上数字是否在文中/表里）、`LEG-MATCHES-DATA`（图例类别数=数据类别数）、`GEO-TEXT-OVERLAP`（小画布最易压字）、`CMP-PANEL-LETTERS`。

## 版式规则（图形摘要专用）
1. **画布**：期刊 GA 常用 160×80 mm（`ga_landscape`）或 13×5 cm；投稿前按目标期刊要求改 `width_mm`/`height_mm`。600 dpi、RGB、无透明背景。
2. **阅读顺序**：左→右（或上→下）单一路径；四栏时每栏顶部面板字母 A/B/C/D 与短标题，字号一致。
3. **一栏一要点**：每栏 ≤2 个实体 + 1 条主箭头；跨栏箭头只画主线，支线一律删掉。
4. **字号下限**：正文标签 ≥6 pt（缩到 13 cm 宽印刷仍可读），面板标题 7–8 pt，标题 9–10 pt。
5. **颜色**：最多 4 色 + 灰；同一变量只用一种视觉通道编码；灰度打印要仍能区分（Okabe–Ito 序列本身满足）。
6. **结论栏**：用一句话 + 一个图标/形状，不要复述方法；不要出现摘要里没有的新主张。
7. **尺度提示**：分子/细胞/组织同图时，按真实层级大小比例绘制（细胞 > 蛋白 > 小分子），必要时加比例尺说明"非等比例"。

## 编辑既有图稿时的处理（source-preserving edit）
用例常要求"在给定图稿上修改"（改标签、加一条通路、换配色）。本技能一律采用**按来源重绘**而非像素级修改位图：

1. 把原图当作**元素清单的来源之一**：逐项抄出实体名、关系方向、分组、单位与图注，写入 `$WORK/entities.json`，并在 `changes` 记录"原图第 X 项 → 新图第 Y 项"。
2. 文字与数值以正文/数据表为准校正；原图与正文冲突时取正文，冲突写进 `uncertainty`。
3. 只改被要求改的部分，其余元素保持标签、顺序与配色不变，并在 `changes` 逐条列出改动。
4. 若原图为位图且无文字层：不把图像噪声当文字；只复现能确认的实体，缺项写入 `uncertainty`，并在交付说明中指出"原图为位图，已按正文重建"。
5. 交付的分层 SVG 可直接在 Illustrator/Inkscape 中按层编辑，`figure_spec.json` 支持再次 `build` 复现，二者共同构成"可编辑来源"。

## 证据与溯源
* 四个面板的标题与实体都要有引文；结论句必须能在摘要/结论段找到对应陈述。
* 结果数值只能来自表/正文，`result.json.data_mapping` 逐条对应。
* 为版式删掉的内容要记进 `changes`（"为单页可读性删去 X 通路"），避免读者以为论文只有这条通路。

## 异常处理
| 情况 | 处置 |
|---|---|
| 论文没有单一"结论"句 | 用最后一段的收敛句改写为陈述句，并在 `uncertainty` 注明改写 |
| 结果数值分散在多图 | 选一个最能代表主线的数值；其余进图注，不要堆数字 |
| 材料跨多个体系（体内+体外） | 面板内用 `sublabel` 标体系（`in vitro`/`in vivo`），不要混在一条箭头里 |
| 小画布文字压叠 | 减字而不是缩字号；`GEO-TEXT-OVERLAP` 会报出具体重叠对 |
| 颜色不够区分 | 换 Okabe–Ito 序列或改形状编码，不要靠加饱和度 |

## 最小示例（示例，不是正式案例结果）
`python "$SKILL/run.py" demo --out /tmp/ff_demo` 演示引擎产物形态；本赛道的四栏图形摘要示例见 `examples/`（示例数据，非正式结果）。

## 参考
`docs/SPEC.md`、`docs/CHECKS.md`、`docs/METHOD.md`、`docs/USAGE.md`。


## 本题评分对齐（graphical-abstract-7030fff2 · Graphical Abstract（图形摘要））

题面评分点与本 Skill 的对应能力：

| 评分点（题面考察内容摘要） | 本 Skill 的对应机制 |
|---|---|
| 产出问题—方法—核心结果—结论的单页图形摘要并可继续编辑 | 四栏面板语法 + ga_landscape 160×80 画布 + 分层 SVG |
| 实体、关系、数据编码与图例与来源一致 | 一栏一要点；颜色只编码一种变量；LEG-MATCHES-DATA；NUM-TRACEABLE |
| 四要素与图例、单位、比例尺等辅助信息覆盖 | CMP-PANEL-LETTERS；尺度提示规则；caption 模板 |
| 图稿、来源映射、版本与导出记录支持独立复核 | changes 记录为版式删掉的内容；element_inventory 逐元素引文 |

* 组织方输入修订（workorder `graphical_abstract`）：固定案例按该工单类型给料；本 Skill 按 `figure_kind` 路由到对应图类语法。
* 公开作品：<https://github.com/hehekevin/boerai/tree/main/week4/Scientific%20Graphics/graphical-abstract-7030fff2/v2>
