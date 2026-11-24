---
name: structure-argument-audit
description: "Diagnose paper structure and logic: map claims to supporting evidence, detect broken/circular argument chains, cross-section redundancy and over-scoped conclusions, and emit executable edit actions (move/merge/split/narrow) with source locations. Use when: a case asks for a source-grounded structural review of a manuscript and an actionable editing plan in JSON/Markdown. NOT for: full unsolicited rewrites, language polishing, or inventing defects not present in the text."
---

# 论文结构与逻辑优化：诊得准、改得动、链得通、说得清

面向结构诊断任务。Agent 负责抽取论断与判定问题类型，引擎负责把判断落到可核对的位置：论点-论据映射、支撑图闭环与循环检测、跨节重复 12-gram 比对、结论尺度词标记——每条诊断都指回原文位置，每条建议都是可执行编辑动作。

## 何时使用
* 用例给出一篇完整稿件，要求六维结构诊断（研究问题/章节结构/论证链/段落关系/重复内容/结论边界）+ 作者可直接执行的修改方案。
* 判定标准：诊断指回原文位置；不虚构缺陷、不漏真实断裂；建议是移动/合并/拆分/收窄级别的动作。

**不适用**：整篇重写、语言润色、凭风格偏好下判语。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（稿件、参考文献、补充材料等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 结构诊断 JSON、可执行修改方案、论证链映射（见"交付物"）。按题面修订说明：可编辑 JSON/Markdown 即可，不强制 PDF 与整篇改写。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/diagnosis.md --artifact data=$WORK/edit_plan.json \
    --artifact provenance=$WORK/struct.json
```

**第 1 步 抽论证链。** Agent 逐章抽取论断与支撑，填 `chain.json`（claims/facts/where/evidence）；`python "$SKILL/run.py" structcheck check $WORK/paper.md $WORK/chain.json $WORK/struct.json` 机械验证：evidence 必须为原文子串、结论必挂支撑、支撑图无环。

**第 2 步 六维体检。** structcheck 一次产出：无支撑结论、循环论证、跨节重复候选（12-gram）、强因果/全称词 scope_review 队列；Agent 逐条确认是否构成问题、属于哪一类，杜绝"放之四海皆准"的套话。

**第 3 步 研究问题闭环。** 用 `coverage check` 核对：研究问题是否提出、是否贯穿、贡献主张是否与实际完成工作一致；缺失环节列入诊断。

**第 4 步 出可执行修改方案。** `edit_plan.json`：每条 `{issue_id, 类型, 位置(章节/句id), 依据(原文片段), action: move|merge|split|narrow|delete, target, rationale}`；action 级建议可再交 `revisions apply` 执行并留痕。

**第 5 步 结论边界。** scope_review 队列逐条对照证据强度：把因果/全称表述改写成数据支持的范围，或补限制说明；改写数字仍需过 `claims validate`。

## 本题判据对齐（题面"四个问题"）
1. **诊得准** → 每条诊断必须挂 where+evidence（原文子串），类型来自六维固定分类，不接受通用建议。
2. **改得动** → edit_plan 只含 move/merge/split/narrow/delete 级动作 + 目标位置，可交 revisions 逐条执行。
3. **链得通** → structcheck 强制结论挂支撑、检测循环论证与跳跃；覆盖核对研究问题闭环。
4. **说得清** → 判断依据为原文片段与定位，作者复核后可采纳/部分采纳/驳回并记录。

## 交付物
* `diagnosis.md`（六维诊断，逐条位置+依据）、`edit_plan.json`（可执行动作）、`struct.json`、`chain.json`、`coverage.json`（闭环核对）。

## 证据与审计规则
* 引擎拒绝定位不到的 evidence（fact_evidence_not_locatable），防止虚构缺陷。
* 重复内容只报候选（12-gram 共享），合并/保留由 Agent 裁决并写理由。
* 结论尺度只标记不裁决；收窄改写必须保留原数字来源绑定。
* 稿件截断/缺章节时如实降级 partial，诊断范围写入 limits。

## 异常处理
| 情况 | 处置 |
|---|---|
| 缺章节/无参考文献 | 按实有结构诊断，缺失环节列入 missing_rhetorical_roles |
| 稿件被截断 | uncertainty 声明截断点，诊断仅覆盖可见部分 |
| 图表/公式缺失 | 仅基于文字链诊断，limits 注明 |
| 论断无支撑但属背景常识 | Agent 标注 kind=background，不记违规但留记录 |
| 循环支撑疑似合理互引 | 列出 cycle 路径由 Agent 裁决，不自动判错 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（structcheck demo 覆盖无支撑结论/循环论证/编造证据/跨节重复）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-8021aacb/v2
