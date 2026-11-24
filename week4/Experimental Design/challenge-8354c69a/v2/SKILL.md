---
name: result-anomaly-analysis
description: "Interpretation of experimental results and anomaly analysis with a locator-bound evidence ledger: trend claims, anomaly points with thresholds, ranked cause hypotheses with supporting/excluding evidence, executable recheck steps, and next-experiment suggestions - every conclusion traceable to a data row. Use when: a case provides real experimental outputs (traces, workbooks, logs) and asks what the data shows, which points are anomalous, why, and what to recheck. NOT for: fabricating wet measurements, causes or replicates; statistical modeling beyond the provided data."
---

# 实验结果解释与异常分析：每条结论回指数据行

面向"这批数据说明什么、哪个点异常、为什么、接下来复核什么"的任务。本技能把解释拆成确定性簿记（引擎）与语义判断（Agent）：引擎负责数据/日志的结构化抽取（每行带定位）、检查表覆盖控制（未查项显式列出）、异常→失败模式映射验证与结论门控；Agent 负责读数、判断趋势与异常、排序原因候选——**任何结论必须能回指原始数据行并说明判定阈值**。

## 何时使用
* 用例给出真实实验结果材料（读数轨迹、工作簿、设备日志、原始论文/方法说明），要求输出趋势判断、异常点定位与程度、原因候选清单、复核步骤与后续实验建议。
* 判定标准：结论可回溯到数据行；阈值明确；第二个人可按记录复算；不编造测量值、原因或重复数。

**不适用**：脱离提供数据的统计建模、补造湿实验测量、论文写作。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（轨迹/工作簿/日志/方法说明等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"          # 表格/文本带定位落盘
python "$SKILL/run.py" review  --work "$WORK" --source <结果汇总或方法文本>
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/interpretation_report.md --artifact data=$WORK/ledger.json \
    --artifact result=$WORK/conclusion_gate.json
```

**第 1 步 数据落位。** extract 把工作簿/CSV/日志抽成带 sheet/行号定位的文本与数据行；Agent 从数据行读数，**数值一律引用定位（sheet+行/列），不得凭记忆转写**。源数据的单位/方法/阈值含糊处原样保留并写入 uncertainty，不做隐式澄清。

**第 2 步 解释台账。** 每条解释结论写入 `ledger.json`：`{id, kind: trend|anomaly|cause|recheck|next_step, claim, threshold, evidence:[{quote, locator}], basis}`。kind=anomaly 必须给出判定阈值（与对照/重复/区间的偏离口径）与异常程度；kind=cause 必须按证据强度排序并分列支持证据与排除证据，标注"相关误当因果"风险。用 `planparse validate ledger.json <来源文本>` 核验每条 locator 可解析——无定位结论被驳回留痕。

**第 3 步 检查表覆盖。** 按本题六要素自建同构 checklist（`checklist init` 后按 schema 改写条目：假设与变量/对照组/设备材料批次/时间成本/参数范围/风险与异常），每条解释结论须能回指其依赖的要素行；coverage 命令逐面计数，**未查项显式列出，不默认满足**。

**第 4 步 异常→失败模式映射。** 异常点登记进 `risk_register.json`（failure_mode=具体异常机理假设，likelihood/impact 按证据分级），`riskreg validate`：泛泛的"数据异常/注意安全"式 failure_mode 被驳回；**每个异常必须映射到具体失败模式**，复核步骤（recheck）须是可执行动作（回查某文件某字段/核对批次与设备日志/加做对照），"检查数据质量"式空话不得入册。

**第 5 步 结论门控与建议。** `verdict build` 对台账门控：存在未查要素 → 结论降级并显式列出；依据缺口写入 uncertainty。后续实验建议（next_step）逐条挂到原因候选与证据缺口（补对照/加密采样点/调整参数范围/扩大重复数），并注明预期成本口径（可用 resources 精确算）。

## 本题判据对齐（题面原文）
1. **"无法回溯到原始数据行、无法说明判定阈值、无法让第二个人按记录复算，就不能作为实验结论使用"** → 台账强制 quote+locator+threshold；planparse.validate 驳回无定位结论；全部产物 JSON 可复算。
2. **"正常波动被当成异常……异常点被归到错误的样本或批次上"** → anomaly 条必须写偏离口径与程度，evidence 并列对照/重复数据行定位。
3. **"原因只给一个没有排除过程的机理猜测"** → cause 条强制支持/排除证据分列与证据强度排序。
4. **"复核步骤写成'检查数据质量'这类无法执行的话"** → recheck 条必须是可执行动作并落到具体文件与字段；riskreg 的 GENERIC 词表驳回空话。
5. **"任何一条解释结论都要能回指到它所依据的假设与变量、对照设置、设备与材料批次、时间与成本约束、参数范围和风险判断"** → 六要素 checklist 覆盖计数，缺口显式列出。

## 交付物
* `interpretation_report.md`（趋势/异常/原因/复核/后续五节）、`ledger.json`（验证后台账）、`checklist.json`、`risk_register.json`+`risk_validation.json`、`conclusion_gate.json`。

## 证据与审计规则
* 无 quote+locator 的结论不得入册；驳回留痕不删除。
* 不编造湿实验测量值、原因或重复数；数据没有的内容写 uncertainty 并降级 status。
* 源数据的单位/方法/阈值歧义原样保留，标注"按原文口径"，不做隐式换算。
* 数值比较用精确算术（Fraction/int），判定阈值随结论一起落盘。

## 异常处理
| 情况 | 处置 |
|---|---|
| 数据文件无法解析 | 记 uncertainty，只解释可读部分，status=partial |
| 单位/方法含糊 | 原样保留并标注歧义，对应结论标 needs_review |
| 异常点归属不清（样本/批次/通道） | 并列各归属假设与证据，不强行定论 |
| 原因证据不足 | 原因候选如实标"证据不足"，写入 uncertainty |
| 结论与原始数据冲突 | 以数据行为准，冲突处双定位并列 |
| 材料要求外部数据而无法获取 | 说明缺口，不联网补造 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：6 个引擎模块 demo（含无定位条目被驳回、异常步骤未映射失败模式被列出、未查项→结论降级守卫）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/challenge-8354c69a/v2
