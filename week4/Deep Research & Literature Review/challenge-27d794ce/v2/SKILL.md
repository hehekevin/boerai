---
name: bounded-lit-review
description: "General-purpose deep-research and literature-review pipeline with bounded claims: question decomposition, retrieval ledger, dedupe with audit trail, evidence matrix with quote+locator per claim, conflict adjudication, sentence-level fact/inference/undetermined classification, and search-grounded gap statements. Use when: a case in the deep-research/literature-review area asks for an evidence-organized review, screening, trend or topic assessment with verifiable conclusions. NOT for: single-paper close reading, translation, writing polish, or fabricating completeness beyond provided materials."
---

# 深度研究与文献综述总课题：有边界的证据综述管线

面向深度研究与文献综述领域的通用任务：围绕固定研究问题组织文献证据，交付结论可回链、边界可说清的综述/评估。本技能是全赛道通用管线：拆解、检索、去重、证据矩阵、冲突裁决、结论分级、空白接地七个环节各有引擎校验器，每个环节的产物落盘 JSON，换一个人拿同样输入可复跑复核。

## 何时使用
* 用例要求围绕固定研究问题完成深度研究、综述、系统筛选、趋势分析或选题评估，并交付证据矩阵与不确定性说明。
* 判定标准：研究边界清晰；引用证据充足且可回链；综述结构来自材料而非套话；结论可追溯；无法确定的部分被如实标注。

**不适用**：单篇精读、全文翻译、写作润色、超出材料范围的事实担保。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、PDF、题录、检索结果等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。输出三件套对应题面契约：**研究产物**（综述/筛选/趋势/评估）、**证据矩阵**（来源+纳排理由+比较字段+定位）、**不确定性**（冲突、偏倚、空白、无法确定项）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 按任务类型选用以下环节，中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact evidence_matrix=$WORK/matrix.json \
    --artifact data=$WORK/synthesis_audit.json
```

**环节 1 拆解**（必有）：`plan.json` → `python "$SKILL/run.py" qplan validate $WORK/plan.json $WORK/plan_check.json`。

**环节 2 检索留痕**：逐轮记 `ledger.json`（signal+decision 强制）→ `iterloop signals/stop`；检索式落盘 `queries.json`。材料已给定而非现场检索时，把材料清单当作 queries 的等价物登记（source="provided_materials"）。

**环节 3 去重**：`python "$SKILL/run.py" identity $WORK/records.json $WORK/deduped.json`——DOI/标题/作者+年规则合并，冲突字段记日志。

**环节 4 筛选**（综述/筛选任务）：`decisions.json` → `python "$SKILL/run.py" screen validate $WORK/records.json $WORK/decisions.json $WORK/screen_check.json`——每条记录恰一条决定+理由码+证据片段；双人分歧 `screen conflicts`。

**环节 5 证据矩阵**（必有）：`matrix.json` → `evidence validate` + `evidence conflicts`——无 quote+locator 的断言被拒绝；冲突裁决不许"尚存争议"搪塞。

**环节 6 结论分级**（必有）：`synthesis.json` → `synthesis audit`——逐句 fact/inference/undetermined；悬空引用、无依据推断、静默遗漏子问题全部被拒。

**环节 7 空白接地**：`gaps map` → `gaps validate`——空白必须回指真实检索记录或标 speculation。

**环节 8 趋势**（趋势类任务）：`trendstat yearly/topics/signals/audit`（见 challenge-073af7d3 同款用法）。

## 本题判据对齐（题面原文的四步要求）
1. **明确研究问题、检索范围和纳排规则** → plan.json（qplan validate）+ decisions.json（screen validate）。
2. **整理文献并提取可比较的证据字段** → matrix.json 的 supports（quote+locator）与比较字段，evidence validate 强制。
3. **形成有来源定位的综合结论或评估** → synthesis audit：fact/inference 必须回链 matrix 中真实存在的 claim。
4. **区分材料事实、合理推断和无法确定的部分** → synthesis 三分类强制；undetermined 必须写清缺什么，是要求的行为而非失败。

## 交付物
* `report.md`（研究产物）、`matrix.json`（证据矩阵）、`synthesis.json`+`synthesis_audit.json`（边界化结论）、`plan.json`/`plan_check.json`、`ledger.json`/`queries.json`、`deduped.json`、`screen_check.json`（筛选任务）、`coverage.json`/`gaps.json`/`gaps_check.json`。

## 证据与审计规则
* 每条结论可回到材料：无 quote+locator 的断言被引擎拒绝；quote 与原文的一致性由 Agent 对照 extract 落盘文本核对。
* 不越过证据范围扩展结论：无法确定项进 uncertainty.json，status=partial 时 limits 写明。
* 冲突证据并列呈现+比较裁决；空白必须有检索记录依据。
* 全部中间产物落盘，第三方可按 inputs.json（含 sha256）与 *_check.json 复跑。

## 异常处理
| 情况 | 处置 |
|---|---|
| 不支持/无法解析的输入 | probe+extract 如实记录 kind 与失败原因，changes.json 留痕，不静默跳过 |
| 材料缺关键字段（无年份/无摘要） | 缺什么标什么，进 uncertainty.json；不进统计也不删除 |
| 检索为空 | 如实记 returned:0；空白走 searched_no_evidence，不得编文献 |
| 证据互相矛盾 | matrix conflicts + adjudication；判定不了就 genuinely_unresolved+依据 |
| 任务中断 | 中间产物已落盘，从最近一个 *_check.json 续跑 |
| 权限不足/文件不可读 | 记入 uncertainty.json，status 降 partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：8 个引擎模块 demo（含无回链断言、搪塞裁决、伪造引用、静默遗漏等负例）+ 一次端到端（合成 case → probe → extract → 模块校验 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Deep%20Research%20%26%20Literature%20Review/challenge-27d794ce/v2
