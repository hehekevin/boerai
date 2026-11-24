---
name: deep-research-orchestrator
description: "Run a deep-research task as an auditable pipeline: decompose the research question into independently retrievable subquestions with dependencies, plan searches with order and stop conditions, log every tool call, and synthesize conclusions where every sentence links back to a specific source passage. Use when: a case asks for multi-step literature research with decomposition, retrieval planning, evidence-linked conclusions and conflict adjudication. NOT for: single-paper close reading, metadata/methodology fact-checking, full-text translation, or writing polish."
---

# 深度研究 Agent：文献综述——综合证据，也说明边界

面向"把一个需要多步推进的研究问题走完整条链路：拆解 → 检索规划 → 多步工具调用 → 证据综合"的任务。本技能把整条链路变成可复跑的确定性簿记：Agent 负责语义判断（子问题写法、相关性、裁决、措辞），引擎负责结构校验、依赖检查、停止判据、证据回链校验与审计轨迹——每一步落盘为 JSON，第三方可按记录复跑。

## 何时使用
* 用例给出研究问题与一批材料/检索入口，要求完成深度研究并交付带回链证据的结论。
* 判定标准：子问题可独立检索且依赖明确；每条结论能回链到具体文献段落；冲突结论被比较裁决而非搪塞；研究空白有检索记录依据。

**不适用**：单篇文献逐句精读、文献元数据与事实的方法学审查、全文翻译、写作润色。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、PDF、表格、检索结果等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 以下各步的中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact evidence_matrix=$WORK/matrix.json \
    --artifact data=$WORK/synthesis_audit.json
```

**第 1 步 问题拆解。** Agent 把研究问题拆成子问题清单 `plan.json`：`{question, subquestions:[{id, text, searchable_terms, depends_on, evidence_required}]}`。每个子问题必须可独立检索（searchable_terms 非空），依赖标清。校验：`python "$SKILL/run.py" qplan validate $WORK/plan.json $WORK/plan_check.json`——重复 id、空检索词、未知依赖、依赖环都会被拒绝。

**第 2 步 检索规划与迭代。** 按依赖序（qplan 输出的 suggested_order）安排检索；前置检索先行，无依赖的可并行。每轮检索记入 `ledger.json`：`{rounds:[{n, action, params, returned, new_items, kept, signal, decision}], covered_ref_ids}`。停止判据由引擎算：`python "$SKILL/run.py" iterloop signals $WORK/ledger.json` 与 `iterloop stop $WORK/ledger.json`——连续零边际收益或目标覆盖完成才停，不得以轮数代替充分性。检索记录同时落盘 `queries.json`：`[{id, subq_id, string, source, returned, kept}]`（空白分析要用）。

**第 3 步 证据矩阵。** 每篇采用文献登记 `sources`；每条判断写成 claim：`{id, text, subq_id, supports:[{source_id, quote, locator}]}`。quote 必须是原文摘录，locator 必须到页/段/行。校验：`python "$SKILL/run.py" evidence validate $WORK/matrix.json $WORK/matrix_check.json`——无摘录+定位的断言被拒绝。去重合并用 `identity`（合并日志记录规则与字段冲突）。

**第 4 步 冲突裁决。** `evidence suggest` 给出同子问题异极性的候选冲突对；Agent 逐对确认并写 adjudication：`{comparison, resolution: a_stronger|b_stronger|both_bounded|genuinely_unresolved, basis}`。校验：`python "$SKILL/run.py" evidence conflicts $WORK/matrix.json $WORK/conflict_check.json`——comparison 过薄（如只写"尚存争议"）或 unresolved 无依据都会被拒绝。

**第 5 步 综合与边界。** 结论逐句写入 `synthesis.json`：`{conclusions:[{id, sentence, class: fact|inference|undetermined, subq_id, claim_ids, basis}], gaps:[...]}`。审计：`python "$SKILL/run.py" synthesis audit $WORK/synthesis.json $WORK/matrix.json $WORK/synthesis_audit.json $WORK/plan.json`——fact/inference 必须回链 matrix 中存在的 claim；inference 必须写推理依据；undetermined 必须写清缺什么（诚实标注是要求的行为）；每个子问题必须被覆盖或显式标缺口。

**第 6 步 研究空白。** `python "$SKILL/run.py" gaps map $WORK/plan.json $WORK/queries.json $WORK/evidence.json $WORK/coverage.json` 生成检索覆盖图；空白主张写入 `gaps.json` 后 `gaps validate`——searched_* 类空白必须引用真实执行过的 query_id；未检索范围必须标 `speculation:true`；与检索记录矛盾的"无证据"主张被拒绝。

## 本题判据对齐（题面原文的"三件事"）
1. **研究问题被拆成了哪些可独立检索的子问题** → plan.json + qplan validate（searchable_terms 强制非空、依赖无环、suggested_order 可复算）。
2. **每条结论能否回链到具体文献段落** → matrix.json 的 quote+locator 强制校验 + synthesis audit 拒绝悬空引用。
3. **整条路径能否被他人按记录复跑** → inputs.json（含 sha256）、ledger.json（逐轮参数/返回/信号）、全部 *_check.json 审计文件落盘。

## 交付物
* `report.md`（主综述/评估）、`matrix.json`（证据矩阵）、`synthesis.json`+`synthesis_audit.json`（带边界的结论）、`plan.json`/`plan_check.json`、`ledger.json`、`queries.json`、`coverage.json`/`gaps.json`/`gaps_check.json`、`conflict_check.json`。

## 证据与审计规则
* 引擎只做簿记与校验；quote 是否真在原文中，由 Agent 对照 extract 落盘文本逐条核对后在 matrix 中记录定位。
* 不编造来源：claim 的 source_id 必须在 sources 登记；synthesis 的 claim_ids 必须在 matrix 存在。
* 材料没有的内容不补：写 `undetermined` + basis，status 降级 partial 并在 uncertainty.json 说明。
* 冲突必须并列呈现并比较双方证据，不允许只取一方或一句"尚存争议"了事。

## 异常处理
| 情况 | 处置 |
|---|---|
| 检索为空（某子问题 0 返回） | 如实记入 queries.json（returned:0），空白走 searched_no_evidence，不得编文献 |
| 工具报错/材料解析失败 | 记入 changes.json，该来源标记不可用，uncertainty.json 说明影响范围 |
| 证据互相冲突 | 进 conflicts 并 adjudication；genuinely_unresolved 须写清为何比较无法判定 |
| 子问题始终证据不足 | synthesis 中标 undetermined+gaps 标 searched_insufficient，status=partial |
| 依赖成环/重复 id | qplan validate 拒绝，回到第 1 步修正拆解 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：8 个引擎模块 demo（含负例：无回链断言、"尚存争议"搪塞、无依据空白均被拒绝）+ 一次端到端（合成 case → probe → extract → qplan/evidence/synthesis 校验 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Deep%20Research%20%26%20Literature%20Review/agent-f8fb8bda/v2
