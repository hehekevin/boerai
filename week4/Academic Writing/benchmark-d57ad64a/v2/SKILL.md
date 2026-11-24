---
name: writing-benchmark-scorecard
description: "Build and run an academic-writing evaluation loop: task-set sheets, reference answers with acceptable variants, observable scoring anchors (0/1/2), double-rating with agreement records, and a per-case report. Use when: a case asks to design writing benchmark items, score drafts against anchors, reconcile rater disagreement, or produce a reproducible evaluation report. NOT for: writing the examined drafts themselves as a substitute for scoring, inventing scores without evidence, or changing scores instead of revising anchors."
---

# 学术写作评测闭环：题面—答案—锚点—双评—报告，全部可复算

面向"学术写作 Benchmark 与评测工具"任务。本技能把评测变成确定性簿记：Agent 负责语义评分判断，引擎负责锚点规范性、评分合法性、双评一致性与报告复算——每条评分落盘 JSON，第三方可按记录重算出同一批分数。

## 何时使用
* 用例要求设计写作评测题（输入材料、指令、必需要点、可接受变体），或对稿件按评分锚点打分并出报告。
* 判定标准：两名评分员不商量能判出同一结果；锚点是可观察现象；分数能从记录复算。

**不适用**：用预制答案冒充实际评分；无证据给分；以修改分数方式消除分歧。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：题面、待评稿件、既有锚点或评分表等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 锚点库、评分记录、一致性记录与评测报告（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/eval_report.md --artifact data=$WORK/agree.json \
    --artifact provenance=$WORK/ratings_check.json
```

**第 1 步 建题面。** 从材料整理 `tasks.json`：每题含输入材料定位、任务指令、字数/引用要求、必需要点清单（可直接作为 `awkit.coverage` 的 brief）、可接受变体与不可接受错误两类标注、完成判定。

**第 2 步 参考答案。** 每题至少一份参考答案，逐句走 `claims validate`（事实句必须挂来源引文、数字必须字面一致或登记 computed），证明答案本身"站得住"；变体差异标明属于风格选择还是实质错误。

**第 3 步 写锚点。** `anchors.json`：`{id, criterion, observable, levels:{0,1,2}}`——observable 必须是可观察现象（"随机抽 5 个数字逐一对照来源"），不是"写得好"。
`python "$SKILL/run.py" scorecard lint-anchors $WORK/anchors.json $WORK/anchors_lint.json` 拒绝空泛锚点与缺档。

**第 4 步 双评。** 两名评分员（或同一 Agent 两轮独立盲评）各自产出 `ratings.json`：`{case_id, anchor_id, rater, score:0|1|2, rationale≥10字, evidence}`。
`python "$SKILL/run.py" scorecard score $WORK/anchors.json $WORK/ratings.json $WORK/ratings_check.json`。

**第 5 步 一致性与裁定。** `python "$SKILL/run.py" scorecard agree $WORK/anchors.json $WORK/ratings.json $WORK/agree.json $WORK/eval_report.md [--adjudications $WORK/adjudications.json]`：分歧 >1 档必须裁定；裁定只能**修订锚点**（anchor_revision），不得直接改分。

**第 6 步 复现包。** 固定输入哈希（probe 已记录 sha256）、锚点版本、原始输出与评分记录一并归档，同一批题重跑应得到可解释的一致结论。

## 本题判据对齐（题面"五个问题"）
1. **题能判定** → tasks.json 强制每题带必需要点清单与完成判定；缺项 lint 不过。
2. **答案站得住** → 参考答案先过 `claims validate`；变体标注区分风格/实质错误。
3. **锚点打得齐** → `scorecard lint-anchors` 拒绝非可观察锚点；agree 输出分歧集中在哪几条判据。
4. **跑得可复现** → probe 冻结输入 sha256 + 锚点版本 + ratings 全量留痕，分数可复算。
5. **报告说得清** → `build_report` 逐题给分数、理由、失败类型、改进建议，而非只有总分。

## 交付物
* `tasks.json`、`anchors.json`（lint 通过）、`ratings.json`（双评全量）、`agree.json`、`eval_report.md`（逐题得分+证据+失败类型+改进建议）、参考答案及其 `claims_report.json`。

## 证据与审计规则
* 每条评分必须带 rationale（≥10 字）与 evidence 引用；引擎拒收缺项评分。
* 分歧处理只许修订锚点并记录 anchor_revision，禁止直接改分。
* 分子分母、总分、一致率全部由引擎从 ratings 复算，报告不手写数字。
* 材料不足或稿件缺失时该题记 not_produced 并写原因，status 降级 partial。

## 异常处理
| 情况 | 处置 |
|---|---|
| 锚点空泛（"写得好"） | lint-anchors 拒收，要求改写为可观察现象 |
| 双评分歧超过一档 | adjudication_required；裁定须 final+rationale，并反推锚点缺陷 |
| 只有一名评分员 | 该对进 pending，报告标注 single_rater_only |
| 待评稿件缺失/损坏 | 该题 not_produced + 原因，不虚构评分 |
| 参考答案自身无来源 | 先补 bindings 或标注【材料不足】，否则不进入评分 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（含 scorecard 的锚点拒收、非法评分拒收、分歧裁定）+ 一次端到端（合成 case → probe → extract → claims/deck 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/benchmark-d57ad64a/v2
