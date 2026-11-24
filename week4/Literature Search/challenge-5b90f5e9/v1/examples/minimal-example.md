# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/screening_engine.py --protocol "ML能否提升肿瘤诊断准确率" > protocol.json
python scripts/screening_engine.py --screen refs.tsv protocol.json > screen.json
python scripts/screening_engine.py --audit stages.json
```

## 示意输出
```json
{"n_input": 3, "counts": {"include": 2, "exclude": 1, "pending": 0},
 "records": [
   {"idx": 0, "decision": "include", "reason_code": "I2", "evidence": "randomized controlled trial"},
   {"idx": 1, "decision": "exclude", "reason_code": "E1", "evidence": "editorial comment"}
 ]}
{"closed_loop": true, "chain": [{"stage": "dedup", "n_in": 5, "n_out": 4, "n_excluded": 1}]}
```
