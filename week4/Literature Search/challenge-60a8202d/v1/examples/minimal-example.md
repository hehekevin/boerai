# 最小调用示例（示例数据，非正式案例结果）

## 调用
```bash
python scripts/citation_network.py --trace seeds.json links.json > expanded.json
python scripts/citation_network.py --network expanded.json
python scripts/citation_network.py --path expanded.json "ref-A"
python scripts/citation_network.py --merge records.json
```

## 示意输出
```json
{"n_reached": 3, "stop_rules": ["hop>=3 剪枝", "单节点入边>8 标记剪枝"]}
{"hubs": [{"node": "ref-A", "inbound": 2, "role": "hub/bridge"}]}
{"found": true, "path": [{"node": "seed-paper-1", "note": "seed"}, {"node": "ref-A", "via": "seed-paper-1", "direction": "backward"}]}
{"n_merge_groups": 1, "merges": [{"version_type": "preprint_vs_journal"}]}
```
