---
name: argument-logic-audit
description: "Logic and argumentation audit of a manuscript: claim extraction with attribution (author/cited/hypothesis), claim-evidence support checks, causal-vs-correlational language screening, cross-section consistency observations, and a validated findings ledger. Use when: a case asks to review a paper's claims, evidence support, reasoning chain and section-to-section coherence with sentence-level locations. NOT for: copyediting, plagiarism detection, reference-format checks, re-analysis of raw data, or journal selection."
---

# 论文逻辑与论证审查：主张与证据之间的断裂，逐条落到原句

面向"主张—证据—推理链—章节衔接"审查。引擎做确定性簿记：claims 抽取主张候选并标注归因（作者/转引/假设）、强度与因果标记；crosscheck 把本文论断与被引片段并排列出；consistency 找跨节数字冲突与摘要-正文缺口；findings 验证器保证每条问题可回原文核对。Agent 做语义判断——特别是区分"作者主张"与"转述他人观点/明确假设"，这是本场景最高频误报。

## 何时使用
* 用例给出论文全文，要求识别结论超出数据、引用不支持观点、推理跳跃、因果与相关混用、引言承诺未交付等逻辑问题。
* 判定标准：问题真实存在且能回到原文某一句话；定位精确到可直接核对；修改建议可执行。

**不适用**：文字润色、查重与不端判定、参考文献格式检查、原始数据重分析、投稿策略。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（稿件全文、被引文献片段/快照、图表文本等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <稿件文本>   # 预扫描+空台账+清单
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 主张抽取。** `python -m arkit.claims <稿件文本> $WORK/claims.json`：得主张候选清单（quote+定位+归因+强度+因果标记）。`review_queue.strong_causal_author_claims` 是优先核查队列；归因=cited_other/hypothesis 的句子**不得**报成作者自相矛盾。

**第 2 步 证据支撑核查。** 对每条作者主张找到支撑句（本文结果或所引文献）；涉及引用的用 `python -m arkit.crosscheck pairs.json $WORK/crosscheck.json` 把本文论断与被引片段并列，引擎给 supported/partial/unsupported/undeterminable 建议，Agent 确认或驳回并写理由。识别"结论超出数据"：主张强度（strong+causal）与证据类型（相关设计/小样本）不匹配时入册 logic 发现。

**第 3 步 推理链与章节衔接。** `python -m arkit.consistency <稿件文本> $WORK/consistency.json`：跨节数字冲突（如 n=42 vs n=40）、摘要独现数字、章节结构缺口；Agent 对照引言承诺与结果交付逐条确认。

**第 4 步 入册与验证。** 每条确认问题写入 `ledger.json`（type=logic/citation/fact，severity 必须带 severity_basis：是否影响主结论/是否可修正/是否影响可复现性），然后 `python -m arkit.findings validate $WORK/ledger.json <稿件文本>`——摘录不在原文的发现一律驳回留痕。

**第 5 步 报告。** 逐项销 checklist；`python -m arkit.report $WORK/ledger.json $WORK/checklist.json $WORK/report.json $WORK/report.md`。

## 本题判据对齐（题面"三件事"原文）
1. **"报出的问题是否真实存在，能否回到原文的某一句话"** → findings.validate 对每条发现做原文摘录核验（exact/fuzzy≥0.92），通不过即驳回；claims 归因标记防止把转引/假设误报为作者矛盾。
2. **"定位是否精确到评审可以直接核对，而不是只给章节名"** → locate.split_units 产出 §节 ¶段 s句 三级定位串；locator 不可解析的发现同样被驳回。
3. **"修改建议是否可执行，能说清补什么证据、改哪一句表述、把哪个结论的强度降下来"** → 台账 suggestion 为必填字段，报告把建议与摘录、定位同行呈现。

## 交付物
* `report.md`/`report.json`（按严重度排序的问题清单）、`ledger.json`、`claims.json`（主张清单+归因）、`crosscheck.json`（论断-被引片段并列）、`consistency.json`（跨节观察）。

## 证据与审计规则
* 每条发现必须有原文摘录+句级定位+判断依据+严重度依据，四缺一直被驳回。
* 引擎观察（数字冲突、强因果措辞）只是候选，Agent 结合上下文确认后才入册——有意设置的对照、明确标注的假设、转述他人观点不得判为缺陷。
* 长文截断必须在 limits 声明实际覆盖范围；跨章节矛盾不得因截断漏检而不报。
* 无法判定的引用标 undeterminable 并进 needs_review，不凭空补结论。

## 异常处理
| 情况 | 处置 |
|---|---|
| 长文被截断 | limits 声明覆盖范围，截断处标 needs_review |
| 被引文献原文不可得 | crosscheck 判 undeterminable，进待复核 |
| 归因歧义（作者 vs 转引） | 标 needs_review 并写明核对点，不直接入册 |
| 图表无法解析 | 对应衔接检查项标 needs_review |
| 重复运行 | 全部中间产物落盘 JSON，可逐条复算 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个模块 demo（claims 演示作者/转引/假设三归因，findings 演示伪造摘录被驳回）+ 端到端合成案例。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-16d4414d/v2
