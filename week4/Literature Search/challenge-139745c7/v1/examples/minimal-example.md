# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/file_search.py --find /data "experiment,result"
python scripts/file_search.py --locate /data/report.md "accuracy"
python scripts/file_search.py --filter /data filters.json
python scripts/file_search.py --versions /data
```

## 示意输出
```json
{"find": {"n_matched": 3, "results": [{"path": "/data/a.md", "score": 6}]}
{"locate": {"n_hits": 2, "hits": [{"line": 42, "section": "3. Results", "excerpt": "...accuracy improved..."}]}}
{"filter": {"n_matched": 1, "unsatisfiable_filters": [{"filter": "year", "reason": "/data/b.md 不是可读文本"}]}}
```
