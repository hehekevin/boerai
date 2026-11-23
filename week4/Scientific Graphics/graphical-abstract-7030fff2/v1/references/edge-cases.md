# 异常与降级处置（edge-cases.md）

| 情形 | 处置 |
|-|-|
| 材料缺结果/结论段 | 对应面板占位 + gaps（"材料未提供 X"），不编内容 |
| 来源未指明关系方向 | 不画箭头；gaps + 具体追问 |
| 实体关系与文字冲突 | 以文字为准；conflicts 记录 |
| 图例色数≠分类数 | 以数据分类数为准修正 |
| 渲染器不可用 | 交付 SVG 源 + 导出清单；anomalies 声明未渲染 |
| 编辑指令指向不存在图层 | 不虚构；uncertainties 记录 |
| SVG XML 解析失败 | 修复合法性问题（未闭合标签/非法字符）后重审计 |
| 预算不足 | element-source-map + SVG 先落盘，status=partial |
