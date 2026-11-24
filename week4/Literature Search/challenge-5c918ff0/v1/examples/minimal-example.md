# 最小调用示例（示例数据，非正式案例结果）

## 输入（3条跨库记录：PubMed方言TI/DOI/AU/PY，Scopus小写title+journal，WoS仅title+year）

## 调用
```bash
python scripts/multidb_engine.py --demo
python scripts/multidb_engine.py --degrade dbs.json
```

## 示意输出
```json
{"n_input": 3, "n_merged": 2, "n_conflicts": 1,
 "merged": [{"merge_key": "doi:10.1/x", "n_sources": 2,
   "field_merge_log": {"title": "conflict_resolved(priority=title_order, first=PubMed)",
                        "journal": "field_priority (from Scopus)"}}]}
{"overall": "incomplete", "n_failed": 1,
 "dbs": [{"db": "Scopus", "status": "rate_limited", "gap": "该库特有覆盖缺失"}]}
```
