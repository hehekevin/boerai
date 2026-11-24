---
name: source-to-sqlite-migration
description: "Collect records from multiple provided sources (RIS/JSON/CSV/local publisher files), map fields with provenance, dedupe by explicit identity rules, migrate transactionally into the case's real initial SQLite target with idempotent upserts, then run completeness verification and diff reports. Use when: a case asks for a closed collect→map→dedupe→migrate→verify loop against organizer-local sources and a SQLite target. NOT for: live external services, simulated targets, or migration without a diff report."
---

# 科研资料收集与迁移：完成操作，也保留过程轨迹

面向"跨来源采集→字段映射→去重→迁移→完整性校验闭环"任务。来源为案例提供的真实已发布来源文件（含归属信息，组织方本地服务，非实时外部服务），目标端为案例自带的**真实初始 SQLite**。引擎保证：一个事务一个批次，失败整体回滚不留半写状态；upsert 键为身份键（DOI>规范标题），重跑报 unchanged 而不是假装新增；迁移后 `verify` 逐条比对目标端与预期集合并输出精确差异报告。

## 何时使用
* 用例给出若干来源快照文件与初始 SQLite 目标，要求收拢成可用资料集并校验。
* 判定标准（评分原文）：真正把采集、字段映射、去重、迁移、完整性校验的链路跑通形成闭环；字段取值与来源一致、映射对得上、去重不漏判不误合并、目标端记录与源端语义一致；输入快照、字段映射表、去重清单、写入日志与差异报告能支撑他人独立复跑。

**不适用**：实时外部服务/需要登录的来源、模拟目标端、无差异报告的"迁完即止"。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：来源文件、初始 SQLite、字段映射要求等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" normalize <来源records.json> $WORK/norm_<src>.json
python "$SKILL/run.py" identity  $WORK/all_records.json $WORK/dedupe.json
python "$SKILL/run.py" sqlite_ops migrate $WORK/final_records.json $WORK/target.sqlite $WORK/migrate_log.json --batch b1
python "$SKILL/run.py" sqlite_ops verify  $WORK/target.sqlite $WORK/final_records.json
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/migration_report.md --artifact data=$WORK/migrate_log.json
```

**第 1 步 采集与冻结。** probe 冻结输入（路径+sha256）；逐来源把原始记录整理为 `{source, records:[...]}`，归属信息（出处文件、快照哈希）随记录保留。

**第 2 步 字段映射。** `normalize`：默认映射表覆盖 RIS/Zotero/CSV 常见异名；题目另有约定时写 `--map map.json`；不可映射字段进 `extra` 并在报告单列，缺失字段显式标注。

**第 3 步 去重。** `identity`：规则优先级 doi_exact > title_exact > author_year_title_fuzzy(≥0.90)；每次合并记录规则与分数，字段冲突进 conflicts，DOI 冲突的疑似对**不合并**并列 suspects——区分精确重复、疑似重复与同名不同文献。

**第 4 步 事务化迁移。** `sqlite_ops migrate`：先复制初始目标到 $WORK 再操作（原始输入只读）；一个事务一个批次；per-record 状态 inserted/updated/unchanged/conflict_kept；任何 sqlite 错误整体回滚并返回 `rolled_back:true`。

**第 5 步 完整性校验。** `sqlite_ops verify`：比对目标端与预期集合，输出 missing/mismatched 精确清单；`export_csv` 供下游交接；差异报告写明哪些差异属预期（如 policy=keep 的冲突保留）、哪些属缺陷。

## 本题判据对齐（评分原文）
1. **"链路跑通形成闭环"** → 五个阶段各有落盘产物：norm_*.json → dedupe.json → migrate_log.json → verify 输出 → migration_report.md。
2. **"字段与来源一致、去重不漏判不误合并"** → normalize 字段出处 `_provenance`、identity 合并规则/分数/suspects 三分清单。
3. **"快照、映射表、去重清单、写入日志与差异报告支撑独立复跑"** → 全部 JSON 落盘 + migration_log 表内审计（batch/ident/status），第三方可重放。

## 交付物
* `norm_<src>.json`、`dedupe.json`、`migrate_log.json`、`target.sqlite`（迁移后副本）、`export.csv`、`migration_report.md`、`result.json`

## 证据与审计规则
* 原始来源文件与初始 SQLite 只读；一切写入发生在 $WORK 副本，溯源链完整。
* 迁移日志含 pre/post 行数、delta、每记录状态；重跑同一批次必须 unchanged，否则说明原因。
* 冲突（同键不同内容）默认 policy=update 时留 replaces 记录，policy=keep 时保留旧值并列 conflicts——无静默覆盖。
* 源端有而目标端无（或反之）由 verify 的 missing/mismatched 精确列出，不用总数搪塞。

## 异常处理
| 情况 | 处置 |
|---|---|
| 来源文件缺失/不可读 | probe/skips 记录，status=partial 并说明缺哪个来源 |
| 字段缺失/不可映射 | extra 保留原值 + 报告 unmappable_source_fields |
| DOI 冲突疑似重复 | 不合并，进 suspects_not_merged 交人工 |
| 迁移中途 sqlite 错误 | 事务回滚，`ok:false, rolled_back:true`，目标端回到批前状态 |
| 重复执行迁移 | 全部 unchanged、delta=0，日志如实记录 |
| 校验不一致 | missing/mismatched 精确清单 + uncertainty，status 降级 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo（sqlite demo 含幂等重跑与冲突保留断言）+ 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-71c94fb7/v2
