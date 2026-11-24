---
name: zotero-library-ops
description: "Operate a real Zotero-class library store end to end: import records from RIS/JSON/local publisher files, repair metadata from frozen DOI snapshots under a never-overwrite-correct-fields policy, dedupe with auditable identity rules, apply tags/collections/notes with an idempotent audit log, snapshot SQLite state before/after, and honor explicit read-only policies. Use when: a case provides a preinitialized source-backed library and asks for import/metadata/tags/notes with a replayable trail. NOT for: live Zotero cloud accounts, shared-library writes beyond the granted scope, image-only patents without a text layer, or AI answers not backed by library items."
---

# Zotero AI 插件：完成操作，也保留过程轨迹

面向"在真实文献库上走完入库—补字段—打标签/写笔记—库内辅助"任务。库为案例预初始化的真实来源支撑库（SQLite 状态可快照），元数据来源为冻结 DOI 元数据/RIS/本地出版商文件（离线，不触达实时解析）。引擎分工：`identity` 幂等去重（规则+冲突审计）、`metarepair` 按优先级补字段（**默认 fill_missing：已有正确字段绝不被覆盖**，冲突留痕）、`tags` 标签/集合/笔记操作幂等+可回退、`ledger` 前后 SQLite/文件状态快照与恢复、`kb` 让库内回答只依据库内条目并可指回来源。组织方显式只读策略（如 C03 readonly）被当作硬约束：任何越界写操作拒绝并留痕。

## 何时使用
* 用例给出预初始化文献库、来源记录（每案真实来源）与任务单，要求库内条目级操作与可复跑轨迹。
* 判定标准（题面原文的"三件事"）：任务是否在真实文献库上从头走到尾；库里最终留下的条目和字段是否与原文和题目要求对得上；整个操作过程能否被别人按记录重跑一遍。

**不适用**：真实云同步/共享账户写权限、无文本层的图像型专利（组织方列为 out-of-scope 控制项）、不依据库内条目的"AI 成功"。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：库文件/SQLite、RIS、冻结元数据快照、出版商文件、策略说明等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
cp <库.sqlite> $WORK/library.sqlite            # 原始库只读，一切写入在副本
python "$SKILL/run.py" normalize <来源records.json> $WORK/norm.json
python "$SKILL/run.py" metarepair $WORK/norm.json $WORK/snapshots.json $WORK/repaired.json
python "$SKILL/run.py" identity   $WORK/repaired.json $WORK/dedupe.json
python "$SKILL/run.py" sqlite_ops migrate $WORK/dedupe.json $WORK/library.sqlite $WORK/mig.json --batch b1
python "$SKILL/run.py" tags $WORK/lib_state.json $WORK/tag_ops.json $WORK/tags_audit.json
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/zotero_ops_report.md --artifact data=$WORK/ledger/.op_ledger.json
```

**第 1 步 边界与快照。** probe 冻结输入哈希；读任务单中的权限策略（如 C03 readonly：该集合只读）——越界写操作一律 refused 并写入审计；`ledger` 对库文件做操作前快照。

**第 2 步 入库。** 来源记录（RIS/JSON/出版商文件）经 normalize 映射为规范条目（作者 Family, Given、DOI 归一、字段出处）；附件/条目对应关系在记录里显式列出，防止附件与条目脱节。

**第 3 步 元数据补全。** `metarepair`：按 DOI>标题匹配冻结快照；默认 fill_missing——只补空字段；与快照冲突时保留库内值并列 conflicts（题目要求 prefer_snap 时逐条记录 kept/discarded）；无快照匹配=unrepaired 如实列出，**不编字段**。

**第 4 步 去重与写入。** `identity` 合并（doi_exact > title_exact > 作者年模糊），合并规则/分数/字段冲突入审计；`sqlite_ops migrate` 事务写入，重跑 unchanged；失败整体回滚，`ledger.rollback` 可恢复库文件到操作前状态。

**第 5 步 标签/笔记与库内辅助。** 标签/集合走 `tags`（幂等、审计、可回退；写向未知条目=refused，防止标签落到相邻条目）；笔记内容必须带来源定位；库内问答走 `kb`（引用经机械核验，超出库范围明确说"库内无依据"）。

## 本题判据对齐（题面原文的"三件事"）
1. **"在真实文献库上从头走到尾"** → 五阶段各有落盘产物（norm→repaired→dedupe→mig→tags_audit），账本含库文件前后哈希。
2. **"库里最终条目和字段与原文和题目要求对得上"** → metarepair 每字段 from_snapshot 出处、identity 冲突清单、sqlite verify 精确差异。
3. **"能被别人按记录重跑一遍"** → 全部 JSON/SQLite 落盘 + migration_log 表内审计 + 幂等重跑断言，第三方可重放。

## 交付物
* `norm.json`、`repaired.json`、`dedupe.json`、`mig.json`、`tags_audit.json`、`library.sqlite`（操作后副本）、`ledger/.op_ledger.json`、`zotero_ops_report.md`、`result.json`

## 证据与审计规则
* 原始库只读；所有写入在 $WORK 副本，前后状态哈希入账，恢复有据。
* 补字段默认不覆盖已有值；任何覆盖必须 prefer_snap 且逐条留 kept/discarded。
* 重复条目零新增：重跑 migrate 必须 unchanged；出现成片重复即审计失守，回滚查因。
* 库内 AI 辅助只依据库内条目，引用必须 `kb validate` 通过；超范围问题明确回答"库内无依据"。
* 图像型/无文本层附件不当作已读内容；只读策略集合写操作 refused 并说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| DOI 在冻结快照中查不到 | unrepaired + reason=no_matching_snapshot，字段留空不编 |
| PDF 无文本层/图像型附件 | 声明 out-of-scope，不作内容性结论 |
| 只读集合（如 C03）写请求 | refused + 策略出处，审计留痕 |
| 迁移中途失败 | 事务回滚 + ledger.rollback 恢复库文件，半成品不入账 |
| 标签写向不存在条目 | refused(unknown_item)，防止错落到相邻条目 |
| 条目被删/键冲突 | sqlite conflicts 清单 + uncertainty，交人工 |
| 重复执行 | unchanged/already 如实入账，不冒充新变更 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo（metarepair demo 含"已有字段不被覆盖"断言、tags demo 含回滚恢复初态断言）+ 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/zotero-ai-a207356c/v2
