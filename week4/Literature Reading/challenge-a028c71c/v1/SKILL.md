---
name: reading-general-forge
description: 文献阅读领域总课题。阅读领域总课题：按case路由到子能力（公式解析/问答/提取/溯源/比较/清洗/分类/批注/评测），全链路可追溯。触发词见核心原则。
---

# reading-general-forge — 文献阅读领域总课题

## 核心原则（不可违反）

1. **四步保底**：明确任务与范围→设计或改进阅读流程→每条结果保留来源与依据→无结果/冲突/缺失/权限显式说明。
2. **按子场景路由**：公式→math_audit；问答→qa_engine；结论数据→extraction_engine；溯源→verify_engine；比较→compare_matrix；清洗→clean_engine；分类→classify_engine；批注→annotation_engine；评测→bench_engine；网页→content_extract。路由理由记录。
3. **每子场景独立可复跑**；路由错误进 anomalies 不硬跑。
4. **脚本先行**；模型仅路由判断+成文。

## 运行环境约定

- 输入 `/input/case.json` 与 `/input/task.md`；材料以实际路径为准。工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段0 盘点与路由（1请求）：`python scripts/inspect_case.py /input/case.json`
### 阶段1-N 按路由执行子引擎（0请求/子命令）
### 阶段末 综合成文（1-2请求）+ result.json 契约核验

### 交付阶段（0请求）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/reading-general-forge.md --require "原则关键词,流程关键词,异常关键词" --names "p1,p2,p3"
```

主产物 `/app/output/reading-general-forge.md`：每条结论带锚点。

## 异常处置速查（详见 references/rules.md）

| 情形 | 处置 |
|-|-|
| 子场景无法判断 | 多引擎串联全跑，各环节分别报告 |
| 引擎不适用 | anomalies 记录不硬跑 |
| 材料为空 | gaps 声明部分交付 |

## 资源清单

- `scripts/`：qa_engine.py, extraction_engine.py, verify_engine.py, compare_matrix.py, clean_engine.py, classify_engine.py, annotation_engine.py, bench_engine.py, novelty_matrix.py, content_extract.py；inspect_case.py、validate_result.py
- `references/rules.md`、`templates/result.schema.json`、`examples/minimal-example.md`、`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。确定性子命令恒为 0 请求；模型仅语义裁决与成文。过 60% 时间冻结：JSON 先落盘，status=partial。