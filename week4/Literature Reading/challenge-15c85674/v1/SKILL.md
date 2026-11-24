---
name: literature-qa-forge
description: 文献智能问答。基于带段落编号的英文论文回答中文问题：跨语言检索定位证据段落，逐题回答（含子问）附段落编号+短引文，保留数值/单位/条件/比较对象，区分实测/作者解释/推断，未报告/部分回答/冲突显式说明——不编造答案或引用。触发词：文献问答、依据、段落编号、拒答。
---

# literature-qa-forge — 文献智能问答：回答问题，也给出依据

一句话：**跨语言检索定位证据、逐题作答附锚点、条件不丢、不确定不编。**

## 核心原则（不可违反）

1. **逐题覆盖**：每个问题及其子问独立作答；必要时整合方法、结果、讨论和表格信息——不漏子问。
2. **依据锚定**：主要论断附论文标识+原文段落编号+支持短引文，答案与证据一一核对；无锚点的论断标为推断。
3. **条件保留**：数值/单位/比较对象/实验条件/结论范围随值保留；"可能""提示"不得改写为确定事实。
4. **不确定性三分类**：材料未报告→说明无法确定；部分可答→列出缺口；原文冲突→指出冲突及出处。读取失败→明确报告。**不编造答案或引用**。
5. **仅依据给定材料**：不联网检索、不做PDF解析/图像识别——平台已提供摘要/正文/表格文字/图注/参考文献著录。
6. **脚本先行**：段落索引/跨语言检索/脚手架/不确定性审计恒为0模型请求；模型只做答案成文与语义裁决。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```
确认论文段落清单、问题清单（含子问）。

### 阶段 1：段落索引（0请求）
```bash
python <SKILL_DIR>/scripts/qa_engine.py --index <论文.json> > /app/work/index.json
```

### 阶段 2：逐题检索与脚手架（0请求/题）
```bash
python <SKILL_DIR>/scripts/qa_engine.py --retrieve <论文.json> "<问题>" > /app/work/ev_Q1.json
python <SKILL_DIR>/scripts/qa_engine.py --scaffold <论文.json> "<问题>" > /app/work/scaf_Q1.json
```
中文问题经 ZH_EN_MAP 扩展后检索英文段落；候选证据按 section 权重排序（Results 优先）。

### 阶段 3：逐题作答（约3-5次模型请求）
按脚手架逐题成文：回答+锚点（段落编号+短引文）+条件+类型标记（实测/解释/推断）。跨章节整合时逐处标锚点。

### 阶段 4：不确定性审计（0请求）
```bash
python <SKILL_DIR>/scripts/qa_engine.py --uncertainty /app/work/answers.json > /app/work/audit.json
```
检查 unreported/partial/conflict/infer/missing_anchor 标记；FAIL 项修复。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：逐题答案（含锚点）、审计、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/qa-report.md --require "回答|answer|逐题,依据|anchor|段落|para|引文,条件|condition|单位|unit,不确定|uncertain|未报告|unreported" --names "answers,anchors,conditions,uncertainty"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 检索零命中 | 同义词二次扩展+全段落扫描；仍零→如实说明论文未涉及该问题 |
| 问题含表格数据 | 表格文字作为段落纳入检索（题面已提供表格文字） |
| 数值无单位 | 标 missing_unit，答案注明"原文未给出单位" |
| 预算不足 | 检索JSON先落盘，答案可 partial |

## 资源清单
- `scripts/qa_engine.py` — index/retrieve/scaffold/uncertainty（确定性引擎，含中英对照词表）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/qa-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。索引/检索/脚手架/审计恒为0请求；模型逐题成文（9问题≤6次请求）。过60%时间冻结：已检索证据先落盘。