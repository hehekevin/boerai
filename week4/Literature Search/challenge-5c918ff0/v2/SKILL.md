---
name: multidb-merge-audit
description: "Merge multi-database search snapshots into one deduplicated record set with field-level source traceability and explicit coverage gaps. Use when: a case asks to merge results from multiple databases into one deduplicated, field-traceable record set. NOT for: bypassing service limits, single-database full-text reading, or moving data to unapproved services."
---

# 多数据库联合检索：找到文献，也保留筛选依据

面向"多库归并：字段可用、来源可溯、缺口明说"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出多个来源库的检索响应快照，要求归并为一份不重复、字段可用、来源可溯的记录集。
* 判定标准：归并可靠、字段可追溯到来源库与原始响应、未覆盖的库与字段被明确说出。

**不适用**：绕过服务限制、单库全文阅读、向未批准服务汇总数据。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、参考集、查询日志、引文图、PDF/表格等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/<主交付物> --artifact data=$WORK/<数据文件>
```

**第 1 步 字段归一。** 各库快照逐字段映射到统一记录；映射表写 `field_map.json`，归一损失逐库记录。

**第 2 步 身份合并。** `python -m lskit.identity all_records.json $WORK/merged.json`：doi_exact/title_exact/author_year_fuzzy 三级规则，合并日志与字段冲突全保留。

**第 3 步 来源回溯。** 每条记录带 `_sources`；交付物中任何字段能指回来源库与原始快照。

**第 4 步 覆盖比较。** 逐库统计独有/被合并/缺字段；明确写出"哪些库未覆盖、哪些字段缺失"。

**第 5 步 口径说明。** 大小写/全半角等已知误差写入 limits；报告给合并前后计数。

## 本题判据对齐（题面原文的"三件事"）
1. **归并不重复且字段可用** → identity 三级规则 + 字段完整性统计。
2. **字段可追溯到来源库与原始响应** → _sources + field_map.json + 快照 sha256。
3. **未覆盖库/字段明确说出** → 覆盖比较表 + limits。

## 交付物
* `merged.json`（含 _sources）、`field_map.json`、`merge_audit.json`、`coverage_by_db.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 同 DOI 但元数据冲突 | 保留一版、冲突逐字段记录，不取平均 |
| 作者名大小写/语序差异 | identity 归一后比对；已知误计写入 limits |
| 某库响应缺页/截断 | 该库完整性标 partial，计数单列 |
| 无 DOI 且标题近似 | author_year 误判风险进 review 队列 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-5c918ff0/v2
