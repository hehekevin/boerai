# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/extraction_engine.py --conclusions paper.json
python scripts/extraction_engine.py --conditions paper.json
python scripts/extraction_engine.py --values paper.json
python scripts/extraction_engine.py --locate extraction.json
```

## 示意输出
```json
{"items": [{"type": "明确结论", "para_no": 2, "sentence": "Our results show the model achieved 93.2 percent accuracy"},
            {"type": "限制条件", "para_no": 3, "sentence": "However, this may only generalize..."}]}
{"items": [{"value": "93.2", "unit": "percent", "stat_sig": "p-value/significant in context", "para_no": 2},
            {"value": "120", "unit": "missing_unit", "para_no": 1}]}
```
