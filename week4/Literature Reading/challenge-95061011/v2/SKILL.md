---
name: multi-paper-comparison-matrix
description: "Compare several papers on one research question in a single field dictionary: per-cell values verified verbatim against the paper they are attributed to, two-level alignment (unified field definitions + condition comparability with subset detection), conclusion consistency and conflict attribution to concrete condition differences with both sides quoted. Use when: a case provides 5-10 papers on one question and asks for a comparison table, method matrix, conflict explanation or evidence-integrated report. NOT for: comparing papers on different questions, cells without source evidence, or meta-analysis statistics."
---

# 多文档比较与整合：同一套字段、逐格可回、冲突可归因

聚焦方向：**共同字段抽取 + 方法与条件两级对齐 + 冲突归因**。Agent 负责逐篇阅读与取值判断，引擎负责字段字典约束、单元格逐字核验、可比性子集划分与冲突归因候选——每个单元格都能回到它标注的那篇论文的具体位置。

## 何时使用
* 用例给出同一研究问题下的多篇论文，要论文对比表、方法矩阵、结论冲突提示或整合报告。
* 判定标准：字段落到同一套定义、取值来自所标论文、差异有可归因的解释、全表可复跑核对。

**不适用**：不同研究问题的横向罗列、无出处填表、统计级 meta 分析。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（多篇论文文本、比较维度要求）。

## 输出（写入 /app/output）
`result.json` + `fielddict.json`（统一字段字典）+ `matrix.json`（比较表，逐格带证据）+ `matrix_report.json`（单元格核验）+ `comparability.json`（可比性判定）+ `conflicts.json`（冲突归因）+ `report.md`（整合报告）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"   # 每篇论文一个 source 编号 S1..Sn
```

**第 1 步 定字段字典。** `fielddict.json`：`[{name, definition, unit?, comparability: direct|subset|not_comparable, note?}]`，覆盖对象/数据/方法/条件/指标/结论/局限七组字段；定义写到"逐格对照有意义"的粒度（如"60 min 可见光降解率"而非"性能"）。

**第 2 步 逐篇抽取填表。** 每篇论文按字段字典取值，写 `matrix.json` 单元格：`{paper_id, field, value, unit, evidence: {loc, quote}, status}`——取不出的保 status（not_reported），不编造；单位、数据集、评价口径随值记录。

**第 3 步 单元格核验。**
```bash
python -m lrkit.matrix validate "$WORK/fielddict.json" "$WORK/matrix.json" "$WORK/blocks_by_paper.json" "$WORK/matrix_report.json"
```
每格 quote 必须逐字存在于**它所标注的那篇论文**；单位与字段字典不一致必须先换算并记录。

**第 4 步 可比性判定。** 登记各论文关键条件（光源功率、样本量、数据集版本、基线…）：
```bash
python -m lrkit.matrix comparability "$WORK/fielddict.json" degradation_pct "$WORK/conditions.json" "$WORK/comparability.json"
```
两级对齐：字段定义统一（字典）+ 条件可比性。条件不一致 → subset 判定并给出可比子集，只允许在子集内排名。

**第 5 步 冲突归因。**
```bash
python -m lrkit.matrix conflict degradation_pct "$WORK/conflict_entries.json" "$WORK/conflicts.json"
```
结论方向矛盾时，引擎按条件差异给出归因候选（样本/方法/条件/指标），Agent 回原文确认写理由；冲突双方原话并列保留，无法归因的标 unresolved 而不是强行解释。

**第 6 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/matrix.json" --artifact report="$WORK/report.md"
```

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **对得齐** → 字段字典唯一定义 + comparability 声明；不在字典里的字段被核验拒绝，各写各的无法通过。
2. **填得准** → `validate_cells`：取值必须逐字来自所标论文；单位/口径随值记录且与字典一致。
3. **说得清** → `conflict_attribution` 按条件差异给归因候选，Agent 确认写理由；双方原话并列；unresolved 是合法结论。
4. **查得回** → 每格 evidence（loc+quote）+ 全表 JSON 落盘，新加论文只需增量填表与重跑核验，不重做全表。

## 交付物
* `fielddict.json`、`matrix.json`、`comparability.json`、`conflicts.json`、`matrix_report.json`、`report.md`。

## 证据与审计规则
* 单元格无证据不得标 extracted；status=not_reported 是合法取值。
* 只在 comparability=direct 或同一 subset 内做横向排名/结论比较，跨子集比较必须在报告中注明条件差异。
* 冲突结论不取平均、不投票；归因到具体条件差异，双方原话保留。
* 同一论文多版本：以案例指定版本为准并在 sources 注明。
* 材料主题不相关的论文：从比较集合剔除并写明剔除理由。

## 异常处理
| 情况 | 处置 |
|---|---|
| 某论文 PDF 解析失败/图表无法读取 | 该论文相关单元格标 failed + 原因，status 降 partial |
| 字段在某论文完全未报告 | 单元格 not_reported，表中留空不编造 |
| 论文主题不相关 | 剔除 + 理由，不进分母 |
| 同一论文多版本 | 指定版本为准，sources 注明 |
| 结论矛盾且无法归因 | conflicts 标 unresolved，不强行解释 |
| 单位口径不一致 | 先换算并记录公式，再填表；无法换算标 not_comparable |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：matrix demo 演示单元格核验（含"单位口径不符被抓出"）、subset 可比性划分与 lamp_w 条件归因。示例论文数据均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-95061011/v2
