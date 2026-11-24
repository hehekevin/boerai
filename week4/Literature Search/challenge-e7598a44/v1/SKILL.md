---
name: question-driven-search-forge
description: 科研问题驱动检索。研究问题先拆解为要素矩阵（对象/机制/方法/时间/比较/证据六槽），逐要素生成查询片段再组合，禁止一句话查询打天下；多轮检索按缺口调整，停止条件四类判据。触发词：问题拆解、要素矩阵、多轮检索、查询组合。
---

# question-driven-search-forge — 科研问题驱动检索

一句话：**先拆解后查询、要素矩阵留痕、多轮按缺口调整、停止有判据。**

## 核心原则（不可违反）

1. **禁止跳过拆解**：研究问题必须先拆成六要素矩阵（对象/机制/方法/时间范围/比较关系/证据要求），识别其中的对象、机制、方法、时间范围、比较关系和证据要求，形成结构化子问题清单——直接写查询=失败。
2. **拆解留痕**：每要素记录 extracted_terms + extraction_basis（词典直查/正则/模型补充）；模型补充的要素显式标注 extraction_basis=model。
3. **组合不拼接**：逐要素生成查询片段（OR组），要素间 AND 组合；一轮宽泛析取兜底召回。
4. **多轮按缺口调整**：R1核心合取→R2同义词扩展+放宽字段→R3缺口驱动；每轮根据上一轮结果调整，形成可解释的迭代路径。
5. **停止条件四类**：边际收益为0/轮次上限/证据充分性/人工介入——脚本评估，不凭感觉。
6. **脚本先行**：拆解/规划/多轮提案恒为0模型请求；模型只补词典未覆盖的语义要素。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：问题拆解（0请求 + 1次模型请求回填）
```bash
python <SKILL_DIR>/scripts/question_decompose.py --decompose "<研究问题>" > /app/work/matrix.json
```
六槽词典直查；gaps_for_model 槽位由模型语义补充回填（extraction_basis=model）。

### 阶段 2：查询规划（0请求）
```bash
python <SKILL_DIR>/scripts/question_decompose.py --plan /app/work/matrix.json > /app/work/plan.json
```
产出要素片段、R1-core/R1-broad 模板、三轮规划（R1核心→R2扩展→R3缺口）。

### 阶段 3：多轮执行与调整（0请求/轮）
执行 R1 → 记录台账 → `--rounds` 提案下一轮 → R2/R3。每轮调整理由记录在案。

### 阶段 4：停止评估与成文（0请求 + 1次复核）
```bash
python <SKILL_DIR>/scripts/question_decompose.py --stop /app/work/ledger.json
```
证据充分/边际收益过低/转人工三类判据。模型撰写检索报告：子问题清单→查询路径→命中汇总→缺口说明。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：要素矩阵（含basis）、查询计划、轮次台账、停止评估、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/qsearch-report.md --require "拆解|decompose|要素|matrix|槽位,查询|query|规划|plan,多轮|round|迭代,停止|stop|判据" --names "decompose,plan,rounds,stop"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 词典未覆盖领域术语 | gaps_for_model → 模型补充，basis=model |
| 问题过短/信息不足 | 槽位大量空 → 模型向题面上下文找线索，仍缺则 gaps 声明 |
| R1 命中为0 | 检查要素拼写/换同义词，报告执行证据不虚构 |
| 预算不足 | matrix/plan 先落盘 status=partial |

## 资源清单
- `scripts/question_decompose.py` — 拆解/规划/多轮提案/停止（确定性引擎）
- `scripts/search_audit.py` — 每轮覆盖率审计
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/qdriven-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。拆解/规划/轮次提案/停止恒为0请求；模型仅要素回填与成文（≤5次）。过60%时间冻结：matrix+plan 先落盘。