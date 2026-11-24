---
name: academic-audit-core
description: "General academic-review engine: deterministic pre-scan (numeric claims, cross-section consistency, declarations), typed findings ledger with anti-fabrication validation (quote+locator+justification or rejected), six-facet checklist coverage, and an auditable report. Use when: a case asks for quality/citation/fact/method/statistics/logic/norms review of a fixed paper or research material with per-item evidence and severity. NOT for: forced defect verdicts, reviewing without source text, or any task where materials are unavailable offline."
---

# 学术审查领域总课题：论文质量审查——发现问题，也给出证据

面向"对固定论文或科研材料完成质量、引用、事实、方法、统计、逻辑或规范审查，逐条给出证据和严重度"的总课题。本技能是六类审查的通用内核：引擎做确定性预扫描与台账验证，Agent 做语义判断；组织方特别要求 **no forced or planted defect verdicts**——引擎原生支持"零发现"诚实结局，任何没有原文摘录+定位+依据的发现都会被验证器驳回。

## 何时使用
* 用例给出论文/科研材料与具体审查面（facets），要求按检查项逐条审查、每条给原文位置与判断依据、区分错误/证据不足/规范问题/建议、无法确认的标待复核。
* 判定标准：问题真实成立、定位可核对、严重度相称、不凭空补结论。

**不适用**：润色代写、查重、无源文本的臆断审查、需要联网核验来源的任务（本技能离线，只用案例提供文件）。

## 输入
`/input/case.json`（含本题具体 facets 与 output_contract）、`/input/task.md`、`/input/**`（全文材料、引用片段、数据表等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <材料文本> [--checklist 自定义清单.json]
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 读题定面。** 从 case.json/task.md 读出本题具体审查 facets 与 output_contract（probe 的 text_fields 与 output_contract 字段）； facets 与默认 12 项清单不同时，按需裁剪 checklist（`arkit.checklist`），裁剪理由落盘。

**第 2 步 预扫描（只产观察）。** audit 命令产出：stats（数字主张及 n/CI/p 伴随情况观察）、consistency（跨节数字冲突、摘要-正文缺口、章节结构）、norms（伦理/利益冲突/数据可用性等声明缺失观察）。观察≠结论。

**第 3 步 Agent 逐面审查。** 对每条观察回到原文确认：是缺陷（入册，注明类型与严重度依据）、是作者有意安排/学科惯例（不入册，checklist 标 pass 并留 note）、还是材料不足以判断（标 needs_review）。引用类判断用 `arkit.crosscheck` 并列本文论断与被引片段。

**第 4 步 验证与报告。** `python -m arkit.findings validate $WORK/ledger.json <材料文本>` 驳回不可核验发现；checklist 逐项销项；`python -m arkit.report ...` 生成报告。零发现 → outcome=no_findings，与有发现一样合法交付。

## 本题判据对齐（题面任务要求原文）
1. **"按题目检查项逐条审查输入"** → checklist 按本题 facets 驱动，coverage 逐面计数，未查项显式列出。
2. **"为每个问题提供原文位置和判断依据"** → 台账强制 quote+locator+justification，验证器核对摘录真实存在。
3. **"区分事实错误、证据不足、规范问题和建议性意见"** → kind 四分类（error/insufficient_evidence/norm_issue/suggestion），报告按类计数。
4. **"对无法确认的条目标记待复核，不凭空补结论"** → status=needs_review 与 checklist 待复核/未检查项在报告中单独成节；材料缺口写 uncertainty。
5. **组织方特别要求"no forced or planted defect verdicts"** → 空台账是合法结局；伪造摘录在 selftest 中被验证器驳回并留痕。

## 交付物
* `report.md`/`report.json`（逐条问题+位置+严重度+建议；驳回记录；待复核与未检查项）、`ledger.json`、`checklist.json`、`prescan_full.json`。

## 证据与审计规则
* 每条发现 = 原文摘录 + 定位串 + 判断依据 + 严重度依据，四缺一直被驳回。
* 引擎只产观察；Agent 的每条结论可独立复核（全部中间产物 JSON 落盘）。
* 无法判断 ≠ 缺陷：进 needs_review 并写核对点；零发现如实报告。
* 不联网：只使用案例提供文件；材料外事实不补造。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料无法解析/扫描件 | 记录 uncertainty，审可读部分，status=partial |
| 题目要求的 facet 材料缺失 | 该面标 needs_review，limits 说明 |
| 引用原文不可得 | crosscheck 判 undeterminable，不臆断不支持 |
| 疑似但无法证伪的问题 | 入册 status=needs_review 而非 confirmed |
| 重复运行 | 输入 sha256 入 sources，结果可复算 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 模块 demo + 端到端（合成案例 → probe → extract → audit → 真发现入册/假发现驳回 → 报告 → result.json），含零发现干净结局。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-398dc732/v2
