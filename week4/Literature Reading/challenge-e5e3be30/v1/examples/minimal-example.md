# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/verify_engine.py --decompose "本方法将准确率提高了5.2个百分点；且在两个数据集上验证。由于计算资源限制，仅在ResNet上进行对比。"
python scripts/verify_engine.py --support evidence.json
python scripts/claim_evidence.py --checkref material.txt
```

## 示意输出
```json
{"subclaims": [{"sub_id": "S1", "claim_type": "fact"}, {"sub_id": "S4", "claim_type": "causal+scope"}]}
{"summary": {"支持": 0, "部分支持": 3},
 "items": [{"sub_id": "S1", "verdict": "部分支持", "reason": "词汇重叠 31%，部分要素未在证据中出现"},
            {"sub_id": "S3", "verdict": "部分支持", "reason": "证据为提示性表述（suggest/may）"}]}
```
