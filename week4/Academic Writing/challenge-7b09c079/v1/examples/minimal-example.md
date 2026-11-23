# 最小调用示例（示例数据，非正式案例结果）

## 调用

```bash
python scripts/revision_tracker.py --numbering manuscript.md --out numbering.json
python scripts/revision_tracker.py --diff manuscript.md manuscript-revised.md --out revisions.json
python scripts/revision_tracker.py --numbering manuscript-revised.md
```

## 示意修订记录（节选）

```json
{"revisions": [
  {"id": "R001", "type": "replaced", "old_para": 2, "before": "本方法效果很好。", "after": "本方法在 A 数据集上准确率提升 5.2 个百分点。"},
  {"id": "R002", "type": "added", "new_para": 4, "after": "## 4. 讨论\n局限性见 4.3。"}],
 "sentence_changes": [{"parent": "R001", "type": "replace", "before": "效果很好", "after": "准确率提升 5.2 个百分点"}]}
```
