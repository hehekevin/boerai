---
name: file-landing-versioning
description: "Land a real batch of research files into an agreed directory tree with a metadata manifest, content-hash dedupe, version-chain reconstruction (who supersedes whom), collision-safe placement and an archive manifest — fully re-runnable from the log. Use when: a case asks to actually organize/upload/archive a file batch, not to advise. NOT for: filename-only dedupe, overwrite-on-collision, or metadata guessed without provenance."
---

# 科研资料库与文件管理：整理文件，也保留版本关系

面向"把一批混杂科研文件（原始数据、扫描件、补充材料、旧版本、改名备份）真正落库"任务。引擎做确定性簿记：`filelib` 盘点+内容哈希去重+落库计划+归档清单，`versions` 按内容重建版本链，`normalize` 维护元数据清单并保留字段出处。语义判断（项目归属、字段含义）由 Agent 完成并落盘为规则文件，第三方按清单可逐条复跑核对。

## 何时使用
* 用例给出一批真实文件与目录约定，要求落库、去重、元数据清单、版本关系与归档交接。
* 判定标准（题面原文）：落库后的目录树与元数据清单是否与约定一致；重复与版本关系是否按内容判断而不是按文件名判断；整理过程能否被他人按记录复跑并核对。

**不适用**：只给整理建议不动手落库、按文件名去重、同名直接覆盖、元数据靠文件名猜。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文件批次、伴随元数据表、目录约定等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" filelib inventory <批次根目录> $WORK/inventory.json
python "$SKILL/run.py" filelib plan $WORK/inventory.json $WORK/rules.json $WORK/landing_plan.json
# versions / normalize 处理（见下）
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/landing_report.md --artifact data=$WORK/archive_manifest.json
```

**第 1 步 盘点与哈希。** `filelib inventory`：全量 sha256；超大文件列入 skips（`listed_without_hash`）而不是假装入库；输出 duplicates 组。

**第 2 步 定规则。** Agent 依据 task.md 的目录约定写 `rules.json`：`{"template": "{project}/{year}/{kind}", "defaults": {...}, "fields": {rel: {...}}}`——字段可来自伴随表格/工单；来源不明的字段必须在 rules 里标注 `unknown`，引擎照样落盘。

**第 3 步 落库计划。** `filelib plan`：逐文件生成 destination；目标名被不同内容占用时自动加哈希后缀改名并记录 collision，**永不覆盖**；同哈希副本不重复占位。

**第 4 步 版本链。** `rlkit.versions`（输入 inventory files + 工单版本注记）：内容相同=副本/别名；词干相同内容不同=版本序列按 mtime 排序，supersede 边逐条留 `basis`；同名不同内容、注记不可验证分别进 conflicts。

**第 5 步 元数据与归档。** `normalize` 整理伴随表格为结构化清单（字段出处 `_provenance`、不可映射字段单列）；`archive_manifest` 输出交接清单（source、destination、sha256、bytes、totals），报告覆盖六类要素：文件类型、元数据字段、目录层级、重复文件、版本差异、权限与来源。

## 本题判据对齐（题面原文的"三件事"）
1. **"目录树与元数据清单是否与约定一致"** → rules.json 冻结约定，landing_plan 逐项 src→dest 可逐条比对。
2. **"重复与版本关系按内容判断而不是按文件名"** → 全部判据为 sha256 + mtime；文件名仅作词干线索；versions 输出每条 supersede 边的依据。
3. **"能否被他人按记录复跑并核对"** → inventory/plan/versions/archive 全是 JSON + 哈希，第三方重哈希源文件即可验证一一对应。

## 交付物
* `inventory.json`、`landing_plan.json`、`versions.json`、`metadata.json`、`archive_manifest.json`、`landing_report.md`、`result.json`

## 证据与审计规则
* 入库文件与源文件哈希一致是硬断言：archive_manifest 的 hashed 计数必须等于文件数（超限文件除外并单列）。
* 难处理文件（无权限、超大、特殊字符名）进 skips/conflicts 并写明原因，报告里禁止写"全部完成"除非 skips 为空。
* 元数据字段必须可回指出处；猜测字段标 `unknown` 来源并在 uncertainty 汇总。
* 重复运行同一计划结果稳定（dest 确定性生成），幂等。

## 异常处理
| 情况 | 处置 |
|---|---|
| 重名冲突（内容不同） | 加哈希后缀改名 + collisions 记录，禁止覆盖 |
| 文件损坏/哈希读取失败 | skips 记录 OSError 原因，不计入已入库 |
| 元数据缺失字段 | 留空 + 出处缺失 + uncertainty；不填"似是而非"的值 |
| 深层目录/特殊字符文件名 | inventory 原样记录 rel；dest 片段净化（去 `/`）并留痕 |
| 版本注记与内容矛盾 | admin_note_unverified 冲突，交人工核对 |
| 重复运行 | 同一 rules.json 产生同一 plan；already/unchanged 入账 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo + 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-2bfd9194/v2
