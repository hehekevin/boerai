---
name: novelty-assess-forge
description: 科研选题与创新性评估。研究问题定义（对象/变量/基线/可证伪）、已有工作比较矩阵、创新点四类判定、可行性带条件结论。触发词见核心原则。
---

# novelty-assess-forge — 科研选题与创新性评估

## 核心原则（不可违反）

1. **问题定义**：模糊设想拆成研究对象/关键变量/比较基线/预期结论/可证伪条件五要素——不可证伪的问题陈述必须标注并补全验证途径。
2. **比较矩阵**：按任务/方法/数据/评价方式/结论五维建矩阵；标出无法直接比较的原因（数据集/评价口径）。
3. **创新点判定**：区分方法创新/数据创新/场景迁移/结论修正；每条创新陈述对照矩阵判定是否已被覆盖；只对给定论文集判定，不声明绝对新颖。
4. **可行性**：核查数据/算力/实验条件/时间窗/人员能力前提；输出带条件的可行性结论+失败风险——未声明前提列为假设。
5. **脚本先行**：decompose/matrix/novelty/feasibility 恒为0模型请求。

## 运行环境约定

- 输入 `/input/case.json` 与 `/input/task.md`；材料以实际路径为准。工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段0 盘点（1请求）：`python scripts/inspect_case.py /input/case.json`
### 阶段1 问题拆解（0请求）：`python scripts/novelty_matrix.py --decompose "<设想>"`
### 阶段2 比较矩阵（0请求+1-2请求抽取）：`python scripts/novelty_matrix.py --matrix papers.json`
### 阶段3 创新判定（0请求）：`python scripts/novelty_matrix.py --novelty matrix.json claims.json`
### 阶段4 可行性（0请求）：`python scripts/novelty_matrix.py --feasibility proposal.json`
### 阶段5 成文（1-2请求）：选题评估报告

### 交付阶段（0请求）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/novelty-assess-forge.md --require "原则关键词,流程关键词,异常关键词" --names "p1,p2,p3"
```

主产物 `/app/output/novelty-assess-forge.md`：每条结论带锚点。

## 异常处置速查（详见 references/rules.md）

| 情形 | 处置 |
|-|-|
| 设想过短 | 要素大量'待补充'→模型按上下文回填 basis=model |
| 比较集为空 | 无法判新颖性→gaps声明 |
| 前提未声明 | 列为假设+失败风险 |

## 资源清单

- `scripts/`：novelty_matrix.py；inspect_case.py、validate_result.py
- `references/rules.md`、`templates/result.schema.json`、`examples/minimal-example.md`、`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。确定性子命令恒为 0 请求；模型仅语义裁决与成文。过 60% 时间冻结：JSON 先落盘，status=partial。