---
name: multdoc-compare-forge
description: 多文档比较与整合。共同字段定义统一后逐篇抽取（对得齐），每格值随单位/数据集/指标口径记录（填得准），结论冲突归因到样本/方法/条件/指标（说得清），每值每结论回到原文位置（查得回）；可比性判定区分全量可比与子集可比。触发词：多文档比较、对比矩阵、冲突归因、可比性。
---

# multdoc-compare-forge — 多文档比较与整合

一句话：**字段先对齐、口径随值走、冲突归因到条件、每格可回原文。**

## 核心原则（不可违反）

1. **对得齐**：研究对象/数据来源/方法设置/实验条件/评价指标/主要结论/局限性七字段统一定义后逐篇抽取——不是各写各的。
2. **填得准**：每个单元格的值来自它标注的那篇论文；单位、数据集版本、指标口径随值记录（field_sources）。
3. **说得清**：结论一致或冲突时，归因到样本/方法/条件/评价指标差异——脚本给出归因候选，模型语义裁决。
4. **查得回**：每个取值和差异结论回到原文具体位置（paper_id+字段+来源），他人可按记录复算。
5. **可比性判定**：条件描述一致=全量可比；条件差异=只能在可比子集内比较（subset_only+子集清单）。
6. **脚本先行**：矩阵/可比性/冲突归因恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：统一字段抽取（约2-3次模型请求 + 0请求建矩阵）
按七字段定义逐篇抽取（模型），写成 papers.json（每字段带取值规则与原文位置）；建矩阵：
```bash
python <SKILL_DIR>/scripts/compare_matrix.py --matrix /app/work/papers.json > /app/work/matrix.json
```

### 阶段 2：可比性判定（0请求）
```bash
python <SKILL_DIR>/scripts/compare_matrix.py --comparable /app/work/matrix.json > /app/work/comparable.json
```

### 阶段 3：冲突归因（0请求）
```bash
python <SKILL_DIR>/scripts/compare_matrix.py --conflicts /app/work/matrix.json > /app/work/conflicts.json
```
方向冲突的归因候选由模型按原文裁决（条件差异具体是什么）。

### 阶段 4：跨文档证据整合（约1-2次模型请求）
一致结论汇总+冲突解释+整合建议。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/compare-report.md --require "对齐|align|字段|field|矩阵|matrix,口径|unit|metric|随值,冲突|conflict|归因|attribution,回|locate|位置|source" --names "align,caliber,conflicts,backlink"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 论文缺某字段 | 标 missing，可比性降级 |
| 指标口径不同（accuracy vs AUC） | 不可直接比较，标注换算需求或仅定性对比 |
| 冲突无法归因 | attribution_candidates 保留候选+人工核查队列 |
| 预算不足 | matrix.json 先落盘 status=partial |

## 资源清单
- `scripts/compare_matrix.py` — matrix/comparable/conflicts（确定性引擎）
- `scripts/multidb_engine.py` — 字段标准化复用
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/compare-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。矩阵/可比/归因恒为0请求；模型抽取+裁决（≤6次）。过60%时间冻结。