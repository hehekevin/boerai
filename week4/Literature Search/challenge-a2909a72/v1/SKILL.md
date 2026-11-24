---
name: scholarly-search-forge
description: 学术文献检索。多轮查询规划（复杂问题拆解为多步检索提高覆盖度），关键词扩展（专业术语/同义词/缩写/跨语言表达），数据库选择与组合（相关性/覆盖度/元数据质量/执行效率权衡），结果去重与来源记录（核验文献信息，保留可靠来源）。触发词：学术检索、关键词扩展、多轮、去重。
---

# scholarly-search-forge — 学术文献检索

一句话：**多轮规划提覆盖、扩展控发散、库组合有权衡、去重留来源。**

## 核心原则（不可违反）

1. **多轮查询规划**：复杂科研问题拆解为多步检索（要素合取→同义扩展→放宽兜底），提高关键文献覆盖度，减少遗漏和无效查询；每轮有目的与判据。
2. **关键词扩展控发散**：专业术语/同义词/缩写/跨语言表达逐词扩展；扩展矩阵留痕（哪词扩了哪些变体）。
3. **库组合有权衡**：按相关性/覆盖度/元数据质量/执行效率四维选择数据库组合，权衡理由记录。
4. **去重与来源记录**：DOI优先去重、无DOI标题归一化；每条记录保留来源库与查询式——可追溯。
5. **脚本先行**：扩展矩阵/去重/多轮台账恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：扩展矩阵与查询模板（0请求）
```bash
python <SKILL_DIR>/scripts/search_audit.py --plan <关键词...> > /app/work/plan.json
```

### 阶段 2：多轮执行与去重（0请求）
```bash
python <SKILL_DIR>/scripts/search_audit.py --dedup <结果集>
python <SKILL_DIR>/scripts/iter_loop.py --ledger <查询日志.tsv> > /app/work/ledger.json
```

### 阶段 3：停止评估与成文（0请求 + 1次复核）
```bash
python <SKILL_DIR>/scripts/iter_loop.py --stop /app/work/ledger.json
```
模型复核相关性初筛与库组合权衡说明。

### 阶段 4：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：plan、dedup、ledger、stop、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/search-report.md --require "规划|plan|轮次|round,扩展|expansion|同义词,库|database|组合,去重|dedup|来源|source" --names "plan,expansion,dbs,dedup"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 结果集缺失 | 只交付 plan+ledger，gaps 声明 |
| 关键词过少 | 模型从研究问题补充，标注来源 |
| 预算不足 | plan.json 先落盘 status=partial |

## 资源清单
- `scripts/search_audit.py`、`scripts/iter_loop.py` — 扩展规划/去重/台账/停止
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/scholarly-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。引擎恒为0请求。过60%时间冻结。