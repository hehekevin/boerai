---
name: source-fidelity-writing
description: "General academic-writing pipeline with source fidelity: bind every factual sentence to a source quote, verify every number literally matches the sources or a registered computation, check required-point coverage, citation integrity, bilingual terms and format compliance. Use when: a case asks to write/rewrite/proofread/structure academic text from fixed materials while keeping facts and sources consistent. NOT for: writing from memory, inventing citations, or silently filling material gaps."
---

# 学术写作总课题：完成产物，也保留来源

面向学术写作领域通用任务（起草、改写、校对、格式、引用、双语、结构化写作）。统一打法：确定性簿记在引擎，语义判断在 Agent——每句事实挂来源引文，每个数字可回溯，材料不足走诚实标注，全套中间产物落盘可复算。

## 何时使用
* 用例给出事实底稿/材料 + 受众/文体/格式约束，要求完成生成、改写、校对或结构化动作。
* 判定标准：事实与来源一致；不新增材料外事实；缺口与冲突明确标注；结果可继续编辑。

**不适用**：脱离材料凭记忆写作；编造引用；把"材料不足"硬写成肯定句。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（事实底稿、数据表、文献、模板、术语表等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 目标产物与事实-来源映射（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 通用六步（按题面裁剪，见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact document=$WORK/draft.md --artifact provenance=$WORK/claims_report.json \
    --artifact data=$WORK/coverage.json --artifact report=$WORK/quality_gate.json
```

**第 1 步 读约束。** 从题面整理：体裁、受众、必需要点（→ `brief.json`）、格式约束（→ `spec.json`）、术语表（→ `terms.json`）。

**第 2 步 冻结来源。** 材料整理成 `sources.json`（id + 全文 + loc 定位）；probe 已记录文件 sha256。

**第 3 步 写作 + 绑定。** 写作时同步填 `bindings.json`；推导数字登记 `computed.json`（公式 + 依据句）。
`python "$SKILL/run.py" claims validate $WORK/draft.md $WORK/sources.json $WORK/bindings.json $WORK/computed.json $WORK/claims_report.json --strict`：无绑定事实句、编造引文、来源外数字全部拒收；写不了就用【材料不足】标注句。

**第 4 步 覆盖与引用。** `coverage check` 核必需要点/章节；`citecheck check` 核引用键解析与条目字段；双语任务加 `bilingual check`。

**第 5 步 格式。** `formatcheck check` 核标题层级、分节字数、参考文献字段顺序。

**第 6 步 质量门。** 汇总各校验结果成 `quality_gate.json`：全绿才 success；任一红 → 修复或 status=partial + uncertainty 说明。

## 本题判据对齐（题面"输出要求"三条）
1. **目标产物满足体裁/受众/格式** → spec/brief 结构化约束 + formatcheck/coverage 机械核对。
2. **事实与来源映射可逐条回溯** → claims 句级绑定 + 数字字面一致性 + computed 公式登记，不新增材料外事实。
3. **版本与边界明确** → changes/uncertainty 落盘；未确认部分【材料不足】标注；结果保持可编辑文本。

## 交付物
* `draft.md`（目标产物）、`claims_report.json`、`coverage.json`、`citecheck.json`、`format.json`、`quality_gate.json`；按题型附 `terms.json`/`bilingual.json`/`changes.json`。

## 证据与审计规则
* 事实句无绑定、引文非来源子串、数字查无出处 → 一律拒收，不接受"大概是这么说的"。
* 诚实路径：`awkit.claims.insufficient()` 生成标注句；partial 必须在 limits 说明缺口。
* 所有校验报告带 violations 明细，第三方可逐条复核。
* probe 冻结输入哈希，保证"同一输入重跑同一结论"。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料不足支撑不了要求 | 【材料不足】标注 + uncertainty + partial |
| 材料之间冲突 | 两处来源都列出，取保守表述并标 conflict |
| 引用键解析失败 | citecheck 拒收；修正键或补条目后复检 |
| 格式要求与内容冲突（如字数装不下要点） | 列冲突项，优先保要点覆盖并记录取舍 |
| 输入文件损坏 | extract 记录失败，status=failed 说明 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo + 一次端到端（合成 case → probe → extract → claims/deck → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-a2c6f23b/v2
