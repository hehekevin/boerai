# 最小调用示例（示例数据，非正式案例结果）

## 调用

```bash
python scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
# （模型：element-source-map + SVG 绘制）
python scripts/svg_audit.py --check /app/output/graphical-abstract.svg
python scripts/svg_audit.py --pair /app/output/graphical-abstract.svg /app/output/graphical-abstract.png
python scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript element-source-map.md --require "实体|element,来源|source,编码|图例" --names "elements,sources,encoding"
```

## 示意 element-source-map（节选）

| 面板 | 要素 | 类型 | 来源 | 图面表达 |
|-|-|-|-|-|
| A | 耐药菌株感染问题 | 实体 | abstract.txt:2 | 病菌图标+文字 |
| B | 纳米载体制备 | 步骤 | methods.md:5 | 圆角矩形+箭头 |
| C | 抑菌率 92.3%（n=6） | 数值 | results.csv:3 | 柱长+标签 |

## 示意 svg_audit（节选）

```json
{"info": {"n_text": 14, "groups": ["panel-A","panel-B","panel-C","panel-D"], "palette": [["#2b6cb0",6],["#e53e3e",3]]},
 "warnings": ["LEGEND: >=4 colors but no legend-like text — color encoding must map to a legend"],
 "problems": []}
```
