---
name: format-spec-conformance
description: "Adapt a manuscript to a target academic template: extract the format spec (headings, numbering, section lengths, reference field order, author truncation) into a checkable list, apply changes without altering content, and verify every item mechanically before export. Use when: a case asks to fit a real manuscript to a journal/thesis template with item-by-item verifiable results. NOT for: guessing template rules from experience, or letting format conversion delete/merge/rewrite content units."
---

# 学术格式与模板适配：认得准、排得对、转得全、交得出

面向模板适配任务。本技能先把模板/格式要求抽成结构化检查项清单（不凭经验猜），逐项机械核对；内容单元（正文、图表、公式、脚注、参考文献）在转换前后逐一比对，保证"格式改了、内容没动"。

## 何时使用
* 用例给出稿件 + 目标模板/格式规定，要求交付逐项符合的可编辑文件与核对记录。
* 判定标准：规格可逐项核对；标题层级/编号/题注/参考文献逐项符合；转换不丢内容；导出可用。

**不适用**：凭经验猜模板规则；以图片化方式"保版式"而牺牲可编辑性。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（稿件、模板文件、格式规定、字体要求等）。注：组织方修订记录要求使用随题提供的 Liberation Serif；字体缺失时按异常表处置。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 适配后稿件、检查项清单与逐项核对报告、内容保真比对（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"   # 模板与稿件都抽成文本/结构
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact document=$WORK/adapted.md --artifact report=$WORK/format.json \
    --artifact provenance=$WORK/fidelity.json
```

**第 1 步 抽规格。** 从模板文件与格式规定整理 `spec.json`：标题层级上限、编号制式、各节字数区间、参考文献字段顺序与作者截断规则、前置/后置必需块、字体要求（如 Liberation Serif）——每条注明来源（模板第几节/规定第几条）。

**第 2 步 基线核对。** `python "$SKILL/run.py" formatcheck check $WORK/draft.md $WORK/spec.json $WORK/format_before.json`：拿到逐项差距清单，而不是"看看差不多"。

**第 3 步 保真适配。** 格式改动走 `revisions apply`（锚定到具体标题/条目，逐条留痕）；参考文献条目重排字段顺序时逐条记录 before/after。

**第 4 步 内容保真比对。** 适配前后文本做句级比对：除 changes.json 已登记的格式操作外，不得出现内容增删；把比对结果写 `fidelity.json`（可用 `claims split_sentences` 的句 id 对齐）。

**第 5 步 复检与导出。** 重跑 `formatcheck check` 至 violations 清零；`citecheck check` 确认重排后引用键仍可解析。导出件（如需 PDF/PPTX）用 deck/soffice 渲染验证，字体缺失（含非 Liberation Serif 回退）如实记录。

## 本题判据对齐（题面"四个问题"）
1. **认得准** → spec.json 每条规格注明来源；不接受无来源的"经验规则"。
2. **排得对** → formatcheck 逐项核对层级/编号/字数/字段顺序/作者截断，violations 清零才算完。
3. **转得全** → fidelity.json 句级比对：未登记的内容差异一律视为丢失，退回修复。
4. **交得出** → 导出走真实渲染验证；字体嵌入/替换情况写入报告，可编辑源文件一并交付。

## 交付物
* `adapted.md`、`spec.json`（带来源的规格清单）、`format_before.json`/`format.json`（前后核对）、`fidelity.json`、`changes.json`。

## 证据与审计规则
* 每项"已适配"必须指到 spec.json 的具体条目；报告不手写"符合要求"。
* 内容单元差异只能来自 changes.json 登记的操作。
* 参考文献字段顺序按 style 配置机械判定；作者超编必须 et al/等。
* 模板版本不明或规定冲突时，两个版本都列出并取更严者，差异写 uncertainty。

## 异常处理
| 情况 | 处置 |
|---|---|
| 模板缺失或版本不明 | 用题面显式格式要求兜底，uncertainty 注明模板不可用 |
| 字体缺失（如要求 Liberation Serif） | 记录回退字体名，标 partial；不假装已嵌入 |
| 样式冲突/规定互相矛盾 | 两条规定都列出，取严执行并记录取舍 |
| 转换无法保真（公式/域代码） | fidelity 报差异单元，退回人工确认 |
| 导出失败 | 记录失败输出，交付可编辑源文件，status 降 partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（formatcheck demo 覆盖层级跳跃、字数越界、作者截断缺失）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-96263d10/v2
