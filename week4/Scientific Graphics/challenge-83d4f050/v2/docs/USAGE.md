# 使用说明 · Usage

## 0. 环境与依赖
* Python ≥ 3.9。必需：`matplotlib`、`numpy`（科学 Python 环境自带）；可选：`Pillow`（TIFF/PNG 元数据）、`openpyxl`（xlsx；缺失时用内置 zip+XML 解析）、`pdftotext`/`pyMuPDF`/`pypdf`（PDF 取文），`cairosvg`/`rsvg-convert`/`inkscape`/ImageMagick（PDF/PNG 兜底）。
* 字体：中文标签需要任一中日韩字体（推荐 `Noto Sans CJK SC`）。字体缺失时 `GLYPH-CJK` 会失败并把原因写进 `result.json.limits`。
* 无需联网、无需安装本仓库以外的数据。

## 1. 目录
```
<skill-dir>/
├── SKILL.md              # 本赛道的调用说明
├── run.py                # 唯一入口
├── engine/               # 抽取、规格、布局、渲染、校验、导出的实现
├── docs/                 # SPEC / CHECKS / METHOD / USAGE
├── resources/            # 配色、关系语义、期刊预设、题集
└── examples/             # 最小示例（示例数据，非正式案例结果）
```

## 2. 五步流程
```bash
export SKILL=/skills/weekly-skill         # 技能安装位置；按实际路径调整
export WORK=/app/work                      # 中间产物
export OUT=/app/output                     # 正式交付物

# 1) 看清输入：case.json 的键、文件清单、指令文本、output_contract
python "$SKILL/run.py" probe --case /input/case.json --input /input --out "$WORK"

# 2) 抽取材料：正文分页、表格按列解析，带页码/表行定位
python "$SKILL/run.py" extract --work "$WORK"

# 2b) 把数据表直接打印成 JSON 行，避免手抄数值出错
python "$SKILL/run.py" table --work "$WORK" --list
python "$SKILL/run.py" table --work "$WORK" --index 1 --limit 200

# 3) 读材料、写规格（唯一需要判断力的一步，见 SKILL.md 的"图面语法"）
#    先写 work/spec.json，再进第 4 步

# 4) 出图 + 自检 + 生成 result.json
python "$SKILL/run.py" build --spec "$WORK/spec.json" --out "$OUT" --work "$WORK" --stem figure

# 5) 按 FAIL 的 fix 提示改规格，重跑第 4 步，直到 fail=0
python "$SKILL/run.py" verify --spec "$WORK/spec.json" --work "$WORK"
```

## 3. 产物
| 文件 | 内容 |
|---|---|
| `figure.svg` | 分层可编辑源文件：`layer-canvas/lanes/containers/edges/nodes/charts/annotations/legend/title/caption/framing`，活文字，元素带 `data-tag`/`data-src` |
| `figure.pdf` | 矢量 PDF，内嵌 TrueType 字体，单页，尺寸=画布 |
| `figure.png` | 600 dpi 位图（`canvas.dpi` 可改） |
| `figure.tif` | 600 dpi LZW TIFF（可按需 `--no-tiff` 关闭） |
| `figure_preview.png` | 1600 px 预览，便于快速检查 |
| `figure_spec.json` | 本次实际使用的规格（含自动补全后的画布） |
| `figure_checks.json` | 25 项自检结果 |
| `figure_provenance.csv` | 元素 → 引文 → 定位 → 原文 |
| `figure_report.md` | 人读摘要：元素统计、检查表、导出参数、限制 |
| `result.json` | 结构化结果：`case_id`、`output_contract` 回填、产物路径、元素清单、数据映射、检查、来源、不确定性、修改记录、运行信息 |
| `run.log` | 时间戳日志 |

## 4. 最小示例（示例，不是正式案例结果）
```bash
python "$SKILL/run.py" demo --out /tmp/figforge_demo
```
输出 `example_figure.svg/.pdf/.png`：一张三区室机制图 + 一个带误差线与显著性括号的柱状图，对应 `examples/example_spec.json`、`examples/example_source.txt`、`examples/example_data.csv`。示例内容为教科书通路 + 虚构数值，用于演示接口，**不得当作正式案例结果引用**。

## 5. 常见操作
* 换期刊尺寸：`canvas.preset` 改为 `nature_single`/`science_double`/`elsevier_double`，或直接给 `width_mm`/`height_mm`。
* 换导出格式：`build --no-tiff` 关闭 TIFF；`canvas.dpi` 改分辨率。
* 只改一个标签：改 `spec.json` 中该元素的 `label`，重跑 `build`，其余几何与来源不变。
* 数据更新后重绘：改 `charts[].data.rows`，柱高、坐标、图例项数随之变化，`LEG-MATCHES-DATA` 会复核分类数。
* 只想要矢量源文件：`build` 总会写 SVG；PDF/PNG 失败时 `result.json.export_report.attempts` 会记录每个兜底后端的结果。

## 6. 失败与降级
| 情况 | 行为 |
|---|---|
| `/input/case.json` 不存在或不是 JSON | `probe` 仍列出 `/input` 下全部文件并给出提示；规格照常可写，`case_id` 记为 `unknown-case` |
| 材料是扫描 PDF（无文字层） | `extract` 记录 `error`；不要臆造内容，把该来源写入 `uncertainty` 并只使用可读材料 |
| 数据表缺列/有空值 | 该行被跳过，`charts` 元数据记录实际使用行数；缺列时 `CHART_NO_DATA` 报错 |
| 中文无字体 | `GLYPH-CJK` fail + `limits` 说明；PDF 仍生成，但字形可能缺失 |
| matplotlib 不可用 | 自动回退 cairosvg/rsvg/inkscape/ImageMagick；全部失败时保留 SVG 并在 `status` 与 `limits` 中说明 |
| 规格为空 | `EMPTY_FIGURE` 报错，`status=failed`，仍写出 `result.json` 说明原因 |
