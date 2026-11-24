---
name: auditable-file-organization
description: "Organize a messy literature file library into real directory moves with an auditable, idempotent and rollback-able operation plan: inventory with hashes, metadata-based naming with explicit 'unknown' fallback for missing fields, duplicate/version detection (preprint vs published vs supplement vs revision), conflict-safe planning that never overwrites different content. Use when: a case asks to classify, tag, rename, deduplicate and batch-organize real files and produce verifiable operation records. NOT for: single-paper close reading, full-text translation, literature discovery/search, or irreversible delete-based cleanup."
---

# 文献与资料自动分类：真整理、可回滚、重跑一致

聚焦方向：**去重与版本区分 + 幂等批量整理**。本技能不做"建议清单"——引擎产出可审阅的操作计划，apply 后真实落盘并写可回滚日志；同名不同内容 → conflict 绝不覆盖；重复运行幂等（已完成自动 skip）。Agent 负责语义分类与元数据核对，引擎负责盘点、命名、冲突检测与操作簿记。

## 何时使用
* 用例给出一个混杂文件库（论文 PDF、预印本、补充材料、扫描件、别名文件），要求归类、命名、去重、输出版本关系与操作记录。
* 判定标准：归属与标签可用原文/元数据核对；操作留可回滚记录；换批同类文件重跑结果一致。

**不适用**：单篇精读、全文翻译、写作润色、文献检索发现、直接删除式清理。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（文件库、别名/版本说明、元数据线索、管理任务工单）。

## 输出（写入 /app/output）
`result.json` + `inventory.json`（文件盘点+哈希+元数据）+ `plan.json`（操作计划）+ `ops_log.json`（执行与回滚日志）+ `versions.json`（重复/版本关系）+ `library_manifest.md`（整理后清单）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
```

**第 1 步 盘点。** probe 的文件清单（路径、大小、sha256、类型）落盘为 `inventory.json` 骨架；逐文件补元数据：标题、作者、年份、期刊、DOI——从文件内容/案例材料核实，**缺失字段标 unknown，绝不凭空补**。

**第 2 步 语义分类与版本判定。** Agent 按题面规则给每个文件定目录类别，落盘 `categories.json`（path→类别+归属依据）；版本信号（preprint/published/supplement/revision）由 `fileorg.guess_version` 给出候选，Agent 结合案例中的版本说明确认，落盘 `versions.json`。

**第 3 步 生成操作计划。**
```bash
python -m lrkit.fileorg plan "$WORK/inventory.json" "$WORK/library" "$WORK/categories.json" "$WORK/plan.json"
```
计划项：move（命名模板 {authors}-{year}-{title}，缺字段降级 unknown）/ skip（内容完全相同的重复下载）/ conflict（同名不同内容，**不覆盖**）。

**第 4 步 审阅后执行。**
```bash
python -m lrkit.fileorg apply "$WORK/plan.json" "$WORK/ops_log.json"
```
apply 采用复制而非移动：源文件永不丢失，回滚 = 按 ops_log 删除 dst。conflict 项由 Agent 人工裁决（改名区分版本或标记归档），裁决写入 ops_log。

**第 5 步 幂等复核与交付。** 重跑一次 apply 确认全部 already_done；输出整理后清单：
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/library_manifest.md" --artifact data="$WORK/ops_log.json"
```

## 本题判据对齐（题面"三件事" → 引擎机制）
1. **每份文件的归属和标签能否用原文与元数据核对** → inventory 记录哈希与元数据来源；categories.json 每项带归属依据；缺失字段显式 unknown（命名模板强制降级，禁止编造）。
2. **命名、去重、移动的操作是否留下可回滚的记录** → apply 复制式执行 + ops_log（含 undo 说明）；skip/conflict/move 决策规则落盘在 plan.json。
3. **换一批同类文件重跑是否得到一致结果** → 计划生成是纯函数（同 inventory+categories 必得同 plan）；apply 幂等，重跑全 already_done。
4. **版本区分** → guess_version 给 preprint/published/supplement/revision 候选并注明依据（文件名/venue/DOI），同名不同版本进 conflict 不覆盖。

## 交付物
* `inventory.json`、`categories.json`、`plan.json`、`ops_log.json`、`versions.json`、`library_manifest.md`（整理后目录清单+前后对照）。

## 证据与审计规则
* 任何文件不被删除；清理类诉求一律转化为 move 到归档目录。
* 同名同内容（哈希一致）→ skip 并注明"重复下载"；同名不同内容 → conflict，人工裁决。
* 元数据只从文件内容/案例材料核实，unknown 是合法值。
* 扫描件/加密 PDF/无权限文件：inventory 如实标注 kind 与 note，不跳过不隐瞒。
* 前后对照：library_manifest.md 列出原路径→新路径逐条映射。

## 异常处理
| 情况 | 处置 |
|---|---|
| 同名不同版本/不同来源 | conflict 不覆盖，人工裁决后改名区分 |
| 元数据缺失（作者/年份/DOI） | 命名降级 unknown + 缺失字段清单，不编造 |
| 损坏文件/加密 PDF | inventory 标注，计划跳过移动并说明 |
| 扫描件无文本层 | 元数据只能来自案例材料，不足即 unknown |
| 权限不足 | 记录到 ops_log problems，status 降 partial |
| 重跑/断点续跑 | apply 幂等：已完成 already_done，失败项可单独重试 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：fileorg demo 用合成文件库演示计划（move/skip/conflict）、apply 幂等与 unknown 降级。示例文件名与元数据均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-666fefb0/v2
