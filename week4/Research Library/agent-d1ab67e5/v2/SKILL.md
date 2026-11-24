---
name: software-ops-ledger
description: "Run a real scientific-software operation chain (import → configure → recalculate → export → verify) with an operation ledger, terminal-state assertions, idempotence checks and rollback-to-state. Built for attributed UCI-style datasets through real headless LibreOffice. Use when: a case asks to actually operate scientific software on provided input files and keep a reviewable trail. NOT for: simulated software, click-through instructions, written-state success, or live network services."
---

# 科研软件操作 Agent：完成操作，也保留过程轨迹

面向"在科研软件里真实跑完导入—设置—运行—导出—检查整条链并留下可复核轨迹"任务。本技能把软件操作组织成带前置条件与完成判据的步骤序列：每一步真实执行（LibreOffice headless 导入数据集、按重算配置真实重算、真实导出 PDF），每步前后对受监视目录做哈希状态快照，失败可回滚到任一前置状态，幂等性用二次运行逐字节比对来断言。**绝不用操作说明代替真实执行，绝不把未运行的步骤写成成功。**

## 何时使用
* 用例给出真实数据集文件（如 UCI 数据集 CSV）与任务单，要求导入计算软件、配置/重算、导出结果并检查。
* 判定标准：目标软件里真的跑完并交出可打开的产物；软件状态与导出物和任务参数/单位/版本一致；失败可发现、可回滚、可复核。

**不适用**：模拟软件行为、写"请依次点击"的操作说明、联网服务、需要许可证/登录的交互式 GUI 操作。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：数据集文件、参数要求、既有工程文件等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" soffice_ops status            # 先确认目标软件真实可用性
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial|failed> \
    --artifact report=$WORK/ops_report.md --artifact data=$WORK/ledger/.op_ledger.json
```

**第 1 步 读任务单与权限边界。** probe 输出里确认输入文件哈希、参数/单位/版本要求；`soffice_ops status` 不可用则在 uncertainty 与 limits 中如实写明，只做确定性簿记部分，绝不假装执行。

**第 2 步 建账本。** 用 `rlkit.ledger.OpLedger($WORK/ledger)` 包住整条链；每一步 `run_step(name, fn, expected_artifacts=[...])` 自动记录 pre/post 状态哈希与终态检查（产物存在且大小>0，PDF 校验 %PDF 魔数）。

**第 3 步 真实执行链。** 导入：`soffice_ops.import_dataset(csv, …)`（exit code + 产物字节数断言）；设置/重算：`soffice_ops.recalculate(…)`（专用 profile 强制 load 时重算，`OOXML/ODFRecalcMode=0`，不信缓存值）；检查：`soffice_ops.verify_computed(…)` 把重算结果导出 CSV 网格，逐格与任务预期值比对；导出：`soffice_ops.export_pdf(…)`。一条参考命令：`python "$SKILL/run.py" soffice_ops chain <输入文件> $WORK/chain`。

**第 4 步 幂等与失败恢复。** 关键写步骤用 `ledger.assert_idempotent(name, fn)` 二次运行断言零差异；任一步 `failed/terminal_failed` 时 `ledger.rollback(seq)` 回到该步前置状态，把半成品从"本次结果"中清除，重跑必须引用回滚记录编号。

**第 5 步 汇总。** `ops_report.md` 逐步列出命令、soffice 版本、exit code、产物路径与字节数、状态差异、终态检查结果；材料没有/无法判断的部分写进 uncertainty，status 相应降级。

## 本题判据对齐（题面原文的"三件事"）
1. **"任务是否真的在目标软件里跑完并交出可继续使用的产物"** → 每步真实调用 soffice，断言 exit code、产物存在、大小>0、PDF 魔数；`verify_computed` 用重算后的 CSV 网格核对数值（demo 里缓存值 0 必须被真实重算成 5 才通过）。
2. **"软件实际状态与导出结果是否与任务给定的参数、单位、版本一致"** → result.json 记录 soffice 版本；recalc profile 保证导出值来自本次真实重算而非残留缓存。
3. **"失败发生时能否被发现、被回滚、被复核"** → 账本逐步留 pre/post 哈希快照，rollback 到指定步骤，幂等断言防止半成品覆盖，第三方可拿 `.op_ledger.json` 逐步复核。

## 交付物
* `$WORK/ledger/.op_ledger.json`（全步骤账本：状态快照、diff、终态检查、回滚记录）
* `$WORK/chain/`（导入产物、重算产物、复算 CSV、PDF）+ `ops_report.md`
* `result.json`（status 诚实分级，失败含原因与停在哪一步）

## 证据与审计规则
* 任何"已完成"都必须指向真实产物：路径 + 字节数 + 校验（哈希或魔数），没有产物的步骤 status 不能是 done。
* 不可用（无 soffice、权限不足、文件被占用）→ 诚实 status=unavailable/failed + limits 说明，不产出模拟结果。
* 重试前必须先回滚，禁止用上一次半成品充当本次结果（账本中 rollback_of 可溯源）。
* 版本、命令、stdout/stderr 截取全部入账，换一台机器可按记录复跑。

## 异常处理
| 情况 | 处置 |
|---|---|
| soffice 不存在/--version 失败 | status=unavailable，报告原因与受限范围，只做确定性部分 |
| 输入文件缺失/不可读 | 该步 failed，原因入账，不继续下游步骤 |
| 转换 exit≠0 或产物缺失/0 字节 | status=failed + stderr 截取；rollback 到前置状态 |
| 重算值与预期不符 | verify_computed 输出实际网格，差异写入 uncertainty，status=partial |
| 步骤非幂等（二次运行有差异） | idempotence_violation 入账，禁止把该步骤标记为稳定 |
| 超时 | subprocess timeout 记录为 failed(error=timeout)，可回滚 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo（soffice demo 在有 LibreOffice 时做真实导入/重算/PDF 并断言数值与魔数，无 LibreOffice 时断言诚实 unavailable 路径）+ 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/agent-d1ab67e5/v2
