# 最小调用示例（示例数据，非正式案例结果）

## 调用

```bash
python scripts/svg_audit.py --check /app/output/diagram.svg
python scripts/svg_audit.py --pair /app/output/diagram.svg /app/output/diagram.png /app/output/diagram.pdf
```

## 示意 element-source-map（节选）

| from | to | 类型 | 方向依据 | 来源 |
|-|-|-|-|-|
| 药物 X | 通路 A | 激活 | "X activates pathway A" | paper.md:14 |
| 通路 A | 通路 B | 抑制 | "A inhibits B" | paper.md:15 |

## 示意 svg_audit（节选）

```json
{"info": {"n_text": 9, "groups": ["mech-core","legend","labels"], "n_path": 12},
 "warnings": ["LAYERS: 2/6 groups unnamed — add data-role/id per panel"],
 "problems": []}
```
