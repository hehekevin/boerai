# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/compare_matrix.py --matrix papers.json > matrix.json
python scripts/compare_matrix.py --comparable matrix.json
python scripts/compare_matrix.py --conflicts matrix.json
```

## 示意输出
```json
{"verdicts": [{"field": "research_object", "comparable": "subset_only",
               "reason": "条件差异 2 种——只能在可比子集内比较"}]}
{"conflicts": [{"papers_up": ["P1"], "papers_down": ["P2"],
                "attribution_candidates": ["research_object", "method", "conditions"]}]}
```
