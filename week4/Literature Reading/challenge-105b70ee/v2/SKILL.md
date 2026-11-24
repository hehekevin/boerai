---
name: evidence-anchored-field-extraction
description: "Extract paper conclusions, experimental conditions and key data into a typed field table with per-field verbatim evidence locators and layered conclusion labels (stated/limited/speculative); distinguishes not_reported from extraction failure. Use when: a case asks to pull structured fields (samples, conditions, metrics, values with units/errors) out of a real paper's text, tables and captions. NOT for: summarizing without locators, unit conversion that rewrites original values, or systematic-review inclusion decisions."
---

# 文献结论与数据提取：统一字段表，每个字段回到原文

聚焦方向：**字段级证据定位 + 结论分层**。把散落在正文、表格、图注里的结论与数据按统一字段表还原成可核对结构；Agent 负责阅读理解与字段取值判断，引擎负责字段齐备、证据逐字、数值字面一致、"未报告/抽取失败"区分的可复算校验。

## 何时使用
* 用例给出一篇（或多篇）论文与字段要求，要结构化抽取实验条件、关键指标、研究结论。
* 判定标准：值与原文字面一致、单位/误差/条件随值记录、每个字段指回页码/段落/表格行列/图注。

**不适用**：无定位的摘要式压缩、擅自换算改写原值、系统综述纳排。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（论文文本/PDF、表格、图注、补充材料文字）。

## 输出（写入 /app/output）
`result.json` + `fields.json`（字段表抽取结果）+ `fielddict.json`（字段定义与抽取口径，随结果一并提交）+ `fields_report.json`（引擎校验）+ `report.md`。

`fields.json` 每条字段：`{value, unit?, status: extracted|not_reported|failed, layer?: stated|limited|speculative, evidence: {loc, quote}, note?}`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 定字段表。** 按题面要求整理 `fielddict.json`：`[{name, type: text|number|enum|list, unit?, required?}]`。正文、表格、图注、补充材料是同一字段表的不同来源，不是四份任务。

**第 2 步 逐字段取值。** 先定位后取值：
```bash
python -m lrkit.locate search "$WORK/blocks.json" "<字段关键词>"
```
数值连同单位、误差、统计显著性与成立条件一起抄录；跨页表格按表号+行列定位（loc 记为 `table.T1.r3` 这类可读形式）。

**第 3 步 分层标注。** 结论性字段标 `layer`：`stated`（作者明确结论）、`limited`（带限制条件的结论）、`speculative`（"可能/提示/suggest"类推测）——推测不得改写成确定事实。

**第 4 步 缺项分类。** 找不到的字段二选一：`not_reported`（通读相关材料后确认原文未给，写 note 说明查过哪些位置）或 `failed`（材料有但读不出，如扫描件无文本层）。两者不得混用。

**第 5 步 引擎核验。**
```bash
python -m lrkit.fields validate "$WORK/fielddict.json" "$WORK/fields.json" "$WORK/blocks.json" "$WORK/fields_report.json"
```
校验内容：每个 extracted 字段的 quote 逐字存在；数值字段的值必须字面出现在引文中（不允许 152 抽成 215）；单位与字段表一致；required 字段标 not_reported 必须带 note。

**第 6 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/fields.json" --artifact report="$WORK/report.md"
```

## 本题判据对齐（题面评分点 → 引擎机制）
1. **"按统一字段表抽成结构化结果，正文/表格/图注/补充材料当作同一份字段表的不同来源"** → fielddict 一份schema 驱动全部来源；blocks.json 统一 loc 体系。
2. **"字段值与原文字面一致，数值、单位、误差、统计量和条件限定不被改写"** → 数值必须字面出现在逐字引文中（fields 校验强制），单位随值记录。
3. **"作者明确结论、限制条件与推测性表述被区分"** → layer 三级标注，非法值被引擎拒绝。
4. **"缺项区分原文未报告与抽取失败"** → status 三值强制互斥，required 字段 not_reported 须附查证说明。
5. **"字段定义与抽取口径随结果一并提交，他人可按同一字段表复跑"** → fielddict.json 是交付物之一。

## 交付物
* `fields.json`、`fielddict.json`、`fields_report.json`、`report.md`（含每字段定位与分层说明）。

## 证据与审计规则
* extracted 字段必须带逐字 evidence；引文最长 240 字符，含数值的字段引文中必须出现该数值字面。
* 不换算、不合并、不四舍五入原值；确需派生值时另开字段并写公式。
* 推测性表述只进 layer=speculative，且 note 引原文措辞（如 "may generalize"）。
* 表格跨页/合并单元格：loc 记全表号与行列范围，note 说明还原方式。
* 材料冲突的多个数值：全部照录并分别定位，写进 uncertainty，不擅自取其一。

## 异常处理
| 情况 | 处置 |
|---|---|
| 扫描件无文本层 | 该来源字段标 failed + 原因；status 降 partial |
| 表格跨页/合并单元格 | loc 记表号+行列范围；还原规则写 note |
| 单位缺失 | unit 留空并在 note 说明，不猜单位 |
| 字段原文未报告 | not_reported + 查证位置说明 |
| 多条来源数值冲突 | 全录+分别定位+uncertainty，status 降 partial |
| 字段表与题面不完全匹配 | fielddict 保留题面字段并增补，problems 说明差异 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：模块 demo 演示字段表校验（含"数值被改写""伪引文"被抓出的反例）+ 端到端合成案例。示例中的催化剂数据均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-105b70ee/v2
