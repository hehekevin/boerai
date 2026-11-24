---
name: search-general-forge
description: 文献检索领域总课题。检索全链路编排：查询规划→执行审计→去重→筛选排序→增量追踪→迭代补检，输出可追溯候选集、筛选依据与遗漏说明。覆盖六个子场景（覆盖率审计/纳排筛选/多库联合/跨语言/增量追踪/引文追踪），每子场景独立可复跑。触发词：文献检索、全链路、总课题、候选集。
---

# search-general-forge — 文献检索领域总课题

一句话：**全链路编排、六子场景可独立复跑、每条结果带依据、遗漏必说明。**

## 核心原则（不可违反）

1. **四步保底**（题面明确）：①明确研究问题和检索范围；②设计或改进检索、筛选、排序或追踪流程；③对每条结果保留来源和相关性依据；④对无结果、冲突、缺失元数据和权限问题明确说明。
2. **按子场景拆分交付**：不要求覆盖所有细分场景——按 case.json 的任务类型路由到对应子引擎（覆盖率审计 search_audit / 纳排筛选 screening_engine / 迭代补检 iter_loop），每个子场景独立可复跑。
3. **候选集可追溯**：每条候选文献带来源（库/查询式/字段来源）；排序或筛选结论带依据码。
4. **遗漏必说明**：无结果/冲突/缺失元数据/权限问题逐条说明，不静默。
5. **脚本先行**：全部确定性操作0模型请求。

## 工作流程

### 阶段 0：盘点与路由（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```
从 task.md 判断子场景：覆盖率审计→search_audit --coverage/--classify；纳排筛选→screening_engine --screen；多轮迭代→iter_loop --ledger/--stop；混合任务→全链路编排。

### 阶段 1-3：按路由执行子引擎（0请求/子命令）
```bash
python <SKILL_DIR>/scripts/search_audit.py --plan/--coverage/--classify/--dedup
python <SKILL_DIR>/scripts/screening_engine.py --protocol/--screen/--dedup-multi/--audit
python <SKILL_DIR>/scripts/iter_loop.py --ledger/--stop/--rollback
```

### 阶段 4：综合成文（约2-4次模型请求）
检索报告：候选集（带来源与依据）→筛选/排序说明→遗漏与缺口说明→下一步建议。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/search-report.md --require "范围|scope|研究问题,依据|evidence|来源|source,遗漏|miss|缺口|gap,候选|candidate" --names "scope,evidence,misses,candidates"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 子场景无法判断 | 全链路执行（plan→coverage→screen→audit），各环节分别报告 |
| 部分引擎不适用 | 路由说明写入 anomalies，不硬跑 |
| 材料为空 | gaps 声明，输出协议与规划部分交付 |
| 预算不足 | 已执行子场景 JSON 先落盘 status=partial |

## 资源清单
- `scripts/search_audit.py`、`scripts/screening_engine.py`、`scripts/iter_loop.py` — 三个子引擎
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/general-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。子引擎恒为0请求；模型路由+成文（≤5次）。过60%时间冻结。