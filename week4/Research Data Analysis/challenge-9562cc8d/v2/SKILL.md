---
name: scientific-chart-spec
description: "Choose scientific chart types from data shape with explicit justification and rejected alternatives, then validate every axis, unit, error representation and series mapping against the data profile before any figure is drawn. Use when: a case asks to turn research data into report-grade figures with correct chart type, encoding, annotation and an auditable data-to-figure chain. NOT for: image beautification, post-hoc pixel editing, or figures whose elements cannot be traced back to profiled columns."
---

# 科研数据可视化：先定口径与选型，图上每个元素都能回指源数据

判断可视化做对不看图多漂亮，而看图上每个视觉元素是否与源数据一一对应、过程能否被他人按记录重跑。本技能把"画图"拆成两段确定性工作：dakit.charts 按数据形态产出 chart spec（图型、编码、被否决项及理由），并用数据画像做一致性校验；清洗与统计口径由 dakit.clean/dakit.stats 留账；Agent 依据 spec 生成绘图代码与图注。

## 何时使用
* 用例给出数据表（宽表/长表、含缺失列、类型混杂、中文列名）要求出图、选图型、写图注。
* 判定标准：图型与数据结构匹配；坐标轴、单位、图例、误差线含义与源数据一致；从数据到成图可被独立复跑逐元素核对。

**不适用**：实验设计、统计方法创新、论文写作、图像后期美化；引擎不直接渲染图片（离线标准库环境），它产出并校验 spec——绘图由 Agent 按 spec 执行。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（数据表、数据字典、期刊/报告导出要求）。

## 输出（写入 /app/output）
`result.json`（case_id + output_contract 全字段 + status/sources/uncertainty/changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" tables  --work "$WORK"
python -m dakit.profile "$WORK/tables.json" "$WORK/profile.json"
```

**第 1 步 口径确认。** 画图前先清洗：`rules.json` + `python -m dakit.clean table.json rules.json $WORK/clean.json`；缺失/异常/重复处置写进图注依据。统计口径（均值/中位数、sd/se/ci95）由 `dakit.stats` 计算落 `stats.json`，图上不得出现手算数字。

**第 2 步 图表选型。** 写 `shape.json`（intent ∈ distribution/comparison/relation/trend/composition，x_type/y_type，n_categories，has_time）后 `python -m dakit.charts shape.json - $WORK/chart_spec.json`：得推荐图型 + justification + rejected（如"无序分类比较不用饼图""时间序列不画并列柱"）。

**第 3 步 一致性校验（出图前必做）。** 用 `dakit.charts.validate_spec(spec, profile)` 核对：轴变量类型与图型匹配（line 的 x 必须是 date/有序数值）、声明单位与表头单位提示一致、同轴多系列单位一致、误差表示 ∈ sd/se/ci95、基线不得截断、禁 3D、双轴给警告、类别超限转 barh/聚合。校验不通过不改图硬出。

**第 4 步 绘图与图注。** Agent 按通过的 spec 生成绘图代码（matplotlib 可用则用，不可用则交付 spec+数据+绘图脚本）；图注必须可独立读懂：样本量、统计方法、误差线定义、单位、清洗口径引用 clean_ledger 条目。

**第 5 步 报告回填。** `python -m dakit.report tpl.md stats.json report.md mapping.json`，正文数字与图上数字同源。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact data=$WORK/chart_spec.json \
    --artifact stats_json=$WORK/stats.json
```

## 本题判据对齐（题面原文 → 机制）
1. **"图表类型与数据结构不匹配，例如把无序分类的比较画成饼图、把时间序列画成并列柱"** → 选型规则表显式否决这两类错配并给理由（demo 断言）。
2. **"误差线不写清是标准差、标准误还是置信区间"** → validate_spec 强制 error ∈ {sd, se, ci95}，缺失即警告、非法即拒绝。
3. **"坐标轴处理不当，截断基线"** / **"量纲差异大"** → 基线截断=problem 拒绝；同轴单位冲突=problem 拒绝。
4. **"过程不可复核，换一台机器重跑得到另一张图"** → spec+stats.json+clean_ledger 全落盘，绘图代码以这些为唯一输入。

## 交付物
* `chart_spec.json`（选型+理由+被否决项+校验结果）、`stats.json`、`clean_ledger.json`、绘图脚本与图注（report.md）、回填映射 `report_mapping.json`。

## 证据与审计规则
* 图上每个元素可回指：轴→profile 列、单位→表头提示或数据字典、误差→stats.json 字段。
* 校验不通过的 spec 不得出图；如人工坚持，须在 uncertainty 写明并接受降级。
* 类别聚合（"other"）必须先在 rules.json 定义规则并进清洗账本，不许只在图上合并。
* 近似披露：统计环节的正态性（偏度/峰度经验规则）、方差齐性（Brown–Forsythe）均为近似，限度写入图注或报告。

## 异常处理
| 情况 | 处置 |
|---|---|
| 类别过多（>12） | 自动转 barh 并警告；聚合须走清洗规则 |
| 占比类 >5 类 | 否决饼图，改 stacked bar |
| 时间列实为文本 | profile 标 type=date 的才允许时间轴；text 拒绝 line |
| 多系列单位冲突 | 拒绝同轴，要求归一化或分面 |
| 绘图后端不可用 | 交付 spec+校验+绘图脚本，status=partial 并说明 |
| 样本量 <20 | 图注强制标注 n，误差解释保守化 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：charts demo 验证六类选型规则与单位冲突/文本时间轴/基线截断的拒绝逻辑；另有 6 个模块 demo + 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-9562cc8d/v2
