# 示例（示例数据，非正式案例结果）

| 文件 | 图型 | 演示要点 |
|---|---|---|
| `example_spec.json` | mechanism_pathway | 三区室、激活/抑制/结合、误差线柱图、图例与图注 |
| `example_relationship.json` | relationship_schematic | 包含框、非成员避让、连线时延标注 |
| `example_chart.json` | data_chart | 2×2 面板：柱、折线、热图、箱线 |
| `example_apparatus.json` | apparatus_route | 部件—管路—流向、工况写在部件上、步骤时长柱图 |
| `example_graphical_abstract.json` | graphical_abstract | 四栏叙事、跨面板主线、颜色编码与图例 |

全部内容为演示接口而构造（教科书拓扑 + 虚构数值），**不得作为正式案例结果引用**。

```bash
python ../run.py demo --out /tmp/figforge_demo          # mechanism 示例
python ../selftest.py                                   # 构建全部示例并打印检查结果
```
