---
name: revision-ledger-editing
description: "Client-style controlled manuscript editing: turn edit instructions into discrete anchored operations with before/after/rationale, accept/reject each revision, keep citation and numbering consistent, and export an editable document. Use when: a case asks to modify a manuscript per instructions with tracked, reviewable, reversible changes. NOT for: full-text rewriting unless explicitly instructed, or edits that cannot be located to an exact anchor in the current draft."
---

# 学术写作客户端：改得准、改得可追溯、格式不塌、交付可用

面向"接收稿件—按指令修改—保留修订—导出可编辑文档"的闭环任务。引擎把修改指令落成离散操作并机械校验锚点，作者可逐条接受/拒绝/回退；改后自动重查事实绑定、引用与格式，防止越改越坏。

## 何时使用
* 用例给出稿件 + 修改指令（措辞/结构/术语/引用层面），要求交付带修订记录的可编辑文档。
* 判定标准：修改落在指定位置与层面；每处改动可定位、有依据、可逐条接受或拒绝；导出后标题/编号/引用仍自洽。

**不适用**：未经指令的整段重写；无法锚定到原文的"凭感觉"修改。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（稿件 md/docx/txt、修改指令、参考文献库、导出要求等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 改后稿、逐条修订记录、引用/格式复检报告（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"   # docx 等抽成带定位文本
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact document=$WORK/draft_v2.md --artifact data=$WORK/changes.json \
    --artifact provenance=$WORK/claims_recheck.json --artifact report=$WORK/postcheck.json
```

**第 1 步 冻结原稿。** probe 记录原稿 sha256；抽取文本落盘 `draft_v1.md`，作为所有锚点的基准。

**第 2 步 指令拆操作。** 把每条修改指令拆成 `ops.json` 离散操作：`{id, op:replace|delete|insert_after, anchor, new, reason, scope:措辞|结构|术语|引用}`。锚点必须取自当前稿原文。

**第 3 步 应用与审定。** `python "$SKILL/run.py" revisions apply $WORK/draft_v1.md $WORK/ops.json $WORK/draft_v2.md $WORK/changes.json`：锚点不唯一/失效即拒绝该条；相似度过低标 drift_warning（防整段覆盖）。作者用 `revisions decide` 逐条 accept/reject 后重跑 apply。

**第 4 步 改后复检（格式不塌）。** 受影响句重跑 `claims validate`（数字与事实绑定可能失效）；`citecheck check` 查新增/删除引用后的编号与字段；`formatcheck check` 查标题层级与编号未塌。三项合成 `postcheck.json`。

**第 5 步 导出。** 交付 `draft_v2.md`（可继续编辑）；如需 PPTX/其他格式走 deck 等生成器并渲染验证；导出失败如实记录。

## 本题判据对齐（题面"四个问题"）
1. **改得准** → 锚点必须恰好命中一次才执行；scope 字段记录修改层面；drift_warning 标记幅度失控。
2. **改得可追溯** → changes.json 每条含 before/after/reason/decision，可逐条接受或拒绝。
3. **格式不塌** → 改后强制 citecheck+formatcheck 复检，编号、题注、参考文献同步。
4. **交付可用** → 原稿 sha256 + 修订全量留痕，可回退到任一已拒绝/已应用状态；导出失败进 uncertainty。

## 交付物
* `draft_v2.md`、`ops.json`、`changes.json`（修订台账）、`claims_recheck.json`、`postcheck.json`、`draft_v1.md`（冻结原稿文本）。

## 证据与审计规则
* 每条修订必须引用指令条目（reason）；无锚点修改不允许执行。
* 改写后事实句必须重新通过 claims 校验，否则该修订退回 pending。
* 引用域变动（增删引）必须同步文献表并复检编号连续性。
* 任何"执行不了"的指令写入 changes.json（result 字段）而非静默跳过。

## 异常处理
| 情况 | 处置 |
|---|---|
| 锚点在稿中出现 0 次 | 该条拒绝执行 + 提示指令与稿本版本可能不符 |
| 锚点出现多次 | 拒绝执行，要求 Agent 扩大锚点上下文至唯一 |
| 指令与稿件内容冲突 | 标 conflict 进 uncertainty，不强行执行 |
| 文档损坏/加密无法抽取 | extract 记录失败原因，status=failed 并说明 |
| 修订后引用断裂 | citecheck 报 unresolved；退回该修订或补文献条目 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（revisions demo 覆盖锚点失效/不唯一/拒绝/回退与 drift 标记）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-7b09c079/v2
