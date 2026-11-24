---
name: traceable-data-cleaning
description: "Clean and standardize literature-extracted data tables with a numbered, prioritized rule library: field mapping, unit conversion keeping original values and formulas, synonym normalization, duplicate detection with explainable keys, and row-level changelog traceable back to source rows and papers; uncertain values go to a review list, never silently changed. Use when: a case provides messy extracted tables from multiple papers and requires a clean, statistics-ready table plus change records. NOT for: inventing missing values, merging different experiments, or unit conversions that overwrite the original record."
---

# 文献数据清洗与标准化：规则有编号，改动追得回

聚焦方向：**可维护规则库 + 行级变更追溯 + 待确认清单**。引擎即规则执行器：字段映射、单位换算、同义归一、越界/缺失判定、重复检测全部按编号规则执行，每个被改动的值可沿 rule_id 回到输入行与原始文献；Agent 负责制定/确认规则与裁决 review 项。

## 何时使用
* 用例给出一批真实文献的抽取结果（CSV/JSON，列名不一、单位混杂、有重复与同义写法），要求清洗成可统计的数据表。
* 判定标准：转换公式与精度保留、合并按可解释判定键、每个改动可追溯、不敢确认的值单独列出。

**不适用**：编造缺失值、把不同实验错并成一条、无变更记录的"成品表"交付。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（抽取结果表、字段说明、单位/同义词线索）。

## 输出（写入 /app/output）
`result.json` + `cleaned.json`（清洗后数据）+ `rules.json`（规则库，有编号有优先级）+ `changelog.json`（行级变更记录）+ `review.json`（待人工确认清单）+ `report.md`（缺失/越界/冲突/换算/来源覆盖报告）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
```

**第 1 步 盘点脏数据。** 把各来源表整理为 `rows.json`：`[{row_id, source: {file, row|loc}, fields: {...}}]`——**原值与来源先行冻结**，后续只在此基础上留痕。统计列名差异、单位写法、缺失与重复模式，写进 report.md 的数据画像。

**第 2 步 定规则库。** 与题面要求对齐后写 `rules.json`：`[{rule_id, kind, priority, ...}]`，kind ∈ rename（字段映射）/unit（单位换算，带 factor+offset 公式）/synonym（同义归一）/range（越界判定，只标不改）/required（缺失判定，保持空缺）。每条规则注明适用条件与失效情形。

**第 3 步 执行清洗。**
```bash
python -m lrkit.clean apply "$WORK/rows.json" "$WORK/rules.json" "$WORK/clean_result.json"
```
输出含 cleaned rows + changelog（行级：row_id、rule_id、old/new、换算公式、source）+ review（换算冲突、无规则单位、越界、rename 冲突）。

**第 4 步 重复检测。**
```bash
python -m lrkit.clean dedup "$WORK/clean_result.json" "$WORK/dedup.json" "material,property"
```
判定键完全一致的 → 建议合并保留首条；判定键相同但其他字段有差异的 → "疑似同物质不同实验条件"，进 review 不自动合并（重复记录 ≠ 重复实验）。

**第 5 步 裁决 review 项。** Agent 逐条处理 review：确认/改规则/保持空缺，处理结果追加进 changelog（人工改动同样留痕）；裁决不了的在 report.md 写明并保留原值。

**第 6 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/cleaned.json" --artifact report="$WORK/report.md"
```

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **规得齐** → rename/synonym/required 规则把同一指标统一到同一字段名与允许值集合；规则有编号有优先级，可增删。
2. **换得准** → unit 规则记录原单位、目标单位与换算公式（new = old × factor + offset），changelog 同时保留原值；不可数值化的值进 review 不硬转。
3. **合得对** → dedup 按显式判定键分组；键外字段有差异的不自动合并，"重复记录"与"重复实验"分开。
4. **追得回** → changelog 行级记录（row_id + rule_id + source），任一输出值可回到输入行与原始文献；review 清单单列工具不敢确认的值。

## 交付物
* `cleaned.json`（可直接统计）、`rules.json`、`changelog.json`、`review.json`、`dedup.json`、`report.md`。

## 证据与审计规则
* 缺失保持空缺，不编造；required 规则只在 changelog 记 `missing_kept_empty`。
* 越界值只标记不修改（range 规则不产生 new 值）。
* 规则冲突（同字段多规则命中）进 review 并说明保留哪个。
* 重复运行同一输入必须得到同一 changelog（规则按 priority 稳定排序）。
* 人工对 review 的裁决也追加进 changelog，区分 engine/人工来源。

## 异常处理
| 情况 | 处置 |
|---|---|
| 单位无法识别/无换算规则 | 进 review 保留原值原单位，不猜换算 |
| 同义词冲突（一名多物） | 归一前回来源核对；存疑进 review |
| 值越界 | range 标记 + review，原值不动 |
| 编码错乱/空表 | probe 阶段报告，status 降 partial，不静默跳过 |
| 重复但实验条件不同 | 不合并，进 review 由人工确认 |
| 规则需要修改 | 改 rules.json 重跑，changelog 全量重算（可追溯） |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：clean demo 演示单位换算留痕（cm2/g→m2/g 带公式）、越界标记、同义归一与"同物质不同条件不自动合并"。示例数据均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-f4bca185/v2
