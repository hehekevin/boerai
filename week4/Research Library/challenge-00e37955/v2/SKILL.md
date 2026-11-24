---
name: research-library-steward
description: "Steward a real research file library: content-hash inventory, metadata lists with provenance, content-based duplicate/version handling, tag/collection audit, and recovery/index operations — with skip/conflict records instead of silent success. Use when: a case asks to organize an actual document library (files, aliases, administrative version notes, metadata, searches) and deliver verifiable manifests and operation records. NOT for: live publisher accounts, private Zotero clouds, or inventing gold answers."
---

# 资料管理领域总课题：整理文件，也保留版本关系

面向"对真实科研文件库做盘点、组织、元数据、版本关系与检索交接"任务。本技能以内容哈希而非文件名为判据：先盘点真实文件树（含跳过原因），再按题目规则组织目录与元数据清单，重建版本/别名关系，标签与集合操作全程审计且幂等，检索问答落到具体文件与定位。跳过、冲突、无权限、重复全部留痕——**不把未完成写成完成**。

## 何时使用
* 用例给出真实文件库（文件、别名、管理性版本说明、元数据、检索问题）与工单，要求整理并交付清单与操作记录。
* 判定标准：目录/清单与输入文件和题目规则一一对应；哈希、来源、权限、变更日志可复跑核对；跳过与冲突如实记录。

**不适用**：需要原始 PDF 全文语义的判定、私有 Zotero 账户操作、编造语义金标准。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文件库、元数据表、版本说明、检索问题等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" filelib inventory <材料根目录> $WORK/inventory.json
# —— 本题处理步骤（见下） ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/steward_report.md --artifact data=$WORK/archive_manifest.json
```

**第 1 步 盘点。** `filelib inventory`：逐文件 sha256、mtime、类型；不可读/超限文件进 skips 并写明原因，绝不静默跳过。

**第 2 步 去重与版本。** `rlkit.versions`（输入 inventory 的 files 数组）：同哈希=副本/别名；同词干不同哈希=版本序列，按 mtime 建 supersede 链；同名不同内容=冲突，两者都保留不覆盖；工单里的管理性版本说明与内容证据不符时标记 `admin_note_unverified` 而非盲信。

**第 3 步 元数据与组织。** `rlkit.normalize` 统一异构元数据（字段映射 + 字段出处 + 不可映射字段清单）；`filelib plan` 按 `{project}/{year}/{kind}` 模板生成落库计划，目标名冲突加哈希后缀改名，**永不覆盖**；`archive_manifest` 产出与输入一一对应的交接清单。

**第 4 步 标签与变更。** 批量标签/集合走 `rlkit.tags`（ops 文件驱动）：每个操作有 before/after、幂等（重复执行为 already）、可 `rollback` 精确恢复。

**第 5 步 检索/问答与汇总。** 有检索问题时用 `rlkit.kb` 建块索引并检索，回答引用必须经 `kb validate` 核验；汇总写 `steward_report.md` + `summary.json`。

## 本题判据对齐（交付要求原文）
1. **"与输入文件和题目规则一一对应"** → inventory 每输入文件一条记录，archive_manifest 逐项 source→destination + sha256，skips 单列。
2. **"他人可复跑并核对"** → 哈希、来源、变更日志全部落盘 JSON；versions/tags 的规则与分数可手工复算。
3. **"不把未完成写成完成"** → 不可读进 skips、冲突进 conflicts、无法判断进 uncertainty，status 相应 partial。

## 交付物
* `inventory.json`、`versions.json`、`landing_plan.json`、`archive_manifest.json`
* `tags_audit.json`（如有标签/集合操作）、`steward_report.md`、`result.json`

## 证据与审计规则
* 重复与版本一律按内容哈希判断；文件名仅作线索，绝不作为唯一判据。
* 每条元数据字段带来源出处（`_provenance`）；无法从材料获得的字段留空并写 uncertainty，不猜。
* 所有变更操作（改名计划、标签、集合）只在账本/清单中登记，原始输入目录只读。
* 管理性说明（工单版本注记）需与内容证据互相印证，不符即冲突标记。

## 异常处理
| 情况 | 处置 |
|---|---|
| 文件不可读/超大 | skips 记录原因与动作（listed_without_hash），不进哈希判重 |
| 同名不同内容 | name_collision：两者保留，落库时加哈希后缀，禁止覆盖 |
| 版本说明与内容证据矛盾 | admin_note_unverified 冲突标记，交人工核对 |
| 元数据字段缺失 | 留空 + `_provenance` 无该字段 + uncertainty 汇总 |
| 重复执行标签操作 | status=already，不产生二次变更 |
| 目录为空 | 如实报告 n_files=0，status=partial 并说明 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo + 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-00e37955/v2
