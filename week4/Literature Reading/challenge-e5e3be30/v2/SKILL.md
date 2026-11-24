---
name: claim-evidence-verification
description: "Verify scientific claims against provided literature: split complex claims into independently checkable subclaims (fact/comparison/causal/scope), locate minimal sufficient evidence per subclaim, and assign four-level verdicts (support/partial/contradict/not_found) with verbatim quotes and rationales; conflicts registered with both sides quoted. Use when: a case asks to check whether statements are supported by given papers, verify citations, or build evidence cards. NOT for: judging truth beyond the provided corpus, topic-relevance-as-support, or citation formatting."
---

# 文献证据溯源与事实核验：论断拆得开，证据找得到，判定说得清

聚焦方向：**论断—段落匹配 + 四级支持度判定**。Agent 负责语义拆解与判定理由，引擎负责拆分候选生成、证据逐字核验、判定聚合与冲突登记的确定性簿记——"主题相关 ≠ 支持"由流程强制：没有逐字证据就不允许判 support。

## 何时使用
* 用例给出论文与一组待核验科研论断（或引用—结论对），要求判定支持程度并给出出处。
* 判定标准：每条子判断有最小充分证据、四级判定与原文表述相符、冲突与限制并列保留。

**不适用**：超出给定材料的真伪判定、只凭主题相关判支持、引用格式排版。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（论文文本、论断清单、引用对照表）。

## 输出（写入 /app/output）
`result.json` + `claims.json`（论断拆解+判定）+ `verify_report.json`（引擎校验，含聚合状态）+ `conflicts.json`（冲突登记，双方原话）+ `report.md`（核验报告/证据卡片）。

四级判定定义（写入交付物）：`support`=证据逐字支持全部要素；`partial`=只覆盖部分要素或条件范围更窄；`contradict`=方向相反或数值矛盾；`not_found`=材料中无可核验证据。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 论断拆解。** 逐条论断先机械拆分，再语义确认：
```bash
python -m lrkit.locate split "$WORK/blocks.json" "$WORK/claim_01.txt"
```
引擎给出子判断候选（fact/comparison/causal/scope）；Agent 合并/删除并确认类型，保证既不遗漏也不重复核验，落盘 `claims_split.json`。

**第 2 步 证据定位。** 每条子判断跑 `python -m lrkit.locate search ...` 找候选段落，Agent 回原文确认**最小充分证据**（精确到段落/句子，不接受只给篇名）。

**第 3 步 逐条判定。** 写 `claims.json`：每条子判断给 verdict、rationale（判定理由必填）、evidence（loc+逐字 quote）。主题相关但要素不全 → partial，不得升 support；范围论断找到一个反例 → contradict。

**第 4 步 引用核验。** 若任务是核对"引用是否真的包含对应结论"：按引用编号回被引段落，摘要与正文表述不一致时在 rationale 写明两处差异。

**第 5 步 冲突登记。** 来源冲突写入 `conflicts.json`：
```bash
python -m lrkit.claims conflicts "$WORK/conflict_entries.json" "$WORK/conflicts.json"
```
冲突双方原话并列保留，说明取舍；禁止只报告支持性证据。

**第 6 步 引擎核验与交付。**
```bash
python -m lrkit.claims validate "$WORK/claims.json" "$WORK/blocks.json" "$WORK/verify_report.json"
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/report.md" --artifact data="$WORK/verify_report.json"
```
父论断状态由引擎从子判断聚合（全 support→supported；有 contradict→contradicted；有 partial/not_found→partially_verified/unverifiable），手填状态与聚合不符即失败。

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **拆得开** → `locate.split_claims` 给出不遗漏不重复的候选，类型标注供 Agent 确认；claims 无 subclaims 不得进入校验。
2. **找得到** → 每条 verdict≠not_found 的子判断必须有 evidence，且 quote 逐字存在于所标段落（`verify_quote` 强制）。
3. **判得准** → 四级判定定义随交付物落盘；`support` 必须有逐字证据——"主题相关当支持"在引擎层无法通过；rationale 必填使判定理由可复核。
4. **说得清** → `conflicts.json` 并列冲突双方原话；样本/范围限制进 rationale 与 uncertainty；`not_found` 不带证据（引擎拒绝 not_found+evidence 的组合）。

## 交付物
* `claims.json`（论断→子判断→证据→判定→理由完整链）、`verify_report.json`、`conflicts.json`、`report.md`（证据卡片或核验报告）。

## 证据与审计规则
* "论断→证据片段→原文定位→支持度判定→判定理由"链条缺一不可，引擎逐环校验。
* 证据取最小充分片段（≤240 字符逐字引文），跨页证据分段引用并分别核验。
* 转引（A 引 B 的结论）在 rationale 注明转引关系，不当一手证据。
* 判 not_found 前必须跑过定位检索并在 rationale 写明查过哪些关键词。
* 材料没有的内容写入 uncertainty，status 降 partial。

## 异常处理
| 情况 | 处置 |
|---|---|
| 论断含多个子判断只找到部分证据 | 该子判断 not_found，父论断聚合为 partially_verified |
| 证据互相冲突 | conflicts.json 并列双方原话 + 取舍说明，不掩盖 |
| 摘要与正文表述不一致 | 两处都引用，rationale 说明差异，以正文为准并注明 |
| PDF 无文本层/原文无法访问 | 该论断 input 侧记 not_found + 原因，status 降 partial |
| 定位失败（关键词无命中） | 换同义词重跑 search 并在 rationale 记录检索轨迹 |
| 只找到主题相关段落 | 判 partial 或 not_found，禁止升 support |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：claims demo 演示"范围论断被反例推翻→contradicted"与"伪引文被抓出"；端到端合成案例跑通全流程。示例论断与论文均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-e5e3be30/v2
