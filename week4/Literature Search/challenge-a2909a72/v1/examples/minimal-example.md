# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/search_audit.py --plan "machine learning" "cancer" > plan.json
python scripts/search_audit.py --dedup results.tsv
python scripts/iter_loop.py --ledger queries.tsv > ledger.json
python scripts/iter_loop.py --stop ledger.json
```
