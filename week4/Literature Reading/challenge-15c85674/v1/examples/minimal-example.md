# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/qa_engine.py --index paper.json > index.json
python scripts/qa_engine.py --retrieve paper.json "模型的准确率是多少？"
python scripts/qa_engine.py --scaffold paper.json "准确率多少？与基线相比如何？" > scaffold.json
python scripts/qa_engine.py --uncertainty answers.json
```

## 示意输出
```json
{"topk": [{"no": 2, "section": "Results", "excerpt": "The model achieved 93.2 percent accuracy..."}]}
{"subquestions": ["准确率多少", "与基线相比如何"], "candidate_evidence": [{"no": 2}]}
{"audit": [{"qid": "Q2外部验证", "flags": [{"flag": "unreported", "handling": "材料未报告——如实说明无法确定"}]}]}
```
