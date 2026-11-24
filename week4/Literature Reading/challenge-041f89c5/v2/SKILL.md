---
name: topic-novelty-assessment
description: "Research-topic and novelty assessment with hard bookkeeping: decompose a vague research idea into a testable statement (object/variables/baseline/expected outcome/falsifiable condition), check every novelty claim type-by-type against the closest prior work with covered/distinct/unclear boundaries and evidence, and force every feasibility premise to carry a source or an explicit assumption+risk label. Use when: a case provides literature and a research idea and asks for problem definition, prior-work comparison, novelty identification or feasibility judgement. NOT for: claiming global novelty from limited retrieval, treating scenario transfer as theory innovation, or unconditional 'feasible' verdicts."
---

# 科研选题与创新性评估：问题可检验、边界逐条划、前提有出处

聚焦方向：**创新点识别 + 可行性判断**（题面允许只选一个方向）。把"检索不到说成无人研究""场景迁移说成理论创新""一句'技术路线可行'"三类典型失败，变成引擎层的强制校验：问题五项不全即不可检验；创新陈述必须逐条与最近工作划界；可行性前提必须有来源或显式标假设。Agent 负责语义评估，引擎负责结构与证据簿记。

## 何时使用
* 用例给出研究设想与一组真实文献，要研究问题定义、已有工作比较、创新点判定或可行性结论。
* 判定标准：问题拆成可检验表述；创新点与最近工作逐条划清边界；可行性每个前提有来源或标为假设。

**不适用**：宣称全局新颖性（检索范围有限）、把应用迁移包装成理论创新、无条件可行结论。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（真实来源文献记录、研究设想、检索/筛选协议）。

## 输出（写入 /app/output）
`result.json` + `problem.json`（可检验问题陈述）+ `comparison.md`（已有工作比较矩阵）+ `novelty.json`（创新点逐条判定）+ `feasibility.json`（前提清单+有条件结论）+ `novelty_report.json`（引擎核验）+ `report.md`（评估报告）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 研究问题拆解。** 把模糊设想拆成五项：研究对象、关键变量、比较基线、预期结论、可证伪条件，写 `problem.json` 并校验：
```bash
python -m lrkit.novelty problem "$WORK/problem.json" "$WORK/problem_report.json"
```
五项缺一 → testable=false，先补齐再评估。

**第 2 步 已有工作比较。** 按任务/方法/数据/评价方式/结论建比较矩阵 `comparison.md`；真正相近的工作（closest work）逐条标出；无法直接比较的注明原因（数据不同、口径不同）。

**第 3 步 创新点逐条判定。** 每条创新陈述写 `novelty.json`：`{claim_id, kind: method|data|scenario|revision, text, closest_work, boundary: covered|distinct|unclear, evidence[]}`：
```bash
python -m lrkit.novelty novelty "$WORK/novelty.json" "$WORK/blocks.json" "$WORK/novelty_report.json"
```
`covered` = 已被已有工作覆盖，不得仍称创新；`distinct` 必须给差异证据（逐字引文）；`unclear` 写明缺什么证据。场景迁移标 scenario、结论修正标 revision，不混为 method。

**第 4 步 冲突证据登记。** 与设想结论相反的文献用 `lrkit.claims conflicts` 登记双方原话与取舍说明，避免只报告支持性证据。

**第 5 步 可行性前提核查。** `feasibility.json`：每条前提 `{premise_id, text, source_ref? | assumption: true + risk}`：
```bash
python -m lrkit.novelty feasibility "$WORK/feasibility.json" "$WORK/feasibility_report.json"
```
裸前提（无来源也未标假设）被引擎拒绝；假设必须带失败风险。可行性结论只能是**有条件的**：列出条件与风险，不给"技术路线可行"一句话。

**第 6 步 交付。**
```bash
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/report.md" --artifact data="$WORK/novelty_report.json"
```

## 本题判据对齐（题面"三件事" → 引擎机制）
1. **研究问题是否被拆成可检验的表述** → `validate_problem` 五项强制：对象/变量/基线/预期结论/可证伪条件，缺一即不可检验。
2. **创新点是否与最近的工作逐条划清了边界** → `validate_novelty_claims`：每条创新必须有 closest_work 与 boundary 判定；distinct 须附逐字差异证据；covered 进统计不得再称创新。
3. **可行性结论的每个前提是否有来源或被明确标为假设** → `validate_feasibility`：裸前提直接失败；假设必须附风险；结论按前提清单给条件式表述。
4. **检索范围诚实** → report 写明检索协议与覆盖范围；"检索不到" ≠ "尚无人研究"，结论边界写入 uncertainty。

## 交付物
* `problem.json`、`comparison.md`、`novelty.json`、`feasibility.json`、`novelty_report.json`/`feasibility_report.json`、`report.md`（含冲突证据与研究空白）。

## 证据与审计规则
* 每条判断可回到具体文献位置（逐字引文+loc）；文献必须真实存在于案例材料，不虚构引用。
* 区分材料事实、合理推断、无法确定：推断写 inferred，无法确定进 uncertainty。
* 冲突证据登记双方原话；取舍说明理由。
* 检索/筛选协议落盘（纳排规则、时间窗），结论不越过证据范围。
* 四件交付（问题定义、已有工作比较、创新点识别、可行性判断）相互一致：创新点引用比较矩阵行，可行性引用问题拆解的基线。

## 异常处理
| 情况 | 处置 |
|---|---|
| 检索为空/文献过少 | 如实报告覆盖不足，novelty 判 unclear，status 降 partial |
| 证据互相冲突 | claims conflicts 登记双方原话 + 取舍说明 |
| 创新点实为场景迁移 | kind=scenario 标注，不按方法创新陈述 |
| 可行性前提无法核实 | 标 assumption + 风险，不写进"已确认"列 |
| 接口/材料读取异常 | probe 报告，uncertainty 说明，status 降 partial |
| 设想本身不可证伪 | problem 校验失败，先与题面约束对齐改写再评估 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：novelty demo 演示问题五项校验、创新点划界（含 distinct 证据核验）与"裸前提被抓出"。示例文献与设想均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-041f89c5/v2
