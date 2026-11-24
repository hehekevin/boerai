---
name: thesis-longdoc-consistency
description: "Write and revise thesis/long academic documents with chapter planning tied to outline and word budget, cross-chapter terminology/symbol consistency, claim-to-citation binding, and chapter-level change records. Use when: a case asks to draft, extend, or repair chapters of a thesis/long document from fixed materials while keeping facts, terms and citations consistent. NOT for: inventing literature or facts beyond the materials, or wholesale rewriting when only local edits were requested."
---

# 学位论文与长文档写作：立得住、连得上、改得动、查得清

面向长文档任务。本技能把长文写作拆成可复跑的簿记：章节规划对齐提纲与字数、术语表机械套用、论断-文献绑定、修订逐条留痕。Agent 负责写作与语义判断，引擎负责一致性、覆盖、引用与数字的机械校验。

## 何时使用
* 用例给出提纲/导师意见/科研材料，要求生成或改写章节，并保持跨章节一致与可追溯。
* 判定标准：章节与提纲对应；术语符号前后一致；每条论断可追溯到材料或文献；改动可回退。

**不适用**：虚构文献与数据；把局部修改指令执行成整章重写。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（提纲、既有章节、参考文献、数据表、导师意见等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 章节稿、术语表、引用校验、改动记录（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact document=$WORK/thesis.md --artifact provenance=$WORK/claims_report.json \
    --artifact data=$WORK/changes.json --artifact report=$WORK/consistency_summary.json
```

**第 1 步 章节规划。** 从提纲整理 `plan.json`：章节顺序、每节论证任务、字数预算、所需证据清单；用 `coverage check` 把必需要点落成可核对项。

**第 2 步 术语与符号表。** 整理 `terms.json`（含 banned_zh 异体写法）；写作与改稿后跑 `bilingual check` 保证同一概念同一写法。

**第 3 步 写作 + 论断绑定。** 写章节时同步填 `bindings.json`（事实句→材料/文献引文）；跑 `claims validate --strict`：含数字句子必须挂绑定，推导数字登记 computed；材料不足处用【材料不足】标注，不硬写。

**第 4 步 引用与格式。** `citecheck check` 保证正文引用键全部解析到文献表、条目字段齐全；`formatcheck check` 按学校/期刊 spec 核标题层级、编号与分节字数。

**第 5 步 按意见改稿。** 把导师/评审意见拆成离散编辑操作 `ops.json`，`revisions apply` 逐条落改前/改后/依据；改写幅度过大自动标 drift_warning；改完对受影响句重跑 claims。

**第 6 步 跨章节巡检。** `structcheck check` 检测跨节重复片段、结论无支撑、循环论证，并把强因果词列入 scope_review 供逐条确认。

## 本题判据对齐（题面"四个问题"）
1. **立得住** → plan.json 把章节与提纲、论证任务、字数预算一一对应；coverage 缺项即失败。
2. **连得上** → bilingual 术语表机械套用 + structcheck 跨节重复/结论呼应检测，改动一处可定位受影响段落。
3. **改得动** → revisions 锚点必须唯一命中才执行，作者逐条 accept/reject，drift_warning 防整段覆盖。
4. **查得清** → claims 逐句绑定 + citecheck 引用解析 + changes.json 全程留痕，他人可独立复核。

## 交付物
* `thesis.md`（章节稿）、`plan.json`、`terms.json`、`claims_report.json`、`citecheck.json`、`format.json`、`struct.json`、`changes.json`、`consistency_summary.json`。

## 证据与审计规则
* 事实句无绑定 → 校验失败；编造引文（quote 非来源子串）→ 直接拒收。
* 引用不存在文献、引用了但结论被改写 → citecheck/claims 分别抓出并记录。
* 每次改动留 before/after/reason；拒绝的修改不进成稿。
* 长上下文失控风险：按章节分文件写作，合并后统一跑全套校验。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料缺失支撑不起论断 | 【材料不足】标注 + uncertainty，status 降 partial |
| 引用找不到原文 | bindings 报 quote_not_in_source；替换为可定位引文或删论断 |
| 章节间结论冲突 | structcheck 列出冲突位置，Agent 裁决并记录 |
| 编号不连续/层级跳跃 | formatcheck 逐项列出，修复后复检 |
| 超长截断 | 分章处理并在 changes.json 记录处理范围，不静默丢段 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo + 一次端到端（合成 case → probe → extract → claims/deck → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-32c0210d/v2
