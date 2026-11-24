# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/classify_engine.py --classify records.json taxonomy.json
python scripts/classify_engine.py --tags records.json
python scripts/classify_engine.py --rename records.json "{authors}_{year}_{title}"
python scripts/classify_engine.py --versions records.json
```

## 示意输出
```json
{"records": [{"title": "深度学习肿瘤检测", "assigned": ["医学AI", "医学AI/检测", "机器学习"],
              "rationale": ["医学AI: 命中关键词 ['肿瘤', '检测']"]}]}
{"renamed": [{"filename": "Zhang_2023_Deep_learning_for_tumor_diagnosis.pdf"}]}
{"findings": [{"verdict": "同一文献两个版本：保留信息更全者，另一份归档不删除"}]}
```
