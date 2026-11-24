---
name: evidence-verify-forge
description: 文献证据溯源与事实核验。复杂论断拆成事实/比较/因果/范围可独立核验的子判断（不遗漏不重复），每条子判断定位最小充分证据（精确到章节/段落/句子），支持度四档判定（支持/部分支持/不支持/不充分——主题相关≠支持），冲突/限制/无法确定显式写出。触发词：证据溯源、事实核验、论断拆解、支持度。
---

# evidence-verify-forge — 文献证据溯源与事实核验

一句话：**论断拆得开、证据找得到、判定判得准（主题相关≠支持）、冲突说得清。**

## 核心原则（不可违反）

1. **拆得开**：复杂论断拆成事实/比较/因果/范围可独立核验的子判断；每条子判断标注所需证据类型；不遗漏不重复。
2. **找得到**：每条子判断定位到最小充分证据——精确到章节/段落/句子，不只给篇名与作者；证据摘录逐字截取。
3. **判得准**：支持度四档（支持/部分支持/不支持/不充分）——"部分支持"与"不支持"必须与"主题相关"区分开（主题相关但要素不全=不充分；提示性表述=部分支持）。
4. **说得清**：来源冲突、样本与范围限制、无法由原文确定的部分显式写出，不被一句结论掩盖。
5. **转引核验**：引用段落是否真含对应结论；处理转引、跨页、图表引用、摘要与正文不一致。
6. **脚本先行**：拆解/支持度判定/引用对账恒为0模型请求；模型只做证据语义定位与边界裁决。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：论断拆解（0请求）
```bash
python <SKILL_DIR>/scripts/verify_engine.py --decompose "<论断原文>" > /app/work/subclaims.json
```

### 阶段 2：证据定位（模型辅助，约2-3次请求）
按子判断证据类型在给定材料中定位最小充分证据——模型逐条找句子级证据，记录 {sub_id, claim_text, evidence_text, section, para_no}。

### 阶段 3：支持度判定（0请求）
```bash
python <SKILL_DIR>/scripts/verify_engine.py --support /app/work/evidence.json > /app/work/verdicts.json
```
四档判定（含跨语言词表扩展）；topic_related_only 标记防止主题相关冒充支持。

### 阶段 4：引用对账（0请求）
```bash
python <SKILL_DIR>/scripts/claim_evidence.py --checkref <材料> 
```

### 阶段 5：冲突与限制成文（约1-2次模型请求）
来源冲突/范围限制/无法确定逐条写明；组装 result.json（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/verify-report.md --require "拆解|decompose|子判断|subclaim,证据|evidence|定位|最小,支持|support|判定|verdict,冲突|conflict|限制|limitation" --names "decompose,evidence,verdicts,conflicts"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 子判断找不到证据 | 标不充分+说明搜索范围，不编造 |
| 证据为转引 | 标"转引"，建议引原文 |
| 图表引用 | 记图表编号+题注（题面已提供图注文字） |
| 中英跨语言判定 | ZH_EN_MAP 词表扩展；未覆盖词入 gaps |
| 预算不足 | subclaims.json 先落盘 status=partial |

## 资源清单
- `scripts/verify_engine.py` — decompose/support（确定性引擎，含跨语言词表）
- `scripts/claim_evidence.py` — 论断单元/引用对账（复用）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/verify-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。拆解/判定/对账恒为0请求；模型证据定位（9问题内≤6次）。过60%时间冻结。