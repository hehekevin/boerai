# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/clean_engine.py --normalize records.json > normalized.json
python scripts/clean_engine.py --units values.json
python scripts/clean_engine.py --merge normalized.json
python scripts/clean_engine.py --trace normalized.json
```

## 示意输出
```json
{"converted": 2, "needs_manual": 1,
 "items": [{"input": "92.5 percent", "canonical": "0.925 ratio", "formula": "92.5*0.01=0.925", "original_kept": "92.5 percent"},
            {"input": "3.2 kPa", "canonical": "3.2 kPa", "formula": "no_conversion", "note": "单位未收录——保留原值"}]}
{"n_merge_groups": 1, "merges": [{"merge_key": {"substance": "tio2", "experiment": "exp1"},
   "field_conflicts": {"accuracy": ["92.5", "93.0"]}}]}
```
