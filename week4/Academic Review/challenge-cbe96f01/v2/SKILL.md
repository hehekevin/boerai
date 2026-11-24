---
name: citation-fact-check
description: "Citation-support and fact verification: side-by-side comparison of in-text claims with cited-source snippets (supported/partial/unsupported/undeterminable), cross-section numeric consistency, and a validated findings ledger. Use when: a case asks whether citations support their claims, whether facts trace to reliable sources, and whether every conclusion lands on a located evidence span. NOT for: live database lookups, plagiarism checking, polishing, or judging the research conclusions themselves."
---

# 引用与事实核验：引用存在 ≠ 引用支持结论

面向"引用是否支持结论、事实来源是否可靠、证据定位是否落得到原文"三件事。引擎做确定性簿记：crosscheck 把每条本文论断与被引文献片段并排列出并给四态建议（完整支持/部分支持/不支持/无法判定）；consistency 核对正文/表格/图注/摘要之间的数字与样本量一致性；findings 验证器保证每条结论指到具体原文位置。Agent 做语义对齐判断——核心是把"引文存在"与"引文支持该句"分开。

## 何时使用
* 用例给出稿件 + 被引文献片段/快照，要求条目化核验清单（位置、原文、判定、严重度、修改建议）。
* 判定标准：每条结论指到具体原文位置；判定与引文语义一致；换一个人按记录复核能得到同一批结论。

**不适用**：论文润色、综述写作、数据分析建模；不联网核验（只用案例提供的来源快照），不替代作者对研究结论的判断。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（稿件、被引文献片段/快照、参考文献表等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <稿件文本>
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 抽取待核论断。** 从稿件收集带引用的论断句（`arkit.locate.find_mentions` 找 `\[\d+\]`/`(Author, year)` 锚点），整理 `pairs.json`：`[{claim:{quote,locator,ref_key}, source:{quote,source_id,locator}}]`——source 引文片段只能来自案例材料快照，取不到就留空。

**第 2 步 引用支持判定。** `python -m arkit.crosscheck $WORK/pairs.json $WORK/crosscheck.json`：每对输出 side-by-side（本文论断‖被引片段）+ 内容词重叠 + 四态建议。Agent 逐对确认或驳回并写理由；source 为空 → undeterminable 进待复核，**不得**臆断不支持。识别"结论超出引文范围"的过度推断：claim_only 关键词列出论断独有内容词辅助判断。

**第 3 步 数值与事实一致性。** `python -m arkit.consistency <稿件文本> $WORK/consistency.json`：摘要/正文/图表间数字、样本量、百分比冲突观察，两处定位并列，Agent 结合单位与语境确认。

**第 4 步入册、验证与报告。** 确认的引用/事实问题写台账（type=citation|fact；kind 区分 error/insufficient_evidence/suggestion；判定与严重度依据必填）；`python -m arkit.findings validate $WORK/ledger.json <稿件文本>`；`python -m arkit.report ...` 出报告。覆盖事实核验、引用支持、方法设计、统计报告、论证链、学术规范六类时按 checklist 销项。

## 本题判据对齐（题面"三件事"原文）
1. **"每条结论是否能指到具体原文位置"** → 台账强制 quote+locator，验证器核对摘录真实存在；crosscheck 保留双侧定位串（本文位置+被引片段位置）。
2. **"判定是否与引文语义一致"** → side-by-side 并列 + 内容词重叠分数 + claim_only/source_only 词表，判定理由必须引用两侧文本；四态含"无法判定"。
3. **"换一个人按记录复核能否得到同一批结论"** → pairs/crosscheck/ledger/report 全部 JSON 落盘，来源快照 sha256 进 result.json sources。

## 交付物
* `report.md`/`report.json`（核验清单）、`ledger.json`、`crosscheck.json`（论断-片段并列）、`consistency.json`、`pairs.json`（冻结输入）。

## 证据与审计规则
* 引用判定四态：完整支持/部分支持/不支持/无法判定；source 片段缺失时只能是"无法判定"。
* 保留事实核验、引用支持、方法设计、统计报告、论证链、学术规范六类的检查记录（checklist），不只报发现的问题。
* 正文数字、样本量、显著性表述在摘要/正文/图注间自相矛盾时，两处摘录并列入册。
* 撤稿/版本不一致：仅当案例材料提供该信息时引用，注明出处；不联网查询、不编造来源状态。

## 异常处理
| 情况 | 处置 |
|---|---|
| 被引原文/快照不可得 | undeterminable + 待复核，不臆断 |
| 引文严重歧义（多义对应多条目） | 标 needs_review 并写核对点 |
| 材料显示来源撤稿或版本不一致 | 入册 norm/citation 发现并附材料内证据 |
| 数据库权限不足/原文取不到 | 记 uncertainty，status=partial |
| PDF 无法解析 | 审可读部分，缺口进 limits |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：crosscheck demo 演示 supported/unsupported/undeterminable 三态与 side-by-side 输出；findings demo 演示伪造摘录被驳回；端到端合成案例走完整流程。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-cbe96f01/v2
