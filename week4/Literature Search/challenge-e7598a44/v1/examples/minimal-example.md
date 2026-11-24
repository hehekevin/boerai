# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/question_decompose.py --decompose "深度学习方法能否提升2020-2024年间肿瘤影像诊断的准确率" > matrix.json
python scripts/question_decompose.py --plan matrix.json
python scripts/question_decompose.py --stop ledger.json
```

## 示意输出
```json
{"elements": [
  {"slot": "object", "extracted_terms": ["肿瘤", "影像"], "extraction_basis": "领域词典直查(object)"},
  {"slot": "mechanism", "extracted_terms": ["诊断"]},
  {"slot": "method", "extracted_terms": ["深度学习"]},
  {"slot": "time_range", "extracted_terms": ["2020-2024"]},
  {"slot": "comparison", "extracted_terms": ["提升"]}],
 "gaps_for_model": ["evidence"]}
{"templates": [
  {"name": "R1-core", "query": "(\"肿瘤\" OR \"影像\") AND (\"诊断\") AND (\"深度学习\")"}]}
```
