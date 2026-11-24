---
name: sqlite-query-audit
description: "Query authorized SQLite snapshots with schema introspection first, row-count and join-inflation checks, column provenance, CSV snapshots with hash verification, and stats/report backfill downstream. Use when: a case provides a SQLite database (or tables) plus a data dictionary and asks for database querying, field interpretation, and cross-table analysis with recomputable results. NOT for: writing to the database, guessing schema without introspection, or reporting aggregates that cannot be re-run from the saved SQL."
---

# 科研数据库查询与分析：先自省 schema，再谈查询，行数必须对得上

面向"连接—查询—抽取—字段解释—跨表分析"链条。原则：不写"像 SQL 的文本"，每条查询都在授权快照上真实执行；连接键用值重叠验证；行数膨胀显式检查；结果快照带哈希可独立复算。Agent 负责把问题翻成 SQL 与解释字段语义，dakit.dbrun 负责执行、校验与留痕。

## 何时使用
* 用例给出 SQLite 数据库快照（含 UCI Concrete/Iris/Wine 类数据集入库形态）与查询/分析问题。
* 判定标准（题面"三件事"）：查询能否在授权快照上直接执行；结果能否与金标准或独立复算对上；字段含义与关联路径能否被他人按记录复核。

**不适用**：写库/改库、未自省 schema 就猜表名字段名、无法重跑的口头数字。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（`.db`/`.sqlite` 快照、数据字典、CSV 辅助表）。

## 输出（写入 /app/output）
`result.json`（case_id + output_contract 全字段 + status/sources/uncertainty/changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
```

**第 1 步 schema 自省（必做，禁止跳过）。** `python -m dakit.dbrun introspect /input/<快照>.db $WORK/schema.json`：表、列、声明类型、主键、外键、行数全部来自 sqlite_master/PRAGMA 实读。只读连接（URI mode=ro）；库文件不存在直接报错而不是建空库。

**第 2 步 字段解释与连接路径。** 对照数据字典给每个用到的字段写含义/单位/取值范围；编码型字段（如类别编号）禁止直接聚合。跨表连接键先用 `dakit.profile` 的 join_candidates（值重叠率 + 类型兼容）验证，一对一/一对多基数写进分析说明。

**第 3 步 执行查询。** `python -m dakit.dbrun query <db> "SELECT ..." $WORK/q1.json $WORK/q1.csv`：记录 SQL 原文、行数、耗时、列出处（同名列歧义标注）；含 JOIN 时自动做行数膨胀检查（结果行数 > 最大基表行数 → 警告漏连接条件）。报错保留 sqlite3 原始错误信息，修复后重跑，不得改写历史冒充一次成功。

**第 4 步 快照与一致性自检。** 结果集落 CSV + sha256 + CSV 行数 == 查询行数校验；这就是可独立复算的金标准对照物。

**第 5 步 下游统计与报告。** 查询结果需要统计时走 `dakit.stats`（假设先行），写报告走 `dakit.report` 占位符回填——报告数字只许来自 stats.json/查询 JSON。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact data=$WORK/q1.csv \
    --artifact stats_json=$WORK/stats.json
```

## 本题判据对齐
1. **"查询能否在授权的数据快照上直接执行"** → dbrun 只读执行真实 SQL，query JSON 记录原文与 elapsed_ms；写操作与多语句被引擎拒绝。
2. **"结果能否与金标准或独立复算对上"** → 每个结果集落 CSV + sha256 + 行数一致性自检；聚合口径（GROUP BY 粒度、连接键）写入 JSON，第三方按 SQL+快照可复算。
3. **"字段含义与关联路径能否被他人按记录复核"** → schema.json（PRAGMA 实读）+ column_provenance（结果列→基表列，歧义标注）+ join 基数说明。

## 交付物
* `schema.json`、`q*.json`（SQL+行数+出处+膨胀检查）、`q*.csv`（快照+哈希）、字段解释与连接路径说明（report.md 内）、下游 `stats.json`/`report.md`。

## 证据与审计规则
* 不许猜 schema：所有表/列名引用必须能在 schema.json 中找到。
* 行数异常必须解释：膨胀检查为 true 时要么修正连接条件，要么写明一对多是预期口径。
* 空结果是结果：记录 n_rows=0 并分析原因（条件过严/快照版本），不得反复改条件凑数。
* 快照版本入 sources（路径+sha256）；同题不同快照的结论不可混用。

## 方法与近似
统计环节同 stats 模块：正态性为偏度/峰度经验规则（非正式检验，n<20 功效低）；方差齐性为 Brown–Forsythe 近似；Welch df 为 Satterthwaite 近似。披露义务与近似限度写入报告。

## 异常处理
| 情况 | 处置 |
|---|---|
| 库文件缺失/损坏 | 直接报错（不建空库），status=partial 并写 uncertainty |
| 表名/列名不存在 | 保留 sqlite3 原始错误，回 schema.json 核对后修正重跑 |
| JOIN 后行数膨胀 | row_inflation_check 警告；核对连接键基数后再下结论 |
| 同名列出处歧义 | column_provenance 标 ambiguous，用 表.列 全名重写查询 |
| 权限/只读限制 | 引擎本来就是只读；需要写临时结果时写 $WORK，不写库 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：dbrun demo 现场建一个 2 表玩具库（含外键与一对多），验证自省、聚合查询、膨胀检查、快照一致性与写拒绝；另有 6 个模块 demo + 一次 CSV 端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-5c56458d/v2
