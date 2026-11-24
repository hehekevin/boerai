# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/content_extract.py --extract page.html > content.json
python scripts/content_extract.py --segments content.txt > segments.json
python scripts/build_glossary.py --segments segments.json --out glossary.csv
python scripts/verify_translation.py --source content.txt --bilingual bilingual.md --glossary glossary.csv
```

## 示意输出
```json
{"n_body_blocks": 3, "structure": [
  {"type": "heading", "text": "Deep Learning for Imaging"},
  {"type": "para", "text": "Paragraph one: model achieved 93.2 percent accuracy."}],
 "n_noise_blocks_removed": 0,
 "note": "导航/广告/参考文献区已切除"}
```
