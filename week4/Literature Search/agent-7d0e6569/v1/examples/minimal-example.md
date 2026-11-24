# 最小调用示例（示例数据，非正式案例结果）

## 输入 queries.tsv
```
1	"cancer" AND "ML"	PubMed	120	5
2	"cancer" AND "deep learning"	WoS	118	8
3	"cancer" AND "neural network"	Scopus	118	10
```

## 调用
```bash
python scripts/iter_loop.py --ledger queries.tsv > ledger.json
python scripts/iter_loop.py --stop ledger.json
python scripts/iter_loop.py --rollback ledger.json
```

## 示意输出
```json
{"should_stop": true, "stop_reasons": [
  {"type": "marginal_gain", "detail": "最后轮边际收益 0.0 < 阈值 0.5"},
  {"type": "coverage", "detail": "估算覆盖 100.0% >= 目标 90%"}],
 "human_intervention_points": 0}
```
