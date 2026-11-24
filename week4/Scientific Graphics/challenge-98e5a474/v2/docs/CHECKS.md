# 自检清单 · Verification checks

`build` 在出图后自动运行 25 项检查，写入 `<stem>_checks.json` 与 `result.json.checks`，并在终端打印 `FAIL` 项及其修复建议。`fail` 会把 `status` 降为 `partial`，`--strict` 时返回码为 2。

## A 证据与溯源

| ID | 判定 | 含义与修复 |
|---|---|---|
| `EVID-IDs` | fail | 元素引用了未定义的 evidence 键。在 `evidence` 中补齐。 |
| `EVID-NODES` | warn | 有实体没有 `source`。逐个绑定引文。 |
| `EVID-EDGES` | warn | 有关系没有 `source`。逐条绑定引文。 |
| `EVID-QUOTE-PRESENT` | fail | 引文在材料文本中找不到（容忍空白/断词，≥80% 词命中）。回到材料复制原句，不要改写。 |
| `EVID-QUOTE-FILLED` | warn | evidence 条目缺 `quote`。 |
| `EVID-LOCATOR` | warn | evidence 条目缺 `locator`。写 `p.7, Fig. 3 legend` 或 `table 2, row 5`。 |

## B 语义

| ID | 判定 | 含义与修复 |
|---|---|---|
| `SEM-RELATION-WORD` | fail | 关系类型与引文动词冲突（引文只有抑制动词却画成激活，反之亦然）。改 `type` 或换正确引文。 |
| `SEM-DIRECTION` | warn | 引文中目标实体出现在来源实体之前且中间有动词，方向可能画反。核对 `from`/`to`。 |
| `SEM-LEGEND-TYPES` | warn | 用了箭头语义但图例没有解释。为每种关系加图例项。 |

## C 数值与单位

| ID | 判定 | 含义与修复 |
|---|---|---|
| `NUM-TRACEABLE` | fail | 图面标签中的数字在材料文本或数据表中找不到。删掉该数字或补证据。 |
| `NUM-CAPTION` | warn | 图注中的数字在材料中找不到（常来自任务说明）。保持与来源一致。 |
| `UNIT-CONSISTENT` | warn | `unit` 与坐标轴标签括号内单位不一致，或有单位无轴标签。统一为一个单位。 |

## D 图例与数据映射

| ID | 判定 | 含义与修复 |
|---|---|---|
| `LEG-EXISTS` | warn | 无图例。只要颜色/线型/箭头编码含义就必须有图例。 |
| `LEG-UNIQUE` | fail | 图例键重复。 |
| `LEG-LABELS` | fail | 图例项无文字。 |
| `LEG-MATCHES-DATA` | fail | 颜色图例项数与数据分类数不一致。逐个分类一项，不多不少。 |

## E 版面几何

| ID | 判定 | 含义与修复 |
|---|---|---|
| `GEO-CANVAS` | fail | 文字超出画布。缩短标签或改用更宽的画布预设。 |
| `GEO-OVERFLOW` | warn | 标签宽于所在方框。缩短或让布局换行（引擎已自动缩放字号）。 |
| `GEO-NODE-OVERLAP` | fail | 两个实体框重叠。减少同列实体数或换画布比例。 |
| `GEO-CONTAINER` | warn | 包含框与非成员相交。调整成员或顺序。 |
| `GEO-TEXT-OVERLAP` | warn | 文字互相压叠。移动标注或增大间距。 |
| `GEO-EDGE-CROSSINGS` | warn | 连线交叉过多。调整同列顺序或改 `route`。 |
| `GEO-FILL` | warn | 内容不足画布宽 55%。缩小画布或放大元素。 |

## F 完整性与字形

| ID | 判定 | 含义与修复 |
|---|---|---|
| `CMP-CAPTION` | warn | 无图注，符号、n、误差线没有定义。 |
| `CMP-AXIS-UNITS` | warn | 定量坐标轴没有单位。 |
| `CMP-PANEL-LETTERS` | warn | 多面板但没有面板字母。 |
| `CMP-RELATIONS` | warn | 只有实体没有关系。补关系或说明这是清单图。 |
| `CMP-DUPLICATE-LABELS` | warn | 实体标签重复，读者无法区分。加同工型/区室限定。 |
| `GLYPH-CJK` | fail | 有中文标签但环境无中日韩字体，会渲染成方框。装 Noto Sans CJK 或改 `font_stack`。 |

## 导出检查（`export_report.checks`）

`pdf_present`、`pdf_vector_text_embedded`（PDF 内嵌 TrueType 字体，文字可编辑）、`pdf_text_selectable`（`pdftotext` 能取出文字）、`pdf_single_page`、`pdf_size_matches_canvas`、`png_present`、`png_dpi_ok`（≥300）、`svg_layers`、`svg_text_editable`、`rgb_color`。任一项为 false 会写入 `limits`。

## 修复循环
1. `python run.py verify --spec spec.json --work work` 只看失败项。
2. 按 `fix` 字段改 spec（不要改渲染器）。
3. 重新 `build`，直到 `fail` 为 0。仍有 `warn` 时，把不能消除的项写进 `uncertainty`，`result.json.limits` 会如实保留。
