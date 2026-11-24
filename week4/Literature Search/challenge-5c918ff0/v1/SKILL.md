---
name: multidb-union-search-forge
description: 多数据库联合检索。按各库语法方言安排查询（不机械复制），跨库字段映射标准化（区分missing与unknown），合并保留裁决规则与来源回溯，失败降级显式披露缺口。触发词：多数据库、联合检索、字段映射、合并去重、来源回溯。
---

# multidb-union-search-forge — 多数据库联合检索

一句话：**各库各语法、字段有映射、合并留裁决、来源可回溯、失败即披露。**

## 核心原则（不可违反）

1. **不机械复制查询**：按各库检索语法、字段能力、调用额度分别安排查询（PubMed/MeSH、WoS/TS=、Scopus/TITLE-ABS-KEY），处理分页/限流/超时；每库查询式单独留痕。
2. **字段标准化**：跨库字段映射表（TI/title/dc:title→title 等）统一作者/期刊/年份/标识符/文献类型表示；missing（原始记录无此字段）与 unknown（存在但不可解析）严格区分。
3. **合并留裁决**：多条重复记录的字段取值按优先级表（doi>title>year>journal...）消解，冲突逐条记录裁决规则与备选值，结果稳定可复算。
4. **来源回溯**：每条记录保留来源库、请求参数、原始响应片段、字段来源——结论可逐条核对到库。
5. **失败降级**：某库不可用/限流/字段变更/返回异常时显式披露缺口（overall=incomplete），不静默返回不完整结果。
6. **脚本先行**：字段映射/合并/去重/降级报告恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：字段标准化（0请求）
按 FIELD_MAP 把各库原始记录映射为规范记录（每字段带 provenance: source_db + source_alias）。

### 阶段 2：合并与去重（0请求）
```bash
python <SKILL_DIR>/scripts/multidb_engine.py --merge /app/work/normalized.json > /app/work/merged.json
```
合并键：DOI优先，无DOI用标题归一化前60字；每字段记录 field_merge_log（field_priority/conflict_resolved/all_missing）。

### 阶段 3：降级报告（0请求）
```bash
python <SKILL_DIR>/scripts/multidb_engine.py --degrade /app/work/dbs.json
```
逐库 status（ok/failed/rate_limited）+ gap 说明 + action。

### 阶段 4：语义复核（约2-4次模型请求）
复核冲突裁决是否合理（如标题仅大小写差异不应算实质冲突→修正规则）、各库覆盖贡献是否异常。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：normalized、merged（含 merge_log）、provenance、degrade 报告、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/multidb-report.md --require "映射|mapping|标准化,合并|merge|去重|dedup,来源|provenance|回溯,降级|degrade|失败|缺口" --names "mapping,merge,provenance,degrade"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 某库不可用 | degrade=failed，overall=incomplete，缺口显式披露 |
| 字段方言未知 | aliases 表扩展并记录，未识别字段进 unknown |
| 合并冲突过多 | 报告冲突率，>30% 时升级人工仲裁 |
| 预算不足 | normalized/merged 先落盘 status=partial |

## 资源清单
- `scripts/multidb_engine.py` — 字段映射/合并/降级（确定性引擎）
- `scripts/search_audit.py` — 合并后覆盖率复算
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/multidb-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。映射/合并/降级恒为0请求。过60%时间冻结：normalized+merged 先落盘。