---
name: conclusion-extraction-forge
description: 文献结论与数据提取。三线抽取：结论（区分作者明确结论/限制条件/推测表述——"可能""提示"不改写为确定事实）、条件（样本/设置/来源/时间/基线随数值绑定）、数值（数值+单位+误差+显著性+条件）；每条带段落锚点可独立抽查，missing_unit 显式标记。触发词：结论提取、数据提取、条件绑定、证据定位。
---

# conclusion-extraction-forge — 文献结论与数据提取

一句话：**结论分三档、数值带条件、missing显式标、锚点可抽查。**

## 核心原则（不可违反）

1. **结论三档**：作者明确结论/限制条件/推测性表述严格区分——"可能""提示""suggest"不得改写成确定事实；触发词进提取记录。
2. **条件绑定**：每条数值必须带它成立的条件（样本、实验设置、数据来源、时间点、比较基线），不脱离语境单独成行。
3. **数值完整**：数值+单位+误差±+统计显著性+条件五要素；跨页表格/合并单元格/范围值/未报告情形如实记录。
4. **显式缺失**：missing_unit 等缺失项显式标记，不猜测补全；工具不敢确认的值单独列出（uncertainties）。
5. **锚点可抽查**：每个结构化字段带段落编号（含section），定位粒度足以让第二个人独立抽查——脚本 --locate 强制校验。
6. **脚本先行**：三线抽取/锚点校验恒为0模型请求；模型只做语义归类复核。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：三线抽取（0请求）
```bash
python <SKILL_DIR>/scripts/extraction_engine.py --conclusions <论文.json> > /app/work/conclusions.json
python <SKILL_DIR>/scripts/extraction_engine.py --conditions <论文.json> > /app/work/conditions.json
python <SKILL_DIR>/scripts/extraction_engine.py --values <论文.json> > /app/work/values.json
```

### 阶段 2：锚点校验（0请求）
```bash
python <SKILL_DIR>/scripts/extraction_engine.py --locate /app/work/extraction.json
```
FAIL 项补锚点后重校。

### 阶段 3：语义复核（约2-4次模型请求）
复核三档归类边界（结论vs推测）、跨页表格数值、条件归属；工具不敢确认的值入 uncertainties。

### 阶段 4：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/extraction-report.md --require "结论|conclusion|三档|推测,条件|condition|绑定|语境,数值|value|单位|unit,定位|locate|锚点|anchor" --names "conclusions,conditions,values,locate"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 无结构化论文输入 | gaps 声明（本题不要求PDF解析） |
| 数值噪声（纯小数字） | 过滤规则：<10 无单位无误差无显著性跳过 |
| 表格跨页 | 按题面提供的表格文字处理，锚点记表格标识 |
| 预算不足 | 三线JSON先落盘 status=partial |

## 资源清单
- `scripts/extraction_engine.py` — conclusions/conditions/values/locate（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/extraction-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。抽取/校验恒为0请求；模型复核（≤5次）。过60%时间冻结。