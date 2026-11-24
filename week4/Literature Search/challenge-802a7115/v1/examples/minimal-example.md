# 最小调用示例（示例数据，非正式案例结果）

## 术语表 terms.tsv
```
肿瘤	tumor	synonym
机器学习	ML	abbr
```

## 调用
```bash
python scripts/crosslang_search.py --termmatrix terms.tsv > terms.json
python scripts/crosslang_search.py --detect records.json
python scripts/crosslang_search.py --match records.json terms.json > hits.json
python scripts/crosslang_search.py --backtranslate hits.json
```

## 示意输出
```json
{"records": [{"id": 1, "lang_title": "zh", "version": "original"},
              {"id": 2, "lang_title": "en", "version": "bilingual_journal", "risk": "语种标错会导致查询词错配"}]}
{"n_matched": 3, "matches": [{"id": 1, "matched_terms": [{"zh": "肿瘤", "en_hit": "tumor"}]}]}
{"high_risk": 1, "queue": [{"id": 3, "backtranslate_required": true, "reason": "音译/本地名命中"}]}
```
