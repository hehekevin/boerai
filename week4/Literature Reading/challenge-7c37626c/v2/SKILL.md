---
name: formula-parsing-verification
description: "Parse paper formulas into checkable structure: LaTeX structural sanity checks, symbol extraction aligned to a variable table where every symbol has a paper-anchored definition (or is explicitly flagged as context/common-sense), stepwise derivation records with stated assumptions, and safe numeric substitution checks (AST whitelist) that catch sign/unit/order-of-magnitude errors with intermediate values. Use when: a case asks to transcribe formulas, explain variables, explain derivations or verify them numerically against a paper. NOT for: deriving new theory beyond the paper, symbolic CAS workloads, or guessing undefined symbols without flagging."
---

# 公式解析与数学推理：认得准、讲得清、推得顺、算得回

聚焦方向：**变量解释 + 数值核验**。Agent 负责识读公式与推导语义；引擎负责结构体检、符号—定义对齐（每个符号要么有原文定义要么显式标为推断/常识）、以及可复算的代入核验——符号错误、单位错误、数量级错误由同一套流程发现。

## 何时使用
* 用例给出论文公式（文本/片段）与解析要求：公式转 LaTeX、变量表、推导说明、数值代入核验。
* 判定标准：结构无歧义还原、符号定义可指回原文、推导步骤带假设、代入结果可复算。

**不适用**：超出论文的新理论推导、大规模符号计算、对未定义符号的无标注猜测。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（论文文本/公式片段、解析任务说明）。

## 输出（写入 /app/output）
`result.json` + `formulas.json`（公式 LaTeX+编号+定位）+ `variable_table.json`（符号—定义—单位—来源）+ `derivation.md`（分步推导+假设）+ `numeric_report.json`（代入核验，含中间值）+ `report.md`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 公式转写与结构体检。** Agent 把目标公式转成 LaTeX（行间公式、上下标、矩阵、分段函数、编号），写 `formulas.json`（含 loc）；逐条体检：
```bash
python -m lrkit.formula check "$WORK/formula_01.tex"
```
括号不配对、环境未闭合、上下标悬空、\frac 缺花括号——先修复再继续，不把结构错误带进变量表。

**第 2 步 变量表。** 引擎抽取符号候选，Agent 逐符号写定义：
```bash
python -m lrkit.formula vtable "$WORK/variable_table.json" "$WORK/formula_01.tex" "$WORK/blocks.json" "$WORK/vtable_report.json"
```
每条 `{symbol, meaning, unit?, range?, source: {kind: paper|context|common_sense, loc?, quote?}}`：paper 定义须逐字证据；常识补充必须 `flagged_assumption:true`——按常识猜测不加区分地写进变量表会被引擎拒绝。

**第 3 步 推导分步。** `derivation.md`：关键推导拆成可检查步骤，每步标所用假设、近似与边界条件；跨公式引用标依赖（式 3 用式 1 的近似）。Agent 写作，引擎的 blocks 定位保证引用可回查。

**第 4 步 数值代入核验。** 可计算公式写 steps：
```bash
python -m lrkit.formula numeric "$WORK/numeric_steps.json" "$WORK/numeric_report.json"
```
安全求值（AST 白名单，无内建任意调用）；每步留中间值；expect 不符时报 computed/expected 比值——比值接近 10 的幂时提示疑数量级/单位错误。

**第 5 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/variable_table.json" --artifact report="$WORK/derivation.md"
```

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **认得准** → `check_latex` 结构体检（上下标/括号层级/环境），结构错误先修不进下游；符号表与公式符号一一对齐（`symbols` 防漏符号）。
2. **讲得清** → `validate_variable_table`：每个符号有定义且区分 paper（逐字证据）/context/common_sense（强制 flagged_assumption）——常识猜测不加区分写不进表。
3. **推得顺** → derivation 分步带假设/近似/边界，跨公式依赖显式标注；每步定位可回原文。
4. **算得回** → `numeric_check`：代入留中间值、expect 不符报比值与排查提示；单位错误（kg 当 g）会被比值≈10³ 的信号抓出。

## 交付物
* `formulas.json`、`variable_table.json`、`derivation.md`、`numeric_steps.json`、`numeric_report.json`、`report.md`。

## 证据与审计规则
* 还原的 LaTeX 与原文符号一一对应；OCR 易混（0/O、l/1、上下标错位）在 vtable note 说明。
* 变量单位与取值范围随定义记录；单位缺失如实标空，不猜。
* 代入核验的数值必须来自原文（loc 可查）或显式标为示例值。
* 推导所用近似（如小角近似、忽略高阶项）逐步标注；不标近似的跳步视为缺陷。
* 代入无解/除零：numeric_report 记录 error，不静默跳过。

## 异常处理
| 情况 | 处置 |
|---|---|
| 公式图像模糊/截断 | 可还原部分先行，缺失符号标 illegible + uncertainty |
| 符号严重歧义（同一符号两种含义） | vtable 分行登记两种用法与各自 loc |
| 单位缺失 | unit 留空 + note；代入核验只做数值级并声明 |
| 代入无解/除零 | 记录 error 与中间值，status 降 partial |
| 原文公式本身疑似有误 | 不修改原文；在 report 记疑点并给核验依据 |
| 公式编号缺失 | 用 loc（页/段）为主键，编号作备注 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：formula demo 演示结构体检、变量表（含"缺定义""常识未标注"被抓出）与代入核验（2000 kg 当 2 kg 的比值=1000 数量级错误被抓出）。示例公式与数值均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-7c37626c/v2
