---
name: reproducible-analysis-run
description: "Generate and execute research-analysis code that actually runs in the given environment: stdlib-only engine, explicit run logs and exit codes, golden-value self-verification, silent-error detection (missing-as-zero, undeduplicated counts, unchecked t-test premises), and preserved failure scenes. Use when: a case asks to write cleaning/statistics/plotting code, configure the environment, run it on real data and verify results against a data dictionary or gold standard. NOT for: code that cannot be re-run from saved inputs, or 'looks-right' numbers without a verification step."
---

# 科研代码生成与执行：跑通只是起点，跑对才算完成

本题的危险不是"写不出来"而是"看起来对了"：缺失被当 0、重复未去重、t 检验前提没查就报 p。本技能的对应策略：分析逻辑收敛到 dakit 引擎（纯标准库，无依赖可配错），每次执行保留命令/退出码/日志，引擎自带教科书金标准自检（selftest.py），结果验证是流水线的强制步骤而不是可选项。Agent 生成的是"调用引擎的编排代码与规则文件"，确定性计算不手写。

## 何时使用
* 用例要求根据数据字典与任务描述生成清洗/统计/可视化代码，配置环境，真实跑通并核对结果。
* 判定标准（题面"三件事"）：代码能否在给定数据和环境下真正跑通；数值与图表能否同数据字典、统计口径和金标准对上；过程与失败原因能否被他人复核。

**不适用**：实验方案设计、机理解释、论文写作；不保留运行现场的一次性脚本。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（数据表/SQLite、数据字典、约束）。

## 输出（写入 /app/output）
`result.json`（case_id + output_contract 全字段 + status/sources/uncertainty/changes）+ 交付物（见下）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
export PYTHONPATH="$SKILL"
# 第 0 步 环境自检（替代依赖安装）：引擎只用标准库，先证明引擎自身可信
python "$SKILL/selftest.py"        # 必须 8/8 pass；失败则停止并报告现场
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" tables  --work "$WORK"
```

**第 1 步 代码生成 = 编排 + 规则文件。** Agent 产出的是：`rules.json`（清洗规则，数据非代码）、`stats_spec.json`（检验与假设组）、`shape.json`（图表形态）、报告模板——全部可 diff、可复跑；字段名必须先在 `profile.json`/数据字典中存在（防"字段名与数据字典对不上"）。

**第 2 步 逐步执行并留痕。** 每步记录命令与退出码（run.log），中间产物落盘：

```bash
python -m dakit.profile "$WORK/tables.json" "$WORK/profile.json"
python -m dakit.clean   "$WORK/tables_0.json" "$WORK/rules.json" "$WORK/clean.json"
python -m dakit.stats   "$WORK/stats_spec.json" "$WORK/stats.json"
python -m dakit.report  "$WORK/report.tpl.md" "$WORK/stats.json" "$WORK/report.md" "$WORK/report_mapping.json"
```

**第 3 步 结果验证（强制）。** ①行数对照：clean 账本 before/after 与原始行数、输出 CSV 行数三方一致；②静默错误排查清单：缺失是否被当 0（账本 fill_value）、重复是否去重（affected_row_ids）、检验前提（stats.json 的 assumptions 段）；③报告数字与 stats.json 一致性由 report.validate 机检。

**第 4 步 错误处理。** 引擎报错（缺列、类型不符、查询为空、方差为 0）保留完整现场到 run.log，按"识别→修复输入/规则→重跑"处理；禁止换段代码继续试而不记录，禁止手填"合理"数值。

```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact code=$WORK/run.log \
    --artifact stats_json=$WORK/stats.json --artifact data=$WORK/clean_ledger.json
```

## 本题判据对齐（题面原文 → 机制）
1. **"跑通了但算错了"的静默错误** → 验证步骤机检：账本行 id、assumptions 段、report.validate 数字同源；selftest 注入缺失/异常/重复验证全链能抓到。
2. **"依赖没装、路径写死"跑不起来** → 引擎零依赖（csv/sqlite3/statistics/math/json），全部路径经 $WORK 相对化，probe 实读输入路径。
3. **"隔天重跑得到另一套数字"** → 引擎全确定性、无随机源、无时钟依赖（时间戳仅在 result.json）；Python 版本写入 runtime。
4. **"出错之后不定位原因"** → run.log + 引擎原生错误现场 + status=partial 的 limits 说明。

## 交付物
* `run.log`（命令+退出码+错误现场）、`rules.json`/`stats_spec.json`（生成的规则与口径）、`clean_ledger.json`、`stats.json`、`report.md`+`report_mapping.json`、selftest 输出。

## 证据与审计规则
* 每个数字可回算：报告占位符 → stats.json → 清洗后行 → 账本 → 原始快照（sha256）。
* 修复必须增量：改规则文件重跑，changes.json 记录改了什么、为什么。
* 引擎自检失败 = 环境不合格，停止分析并报告，不得带病运行。
* 近似披露：正态性（偏度/峰度经验规则）、方差齐性（Brown–Forsythe）、Welch df（Satterthwaite）均为近似，写进报告方法节。

## 异常处理
| 情况 | 处置 |
|---|---|
| 缺列/字段名不符 | profile 对照数据字典；报错留现场，修正映射后重跑 |
| 类型不符/编码错误 | extract 层 errors=replace 保底 + profile mixed 列警告 |
| 查询为空 | 记录 n_rows=0，分析条件口径，不反复改条件凑数 |
| 数值溢出/除零/零方差 | 引擎断言失败给原因，status=partial |
| 自检（selftest）不过 | 停止并交付失败现场，视为环境问题而非数据问题 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：7 个模块 demo（金标准断言）+ 端到端（合成 CSV → 全链 → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Data%20Analysis/challenge-9ec929fe/v2
