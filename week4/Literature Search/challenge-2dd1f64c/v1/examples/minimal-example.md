# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/ranking_engine.py --score records.json > scored.json
python scripts/ranking_engine.py --label scored.json
python scripts/ranking_engine.py --conflicts scored.json
python scripts/ranking_engine.py --explain scored.json
```

## 示意输出
```json
{"ranked": [{"rank": 1, "title": "Deep learning tumor diagnosis RCT", "score": 0.8945}]}
{"summary": {"core_evidence": 3}}
{"n_conflicts": 1, "conflicts": [{"type": "same_study_multi_report"}]}
{"explanations": [{"rank": 1, "rule_hit": "加权合计（主信号: relevance_terms_hit）", "confidence": "high"}]}
```
