---
name: sci-automation-steward
description: "Orchestrate a cross-tool scientific workflow over organizer-local services: collect from provided published sources, normalize and dedupe records, migrate transactionally into the case's real initial SQLite, export Datasette-ready CSV, and keep an operation ledger with snapshots, idempotence assertions and rollback. Use when: a case spans browser/library/filesystem/software boundaries and demands a replayable trail with terminal-state checks. NOT for: live external services, Bohrium scientific space calls, or automation without logs."
---

# 科研软件插件与自动化领域总课题：完成操作，也保留过程轨迹

面向"跨浏览器、文献库、文件系统与科研软件的受控编排"任务（本课题为领域总课题，本技能选定"多来源采集 → SQLite 事务化迁移 → Datasette 交接"这条明确链路做深）。来源为案例提供的真实已发布来源（组织方本地服务，含归属），目标端为案例自带的真实初始 SQLite；全程操作账本（状态快照、幂等断言、失败回滚、终态检查），Datasette 交接以 CSV 导出 + 行数/字段核验完成。

## 何时使用
* 用例跨越多个工具边界，要求采集、迁移、身份/别名处理、恢复与冲突操作，并保留可复核轨迹。
* 判定标准：核心科研任务真正完成并交付可用成果；结果可追溯到原始材料、工具调用和实际执行过程；重复运行与输入变化下仍稳定。

**不适用**：实时外部服务、Bohrium 科学空间调用、无日志黑盒自动化、需要真实云账户权限的操作。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：来源文件、初始 SQLite、服务说明等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" normalize <来源records.json> $WORK/norm.json
python "$SKILL/run.py" identity  $WORK/norm.json $WORK/dedupe.json
python "$SKILL/run.py" sqlite_ops migrate $WORK/final.json $WORK/target.sqlite $WORK/mig.json --batch b1
python "$SKILL/run.py" sqlite_ops export  $WORK/target.sqlite $WORK/datasette_export.csv
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/workflow_report.md --artifact data=$WORK/ledger/.op_ledger.json
```

**第 1 步 建账本。** `rlkit.ledger.OpLedger($WORK/ledger)`：每个工具调用作为一个 step，pre/post 状态哈希快照 + 终态检查（产物存在且非空）。

**第 2 步 采集与规范化。** 逐来源 normalize（字段映射+出处）；归属信息随记录保留；不可映射字段单列。

**第 3 步 身份与别名。** `identity` 去重合并（规则+分数+冲突审计）；别名/多键记录进 `_keys`，恢复与冲突操作有依据。

**第 4 步 事务迁移 + 交接。** `sqlite_ops migrate`（幂等 upsert、失败整体回滚）→ `verify`（精确差异）→ `export_csv` 产出 Datasette 可用 CSV（列名、行数、字节数入账）。

**第 5 步 幂等与恢复。** 关键步骤 `assert_idempotent`；失败步骤 `rollback(seq)` 回状态后重跑；handoff（人工接管）时导出当前状态、已得证据与待判问题。

## 本题判据对齐（交付要求原文）
1. **"目标状态和字段正确"** → migrate 的 pre/post 行数 + verify 的 missing/mismatched 精确清单，不用总数搪塞。
2. **"他人可复核每一步"** → 账本逐步留命令、状态 diff、终态检查；迁移日志表内审计（batch/ident/status）。
3. **"失败可发现、可解释、可接管"** → failed 步骤带错误与 traceback 截取，rollback 记录编号，handoff packet 落盘。

## 交付物
* `norm.json`、`dedupe.json`、`mig.json`、`datasette_export.csv`、`ledger/.op_ledger.json`、`workflow_report.md`、`result.json`

## 证据与审计规则
* 只操作组织方本地/案例提供的来源与目标；明确标注不触达实时外部服务。
* 每个"完成"必须指向真实产物（路径+字节数/行数）；账本终态检查 missing_or_empty 非空即该步不算完成。
* 重跑同一批次必须 unchanged；任何 delta≠0 的重跑都要解释。
* 冲突操作（keep/update）逐条留 policy 与冲突内容，禁止静默覆盖。

## 异常处理
| 情况 | 处置 |
|---|---|
| 来源缺失/服务说明不清 | probe 记录，status=partial + uncertainty，不虚构来源 |
| 迁移 sqlite 错误 | 事务回滚 + rolled_back:true + 账本 failed 步骤 |
| 步骤非幂等 | idempotence_violation 入账，禁止标记为稳定步骤 |
| CSV 导出行数与库不符 | 终态检查失败，回查 migration_log，status 降级 |
| 同步/版本冲突 | conflicts 清单 + policy 记录，交人工或按题目规则处置 |
| 需要人工接管 | handoff packet：当前状态、证据、待判问题 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo + 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-912f63bd/v2
