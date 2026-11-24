# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/increment_tracker.py --baseline baseline.json current.json
python scripts/increment_tracker.py --dedupkeys current.json
python scripts/increment_tracker.py --window 2026-11-18 2026-11-25 UTC+8
python scripts/increment_tracker.py --retrylog events.json
```

## 示意输出
```json
{"n_new": 1, "n_updated": 1, "n_removed": 0,
 "updated": [{"key": "doi:10.1/a", "changes": {"version": {"old": "None", "new": "v2"}}}],
 "removed": [], "next_watermark_note": "本次 current 快照即下次的 baseline"}
{"retryable": 1, "non_retryable": 1, "note": "重跑幂等，不产生二次推送"}
```
